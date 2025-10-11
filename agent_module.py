# 투자 판단 서브-에이전트 (LangGraph 노드용)
# 입력 기대 키:
#   state["market_eval"] = {
#       "normalized_score": float (0~1) | None,
#       "method": "bessemer" | "scorecard" | None,
#       "bessemer": { "product_market_fit":0~5, "growth_moat":0~5, "monetization":0~5,
#                     "team_experience":0~5, "regulatory_risk":0~5 } | None,
#       "scorecard": { "management_team":0~10, "market_size":0~10, "product_technology":0~10,
#                      "competitive_environment":0~10, "marketing_sales":0~10,
#                      "need_for_additional_investment":0~10 } | None,
#       "positives": [str], "risks": [str], "evidence_sources": [str]
#   }
#   state["competitor_eval"] = {
#       "target_name": str,
#       "items": [{"name": str, "rating": int(1~5), "notes": str?}, ...],
#       "evidence_sources": [str]
#   }
# 출력 업데이트 키:
#   state["investment_decision"] = {
#       "decision": "YES" | "NO",
#       "confidence": float(0~1),
#       "score_breakdown": {"market_score": float, "competitor_score": float, "final": float},
#       "rationale": [str],
#       "risks": [str],
#       "next_actions": [str],
#       "used_sources": [str]
#   }

import os
from typing import Dict, Any, List

# 환경변수 기반 정책 파라미터 (필요시 .env로 관리)
W_MARKET = float(os.getenv("INV_DECISION_W_MARKET", "0.6"))
W_COMP   = float(os.getenv("INV_DECISION_W_COMP", "0.4"))
THRESH_YES   = float(os.getenv("INV_DECISION_THRESH_YES", "0.62"))
THRESH_MAYBE = float(os.getenv("INV_DECISION_THRESH_MAYBE", "0.52"))
MIN_SOURCES  = int(os.getenv("INV_DECISION_MIN_SOURCES", "1"))

def _normalize_market(m: Dict[str, Any]) -> float:
    if not m:
        return 0.0
    ns = m.get("normalized_score", None)
    if ns is not None:
        try:
            return max(0.0, min(1.0, float(ns)))
        except Exception:
            return 0.0

    method = m.get("method")
    if method == "bessemer" and isinstance(m.get("bessemer"), dict):
        b = m["bessemer"]
        keys = ["product_market_fit","growth_moat","monetization","team_experience","regulatory_risk"]
        vals = []
        for k in keys:
            if k in b:
                try:
                    vals.append(float(b[k]))
                except Exception:
                    pass
        if not vals:
            return 0.0
        return max(0.0, min(1.0, sum(vals)/len(vals) / 5.0))

    if method == "scorecard" and isinstance(m.get("scorecard"), dict):
        s = m["scorecard"]
        keys = ["management_team","market_size","product_technology",
                "competitive_environment","marketing_sales","need_for_additional_investment"]
        vals = []
        for k in keys:
            if k in s:
                try:
                    vals.append(float(s[k]))
                except Exception:
                    pass
        if not vals:
            return 0.0
        return max(0.0, min(1.0, sum(vals)/len(vals) / 10.0))

    return 0.0

def _normalize_competitor(c: Dict[str, Any]) -> float:
    if not c:
        return 0.0
    items = c.get("items") or []
    if not items:
        return 0.0
    ratings = []
    for it in items:
        try:
            ratings.append(int(it.get("rating", 0)))
        except Exception:
            pass
    if not ratings:
        return 0.0
    avg = sum(ratings)/len(ratings)
    return max(0.0, min(1.0, (avg - 1.0) / 4.0))  # 1→0.0, 5→1.0

def _aggregate_score(market_score: float, comp_score: float) -> float:
    tot = W_MARKET + W_COMP
    if tot <= 0:
        return 0.0
    return (W_MARKET*market_score + W_COMP*comp_score)/tot

def _confidence(final_s: float, m_s: float, c_s: float, n_src: int) -> float:
    dist = abs(final_s - 0.5)                      # 임계 중심과 거리
    align = 1.0 - abs(m_s - c_s)                   # 두 점수 정렬도
    source_factor = min(1.0, 0.2 + 0.15*max(0, n_src))  # 근거 개수 보정
    c = 0.4*dist + 0.4*align + 0.2*source_factor
    return max(0.0, min(1.0, c))

def _collect_sources(m: Dict[str, Any], c: Dict[str, Any]) -> List[str]:
    s: List[str] = []
    me = (m or {}).get("evidence_sources") or []
    ce = (c or {}).get("evidence_sources") or []
    if isinstance(me, list):
        s.extend([str(x) for x in me])
    if isinstance(ce, list):
        s.extend([str(x) for x in ce])
    # 중복 제거 (순서 보존)
    return list(dict.fromkeys(s))

def _make_rationale(market: Dict[str,Any], comp: Dict[str,Any],
                    ms: float, cs: float, fs: float) -> List[str]:
    bullets = [
        f"시장성 정규화 점수={ms:.2f} (w={W_MARKET:.2f})",
        f"경쟁우위 정규화 점수={cs:.2f} (w={W_COMP:.2f})",
        f"가중 종합 점수={fs:.2f} (YES {THRESH_YES:.2f}, 모호 {THRESH_MAYBE:.2f})",
    ]
    pos = (market or {}).get("positives") or []
    if pos:
        bullets.append("시장성 강점: " + "; ".join([str(x) for x in pos[:5]]))
    rks = (market or {}).get("risks") or []
    if rks:
        bullets.append("시장성 리스크: " + "; ".join([str(x) for x in rks[:5]]))

    items = (comp or {}).get("items") or []
    if items:
        try:
            top3 = sorted(items, key=lambda x: int(x.get("rating", 0)), reverse=True)[:3]
            bullets.append("주요 경쟁사 비교(상위3): " + "; ".join([f"{i.get('name','?')}:{i.get('rating','?')}" for i in top3]))
        except Exception:
            pass
    return bullets

def _next_actions(decision: str) -> List[str]:
    if decision == "YES":
        return [
            "규제·보안 DD 착수(의료데이터 거버넌스/컴플라이언스 확인)",
            "핵심 고객 레퍼런스 콜 3건 실행",
            "12~18개월 런웨이 기준 투자금/밸류 책정 워킹"
        ]
    return [
        "3개월 후 트랙션(매출/고객수/파일럿 전환율) 재확인",
        "경쟁 대비 USP 실증 자료(임상/벤치마크) 요청"
    ]

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
        decision = "NO"  # 모호 구간 보수적 처리

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



'''
# 예시 (그래프 구성 코드 내)
from langgraph.graph import StateGraph, END
from agents.investment_decider import investment_decider_node

g = StateGraph(dict)
g.add_node("investment_decider", investment_decider_node)
# 상위 노드에서 market_eval / competitor_eval 채워진 뒤 실행되도록 엣지 연결
# g.add_edge("competitor_agent", "investment_decider")
# g.add_edge("investment_decider", END)
graph = g.compile()
'''