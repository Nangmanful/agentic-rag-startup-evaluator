# agents/investment_decider.py
# 투자 판단 서브-에이전트 (LangGraph 노드용) - 시장성 지표 + 경쟁사 비교(1~5) 반영 버전
# - Scorecard: 표준 비중(%) 반영
# - Bessemer: 기존 5키(백워드 호환) + 선택적 10문항 체크리스트 지원
# - 규제 리스크 방향 반전 옵션 포함
# - 분류만 수행(외부 검색/추론 없음)

import os
from typing import Dict, Any, List, Optional

# ===== 설정값 =====
W_MARKET = float(os.getenv("INV_DECISION_W_MARKET", "0.6"))
W_COMP   = float(os.getenv("INV_DECISION_W_COMP", "0.4"))
THRESH_YES   = float(os.getenv("INV_DECISION_THRESH_YES", "0.62"))
THRESH_MAYBE = float(os.getenv("INV_DECISION_THRESH_MAYBE", "0.52"))
MIN_SOURCES  = int(os.getenv("INV_DECISION_MIN_SOURCES", "1"))
# 규제 리스크가 높을수록 "나쁘다"면 false로 두십시오(점수 반전)
REG_RISK_HIGH_IS_GOOD = os.getenv("INV_DECISION_REG_RISK_HIGH_IS_GOOD", "false").lower() == "true"

# Scorecard 비중(%) - 표에 맞춤
SCORECARD_WEIGHTS = {
    "management_team": 30,                # Owner
    "market_size": 25,                    # Opportunity Size
    "product_technology": 15,             # Product/Tech
    "competitive_environment": 10,        # Competitive Advantage
    "marketing_sales": 10,                # Traction
    "need_for_additional_investment": 10, # Deal Terms
}

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def _to_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None

def _to_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None

def _collect_sources(m: Dict[str, Any], c: Dict[str, Any]) -> List[str]:
    s: List[str] = []
    me = (m or {}).get("evidence_sources") or []
    ce = (c or {}).get("evidence_sources") or []
    if isinstance(me, list):
        s.extend([str(x) for x in me])
    if isinstance(ce, list):
        s.extend([str(x) for x in ce])
    # 중복 제거(순서 보존)
    return list(dict.fromkeys(s))

# ---------------------------
# 시장성 정규화 점수 계산
# ---------------------------
def _normalize_market(m: Dict[str, Any]) -> float:
    """
    우선순위:
      1) normalized_score (0~1) 직접 주면 그대로 사용
      2) method == "scorecard": 표준 비중 가중 평균(0~10) → /10
      3) method == "bessemer":
         3-1) 선택적 10문항 체크리스트가 있으면 가중 평균
         3-2) 없으면 기존 5키 평균(0~5) → /5 (백워드 호환)
    """
    if not m:
        return 0.0

    # 1) 직접 정규화
    ns = _to_float(m.get("normalized_score"))
    if ns is not None:
        return _clamp01(ns)

    method = m.get("method")

    # 2) Scorecard 가중 평균
    if method == "scorecard" and isinstance(m.get("scorecard"), dict):
        s = m["scorecard"]
        wsum = 0.0
        wtot = 0.0
        for k, w in SCORECARD_WEIGHTS.items():
            v = _to_float(s.get(k))
            if v is None:
                continue
            # 0~10 가정
            wsum += v * w
            wtot += w
        if wtot == 0.0:
            return 0.0
        raw_0_10 = wsum / wtot
        return _clamp01(raw_0_10 / 10.0)

    # 3) Bessemer
    if method == "bessemer":
        # 3-1) 선택적 10문항 체크리스트(있으면 우선 사용)
        # 입력 예시(옵션):
        # m["bessemer_checklist"] = {
        #   "market_size": 0~5 or {yes/no→1/0→×5}, "solves_real_problem": 0~5, ...
        #   총 10개 키(이름은 아래 keys_10 참고). 스케일 0~5 기준 권장.
        # }
        bc = m.get("bessemer_checklist")
        if isinstance(bc, dict):
            # 10문항 키 매핑(이름은 설명용, 실제 스키마는 유연하게 받아 float 변환되는 값만 사용)
            keys_10 = [
                "market_size",
                "solves_real_problem",
                "willingness_to_pay",
                "differentiation",
                "founder_team_credibility",
                "early_customer_reaction",
                "revenue_model_clarity",
                "is_big_opportunity_if_success",
                "risks_tech_ops_legal",
                "founder_long_term_commitment",
            ]
            vals: List[float] = []
            for k in keys_10:
                v = _to_float(bc.get(k))
                if v is None:
                    continue
                # 규제/법률 리스크 항목이 "높을수록 나쁨" 스케일이라면(예: 0 나쁨 ~ 5 좋음으로 바꾸려면) 반전 규칙 적용
                if k == "risks_tech_ops_legal" and not REG_RISK_HIGH_IS_GOOD:
                    # 입력이 "리스크 크기"라면 낮을수록 좋게 만들기 위해 반전
                    # 0~5 스케일 가정 → 5 - v
                    v = 5.0 - v
                vals.append(v)
            if vals:
                raw_0_5 = sum(vals) / len(vals)
                return _clamp01(raw_0_5 / 5.0)
            # 체크리스트가 있으나 전부 비어있으면 5키로 폴백

        # 3-2) 기존 5키(백워드 호환)
        b = m.get("bessemer")
        if isinstance(b, dict):
            keys = ["product_market_fit", "growth_moat", "monetization", "team_experience", "regulatory_risk"]
            vals = []
            for k in keys:
                v = _to_float(b.get(k))
                if v is None:
                    continue
                if k == "regulatory_risk" and not REG_RISK_HIGH_IS_GOOD:
                    v = 5.0 - v
                vals.append(v)
            if not vals:
                return 0.0
            raw_0_5 = sum(vals) / len(vals)
            return _clamp01(raw_0_5 / 5.0)

    # 아무 것도 없으면 0
    return 0.0

# ---------------------------
# 경쟁사 비교 정규화 (1~5 → 0~1)
# ---------------------------
def _normalize_competitor(c: Dict[str, Any]) -> float:
    if not c:
        return 0.0
    items = c.get("items") or []
    if not items:
        return 0.0
    ratings: List[int] = []
    for it in items:
        r = _to_int(it.get("rating", 0)) if isinstance(it, dict) else None
        if r is None:
            continue
        if r < 1: r = 1
        if r > 5: r = 5
        ratings.append(r)
    if not ratings:
        return 0.0
    avg = sum(ratings) / len(ratings)  # 1~5
    return _clamp01((avg - 1.0) / 4.0) # 0~1

# ---------------------------
# 집계, 신뢰도, 설명
# ---------------------------
def _aggregate_score(market_score: float, comp_score: float) -> float:
    tot = W_MARKET + W_COMP
    if tot <= 0:
        return 0.0
    return (W_MARKET * market_score + W_COMP * comp_score) / tot

def _confidence(final_s: float, m_s: float, c_s: float, n_src: int) -> float:
    dist = abs(final_s - 0.5)                      # 중심과 거리
    align = 1.0 - abs(m_s - c_s)                   # 두 점수 정렬도
    source_factor = min(1.0, 0.2 + 0.15 * max(0, n_src))  # 근거 개수 보정(대략 6개부터 상한)
    return _clamp01(0.4 * dist + 0.4 * align + 0.2 * source_factor)

def _make_rationale(market: Dict[str, Any], comp: Dict[str, Any],
                    ms: float, cs: float, fs: float) -> List[str]:
    bullets = [
        f"시장성 정규화 점수={ms:.2f} (w={W_MARKET:.2f})",
        f"경쟁우위 정규화 점수={cs:.2f} (w={W_COMP:.2f})",
        f"가중 종합 점수={fs:.2f} (YES {THRESH_YES:.2f}, 모호 {THRESH_MAYBE:.2f})",
    ]
    pos = (market or {}).get("positives") or []
    if pos:
        bullets.append("시장성 강점: " + "; ".join(map(str, pos[:5])))
    rks = (market or {}).get("risks") or []
    if rks:
        bullets.append("시장성 리스크: " + "; ".join(map(str, rks[:5])))

    items = (comp or {}).get("items") or []
    if isinstance(items, list) and items:
        try:
            top3 = sorted(items, key=lambda x: _to_int(x.get("rating")) or 0, reverse=True)[:3]
            bullets.append("주요 경쟁사 비교(상위3): " + "; ".join(
                [f"{(i.get('name') or '?')}:{(i.get('rating') or '?')}" for i in top3]
            ))
        except Exception:
            pass
    return bullets

def _next_actions(decision: str) -> List[str]:
    if decision == "YES":
        return [
            "규제·보안 DD 착수(의료데이터 거버넌스/컴플라이언스 확인)",
            "핵심 고객 레퍼런스 콜 3건 실행",
            "12~18개월 런웨이 기준 투자금/밸류 책정 워킹",
        ]
    return [
        "3개월 후 트랙션(매출/고객수/파일럿 전환율) 재확인",
        "경쟁 대비 USP 실증 자료(임상/벤치마크) 요청",
    ]

# ---------------------------
# LangGraph 노드
# ---------------------------
def investment_decider_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph State 노드: 입력 state에서 결과를 계산해 부분 업데이트 반환"""
    market = state.get("market_eval") or {}
    comp   = state.get("competitor_eval") or {}

    sources = _collect_sources(market, comp)
    if len(sources) < MIN_SOURCES:
        return {"investment_decision": {
            "decision": "NO",
            "confidence": 0.0,
            "score_breakdown": {"market_score": 0.0, "competitor_score": 0.0, "final": 0.0},
            "rationale": ["증거 소스 부족으로 보수적 NO"],
            "risks": (market.get("risks") or []) if isinstance(market, dict) else [],
            "next_actions": ["근거 소스 보강 후 재평가"],
            "used_sources": sources
        }}

    ms = _normalize_market(market)
    cs = _normalize_competitor(comp)
    fs = _aggregate_score(ms, cs)

    if fs >= THRESH_YES:
        decision = "YES"
    elif fs < THRESH_MAYBE:
        decision = "NO"
    else:
        decision = "NO"  # 모호 구간은 보수적 NO

    conf = round(_confidence(fs, ms, cs, len(sources)), 3)
    out = {
        "decision": decision,
        "confidence": conf,
        "score_breakdown": {
            "market_score": round(ms, 3),
            "competitor_score": round(cs, 3),
            "final": round(fs, 3)
        },
        "rationale": _make_rationale(market, comp, ms, cs, fs),
        "risks": (market.get("risks") or []) if isinstance(market, dict) else [],
        "next_actions": _next_actions(decision),
        "used_sources": sources
    }
    return {"investment_decision": out}
