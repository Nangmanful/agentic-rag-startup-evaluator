# orchestrator.py
# 스타트업 투자평가 오케스트레이터 (LangGraph)
# - tech_summary_agent (그래프)
# - market_analyst (그래프 래퍼 노드)
# - competitor_analysis_agent (그래프)
# - investment_decider (함수형 노드)
#
# 실행 예:
#   python -m agents.core.orchestrator
#
# 필요 ENV:
#   OPENAI_API_KEY, (선택)TAVILY_API_KEY
#   INV_DECISION_* (선택) 가중치/임계치

from __future__ import annotations

import pathlib
import sys
from typing import Dict, Any, TypedDict, Annotated, Sequence, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 패키지 실행과 직접 실행 모두 지원
if __package__ is None:
    sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "resources" / "docs"

# ─────────────────────────────────────────────────────────────
# 1) 네가 올린 모듈 불러오기
# ─────────────────────────────────────────────────────────────
# 기술요약 그래프 (messages 입출력)
from agents.core.tech_summary_agent import build_graph as build_tech_graph

# 시장성 평가: market_analyst_node(state) 제공
from agents.market.market_analyst import market_analyst_node

# 경쟁사 비교 그래프(run_competitor_analysis 또는 build_graph)
from agents.competitor.competitor_analysis_agent import run_competitor_analysis

# 투자판단 함수형 노드
from agents.core.estimation_agent import investment_decider_node

from agents.core.report_generator_agent import build_graph as build_report_graph
report_graph = build_report_graph()
# ─────────────────────────────────────────────────────────────
# 2) 메인 State 정의
# ─────────────────────────────────────────────────────────────
class MainState(TypedDict):
    # 공통
    messages: Annotated[Sequence, add_messages]

    # 입력
    startup_info: dict          # {"name": str, "category": str, ...}
    document_path: str          # 시장성 분석용 PDF 경로 등(없으면 기본값)

    # 중간 산출
    tech_summary: str           # 기술요약 텍스트
    market_analysis: dict       # 시장성 평가 원본(에이전트 출력)
    competitor_output: dict     # 경쟁사 그래프 최종 상태(final_output 포함)

    # 투자판단 노드 입력용 어댑트 결과
    market_eval: dict
    competitor_eval: dict

    # 최종
    investment_decision: dict

# ─────────────────────────────────────────────────────────────
# 3) 어댑터: 각 서브그래프 → 투자판단 입력 스키마로 변환
# ─────────────────────────────────────────────────────────────
def adapt_market(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    market_analyst_node가 남긴 market_analysis -> investment_decider가 기대하는 market_eval로 변환
    기대 포맷(유연):
      market_eval = {
        "method": "scorecard" | "bessemer" | ...,
        "scorecard": {management_team:0~10, ...}  # scorecard일 때
        "bessemer_checklist": {...}               # bessemer일 때(0~5)
        "positives": [...], "risks": [...],
        "evidence_sources": [...]
      }
    """
    ma = state.get("market_analysis") or {}
    # 아래는 안전한 디폴트 매핑(너의 market_analyst 최종 보고서 키에 맞춰 수정 가능)
    method = "scorecard" if "scorecard_method" in ma else "bessemer" if "bessemer_checklist" in ma else "scorecard"

    scorecard = {}
    if "scorecard_method" in ma and isinstance(ma["scorecard_method"], dict):
        # 0~10 가정. 없으면 6 근처로 폴백
        scorecard = {
            "management_team":      float(ma["scorecard_method"].get("management_team", 6.0)),
            "market_size":          float(ma["scorecard_method"].get("market_size", 6.0)),
            "product_technology":   float(ma["scorecard_method"].get("product_technology", 6.0)),
            "competitive_environment": float(ma["scorecard_method"].get("competitive_environment", 5.5)),
            "marketing_sales":      float(ma["scorecard_method"].get("marketing_sales", 5.5)),
            "need_for_additional_investment": float(ma["scorecard_method"].get("need_for_additional_investment", 6.0)),
        }

    bessemer_checklist = {}
    if "bessemer_checklist" in ma and isinstance(ma["bessemer_checklist"], dict):
        bessemer_checklist = dict(ma["bessemer_checklist"])  # 0~5 가정

    positives = []
    risks = []
    if isinstance(ma.get("summary"), dict):
        positives = ma["summary"].get("positives", []) or []
        risks = ma["summary"].get("risks", []) or []

    sources = ma.get("evidence_sources", []) or ["internal-market"]  # 최소 1개 보장

    market_eval = {
        "method": method,
        "scorecard": scorecard,
        "bessemer_checklist": bessemer_checklist,
        "positives": positives,
        "risks": risks,
        "evidence_sources": sources,
    }
    return {"market_eval": market_eval}

def _score_from_positioning(pos: str) -> int:
    """
    경쟁 포지셔닝 텍스트를 1~5 점수로 매핑 (휴리스틱)
    """
    if not pos:
        return 3
    p = pos.lower()
    if any(k in p for k in ["leader", "strong", "dominant", "category leader"]):
        return 5
    if any(k in p for k in ["competitive", "on par", "parity"]):
        return 3
    if any(k in p for k in ["lagging", "weak", "behind"]):
        return 2
    return 4  # 기본 보수적 상향

def adapt_competitor(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    competitor_output(final_output 등) -> investment_decider가 기대하는 competitor_eval로 변환
    기대 포맷:
      competitor_eval = {
        "items": [{"name": str, "rating": 1~5}, ...],
        "evidence_sources": [...]
      }
    """
    co = state.get("competitor_output") or {}
    final_out = co.get("final_output") or {}

    # 1) 경쟁사 이름들
    names = final_out.get("competitors_found") or []
    if not isinstance(names, list):
        names = []

    # 2) 포지셔닝 기반 점수(1~5) 휴리스틱
    pos = final_out.get("competitive_positioning") or co.get("competitive_positioning") or ""
    base = _score_from_positioning(pos)

    # 3) 장단점 개수 기반 ±1 보정
    adv = final_out.get("competitive_advantages") or []
    dis = final_out.get("competitive_disadvantages") or []
    delta = 0
    if isinstance(adv, list) and isinstance(dis, list):
        if len(adv) >= len(dis) + 2:
            delta = 1
        elif len(dis) >= len(adv) + 2:
            delta = -1
    score = max(1, min(5, base + delta))

    # 4) items 구성
    if names:
        items = [{"name": n, "rating": score} for n in names[:5]]
    else:
        items = [{"name": "peer_avg", "rating": score}]

    # 5) 증거 소스 최소 1개 보장
    sources = ["internal-competitor"]

    return {"competitor_eval": {"items": items, "evidence_sources": sources}}

# ─────────────────────────────────────────────────────────────
# 4) 서브그래프/노드 래퍼
# ─────────────────────────────────────────────────────────────
def tech_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    기술요약 서브그래프 실행 → tech_summary 문자열만 추출
    (tech_summary_agent는 messages 기반 그래프)  :contentReference[oaicite:8]{index=8}
    """
    graph = build_tech_graph()
    out = graph.invoke({"messages": state.get("messages", [])})
    # 최종 메시지 텍스트만 저장
    msg_list = out.get("messages") or []
    text = ""
    if msg_list:
        last = msg_list[-1]
        text = getattr(last, "content", "") if hasattr(last, "content") else str(last)
    return {"tech_summary": text}

def market_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    시장성 평가 노드 호출 (이미 래퍼 제공)  :contentReference[oaicite:9]{index=9}
    """
    # market_analyst_node는 state를 받아 {"market_analysis": {...}}를 반환
    startup_name = state.get("startup_info", {}).get("name", "Unknown")
    res = market_analyst_node({
        "startup_name": startup_name,
        "document_path": state.get("document_path", str(DOCS_DIR / f"{startup_name}_IR.pdf"))
    })
    return res  # {"market_analysis": {...}}

def competitor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    경쟁사 비교 서브그래프 실행 → 최종 상태(final_output 등) 회수  :contentReference[oaicite:10]{index=10}
    """
    company = state.get("startup_info", {}).get("name", "Target Startup")
    ts = state.get("tech_summary", "") or "No tech summary"
    info = state.get("startup_info", {}) or {}
    final_state = run_competitor_analysis(company_name=company, tech_summary=ts, startup_info=info)
    return {"competitor_output": final_state}

def invest_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    투자판단 함수형 노드 호출 전, 어댑터로 스키마 맞추기  :contentReference[oaicite:11]{index=11}
    """
    state.update(adapt_market(state))
    state.update(adapt_competitor(state))
    return investment_decider_node(state)

# ─────────────────────────────────────────────────────────────
# 5) 메인 그래프 컴파일
# ─────────────────────────────────────────────────────────────
def build_orchestrator():
    workflow = StateGraph(MainState)

    workflow.add_node("tech_summary", tech_node)
    workflow.add_node("market_eval_raw", market_node)
    workflow.add_node("competitor_raw", competitor_node)
    workflow.add_node("invest", invest_node)

    workflow.add_edge(START, "tech_summary")
    workflow.add_edge("tech_summary", "market_eval_raw")
    workflow.add_edge("market_eval_raw", "competitor_raw")
    workflow.add_edge("competitor_raw", "invest")
    workflow.add_edge("invest", END)

    return workflow.compile()

# ─────────────────────────────────────────────────────────────
# 6) 예시 실행
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    graph = build_orchestrator()

    example = {
        "messages": [("user", "이 스타트업의 기술·시장·경쟁사를 종합해 투자 판단을 내려줘.")],
        "startup_info": {"name": "Lunit", "category": "Medical AI"},
        # 없다면 market_node에서 기본 경로 생성
        "document_path": str(DOCS_DIR / "Lunit_IR_2025.pdf"),
    }

    final = graph.invoke(example, config={"recursion_limit": 100})
    decision = final.get("investment_decision", {})
    print("\n" + "="*80)
    print("🧭 투자 판단 결과")
    print("="*80)
    print(decision)
    report_out = report_graph.invoke(final)
    print(report_out["report_path"])
