# ----------------------------------------------------------
# 투자 판단 에이전트 (Aggregator / Arbiter)
# - 입력: 시장성 평가 에이전트 결과, 경쟁사 비교 에이전트 결과
# - 출력: YES / NO + 근거(정량/정성), 신뢰도, 권장 후속액션
# - 설계 원칙:
#   1) 결정 규칙이 명시적(재현 가능)
#   2) 임계치/가중치를 환경변수로 변경 가능
#   3) FastAPI 라우터로 즉시 연동 가능
# ----------------------------------------------------------

import os
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, conint, confloat, validator

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/agents/investment", tags=["Agent - InvestmentDecision"])

# =========================
# 환경변수 (기본값 포함)
# =========================
W_MARKET: float = float(os.getenv("INV_DECISION_W_MARKET", "0.6"))      # 시장성 평가 가중치
W_COMP: float = float(os.getenv("INV_DECISION_W_COMP", "0.4"))          # 경쟁사 비교 가중치
THRESH_YES: float = float(os.getenv("INV_DECISION_THRESH_YES", "0.62")) # 종합 점수 YES 임계치(0~1)
THRESH_MAYBE: float = float(os.getenv("INV_DECISION_THRESH_MAYBE", "0.52")) # 모호 구간 하한(0~1)
MIN_SOURCES: int = int(os.getenv("INV_DECISION_MIN_SOURCES", "1"))      # 평가 소스 최소 개수

# =========================
# 입력 스키마
# =========================

class MarketEvalBessemer(BaseModel):
    # Bessemer’s Checklist 일부 예시 스코어(0~5)
    product_market_fit: confloat(ge=0, le=5)
    growth_moat: confloat(ge=0, le=5)
    monetization: confloat(ge=0, le=5)
    team_experience: confloat(ge=0, le=5)
    regulatory_risk: confloat(ge=0, le=5)  # 낮을수록 좋지만, 일단 점수는 높을수록 우수로 가정
    comments: Optional[str] = None

class MarketEvalScorecard(BaseModel):
    # Scorecard Method 일부 예시 가중 스코어(0~10)
    management_team: confloat(ge=0, le=10)
    market_size: confloat(ge=0, le=10)
    product_technology: confloat(ge=0, le=10)
    competitive_environment: confloat(ge=0, le=10)
    marketing_sales: confloat(ge=0, le=10)
    need_for_additional_investment: confloat(ge=0, le=10)
    comments: Optional[str] = None

class MarketEvaluationInput(BaseModel):
    method: Literal["bessemer", "scorecard"]
    # 0~1 구간의 최종 정규화 점수를 바로 줄 수도 있음 (우선순위가 더 높음)
    normalized_score: Optional[confloat(ge=0, le=1)] = None
    bessemer: Optional[MarketEvalBessemer] = None
    scorecard: Optional[MarketEvalScorecard] = None
    risks: Optional[List[str]] = None
    positives: Optional[List[str]] = None
    evidence_sources: Optional[List[str]] = None  # URL, 문서 ID 등

    @validator("bessemer", always=True)
    def check_bessemer_when_needed(cls, v, values):
        if values.get("method") == "bessemer" and values.get("normalized_score") is None and v is None:
            raise ValueError("method='bessemer'면 bessemer 필드 또는 normalized_score가 필요합니다.")
        return v

    @validator("scorecard", always=True)
    def check_scorecard_when_needed(cls, v, values):
        if values.get("method") == "scorecard" and values.get("normalized_score") is None and v is None:
            raise ValueError("method='scorecard'면 scorecard 필드 또는 normalized_score가 필요합니다.")
        return v

class CompetitorItem(BaseModel):
    name: str
    # 경쟁사 비교 점수 ENUM(5~1) → 5가 우리 대상이 우월, 1이 열세라고 해석
    rating: conint(ge=1, le=5)
    notes: Optional[str] = None

class CompetitorComparisonInput(BaseModel):
    target_name: str
    items: List[CompetitorItem]
    evidence_sources: Optional[List[str]] = None

    @validator("items")
    def non_empty(cls, v):
        if not v:
            raise ValueError("items는 최소 1개 이상이어야 합니다.")
        return v

class InvestmentDecisionRequest(BaseModel):
    market: MarketEvaluationInput
    competitor: CompetitorComparisonInput

# =========================
# 출력 스키마
# =========================

class InvestmentDecisionOutput(BaseModel):
    decision: Literal["YES", "NO"]
    confidence: confloat(ge=0, le=1)
    score_breakdown: Dict[str, float]  # {"market_score":0.x, "competitor_score":0.y, "final": z}
    rationale: List[str]               # 정량/정성 근거 요점
    risks: List[str]                   # 주요 리스크
    next_actions: List[str]            # 후속 조치
    used_sources: List[str]            # 증거 링크/문서 ID

# =========================
# 내부 계산 함수
# =========================

def _normalize_market(market: MarketEvaluationInput) -> float:
    if market.normalized_score is not None:
        return float(market.normalized_score)

    if market.method == "bessemer" and market.bessemer:
        b = market.bessemer
        # 간단 평균(0~5) → 0~1 정규화
        raw = (b.product_market_fit + b.growth_moat + b.monetization +
               b.team_experience + b.regulatory_risk) / 5.0
        return max(0.0, min(1.0, raw / 5.0))

    if market.method == "scorecard" and market.scorecard:
        s = market.scorecard
        # 간단 평균(0~10) → 0~1 정규화
        raw = (s.management_team + s.market_size + s.product_technology +
               s.competitive_environment + s.marketing_sales + s.need_for_additional_investment) / 6.0
        return max(0.0, min(1.0, raw / 10.0))

    # 방어적 기본값
    return 0.0


def _normalize_competitor(comp: CompetitorComparisonInput) -> float:
    # ENUM(5~1) → 0~1 정규화. 5=우월(1.0), 1=열세(0.0)
    avg = sum(item.rating for item in comp.items) / len(comp.items)
    return (avg - 1.0) / 4.0  # 1→0.0, 5→1.0


def _aggregate_score(market_score: float, comp_score: float) -> float:
    # 가중 평균
    total_w = W_MARKET + W_COMP
    if total_w <= 0:
        return 0.0
    return (W_MARKET * market_score + W_COMP * comp_score) / total_w


def _confidence(final_score: float, market_score: float, comp_score: float, n_sources: int) -> float:
    # 간단 신뢰도 휴리스틱:
    # - 점수가 임계치에서 멀수록 ↑
    # - market/competitor가 일치(동일 방향으로 높거나 낮음)하면 ↑
    # - 증거 소스 개수 많을수록 ↑
    dist = abs(final_score - 0.5)
    align = 1.0 - abs(market_score - comp_score)  # 0~1
    source_factor = min(1.0, 0.2 + 0.15 * max(0, n_sources))  # 1~5개 근거에서 0.35~1.0 근처
    c = 0.4 * dist + 0.4 * align + 0.2 * source_factor
    return max(0.0, min(1.0, c))


def _make_rationale(market: MarketEvaluationInput, comp: CompetitorComparisonInput,
                    market_score: float, comp_score: float, final_score: float) -> List[str]:
    bullets = [
        f"시장성 정규화 점수={market_score:.2f} (가중치 {W_MARKET:.2f})",
        f"경쟁우위 정규화 점수={comp_score:.2f} (가중치 {W_COMP:.2f})",
        f"가중 종합 점수={final_score:.2f} (YES 임계치 {THRESH_YES:.2f}, 모호구간 하한 {THRESH_MAYBE:.2f})",
    ]
    if market.positives:
        bullets.append("시장성 강점: " + "; ".join(market.positives[:5]))
    if market.risks:
        bullets.append("시장성 리스크: " + "; ".join(market.risks[:5]))
    # 경쟁사 간단 요약
    top3 = sorted(comp.items, key=lambda x: x.rating, reverse=True)[:3]
    bullets.append("주요 경쟁사 비교(상위 3): " + "; ".join([f"{it.name}:{it.rating}" for it in top3]))
    return bullets


def _make_next_actions(decision: str, market: MarketEvaluationInput, comp: CompetitorComparisonInput) -> List[str]:
    actions: List[str] = []
    if decision == "YES":
        actions += [
            "기술·규제 DD 착수(의료 규제/데이터 거버넌스 확인)",
            "핵심 고객 3곳 레퍼런스 콜",
            "12~18개월 런웨이 기준 투자금액·밸류 산정 워킹",
        ]
    else:
        actions += [
            "3개월 후 트랙션 지표(매출/고객수/파일럿 전환율) 재확인",
            "경쟁사 대비 USP 입증 자료(임상/성능 벤치마크) 요청",
        ]
    return actions


def _collect_sources(market: MarketEvaluationInput, comp: CompetitorComparisonInput) -> List[str]:
    src = []
    if market.evidence_sources:
        src.extend(market.evidence_sources)
    if comp.evidence_sources:
        src.extend(comp.evidence_sources)
    # 중복 제거
    return list(dict.fromkeys(src))


def decide_investment(payload: InvestmentDecisionRequest) -> InvestmentDecisionOutput:
    # 1) 입력 검증: 최소 증거원 개수
    sources = _collect_sources(payload.market, payload.competitor)
    if len(sources) < MIN_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"증거 소스가 부족합니다. 최소 {MIN_SOURCES}개 이상 필요합니다."
        )

    # 2) 정규화 점수 계산
    market_score = _normalize_market(payload.market)
    comp_score = _normalize_competitor(payload.competitor)

    # 3) 종합 점수 산출
    final_score = _aggregate_score(market_score, comp_score)

    # 4) 결정 규칙
    if final_score >= THRESH_YES:
        decision = "YES"
    elif final_score < THRESH_MAYBE:
        decision = "NO"
    else:
        # 모호구간: 보수적으로 NO
        decision = "NO"

    # 5) 신뢰도 & 근거 & 리스크/액션
    conf = _confidence(final_score, market_score, comp_score, n_sources=len(sources))
    rationale = _make_rationale(payload.market, payload.competitor, market_score, comp_score, final_score)
    risks = payload.market.risks or []
    next_actions = _make_next_actions(decision, payload.market, payload.competitor)

    return InvestmentDecisionOutput(
        decision=decision,
        confidence=round(conf, 3),
        score_breakdown={
            "market_score": round(market_score, 3),
            "competitor_score": round(comp_score, 3),
            "final": round(final_score, 3),
        },
        rationale=rationale,
        risks=risks,
        next_actions=next_actions,
        used_sources=sources
    )

# =========================
# FastAPI 라우터
# =========================

@router.post("/decide", response_model=InvestmentDecisionOutput)
def post_decide(req: InvestmentDecisionRequest):
    try:
        result = decide_investment(req)
        return JSONResponse(status_code=200, content=result.dict())
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal error: {e}")
