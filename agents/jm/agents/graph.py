"""
시장성 평가 에이전트 LangGraph 워크플로우 (v0.3.0 - 산업 뉴스 추가)
Reference: 22-LangGraph/03-LangGraph-Agent.ipynb
"""

from langgraph.graph import StateGraph, START, END

from jm.agents.state import MarketAnalysisState
from jm.agents.nodes import (
    initialize_analysis,
    search_industry_news,
    select_next_question,
    retrieve_documents,
    grade_relevance,
    rewrite_question,
    web_search_fallback,
    generate_answer,
    skip_question,
    calculate_scorecard,
    analyze_industry_insights,
    finalize_report
)


# ========== 라우터 함수들 ==========

def route_after_relevance_grade(state: MarketAnalysisState) -> str:
    """
    [라우터 1] 관련성 평가 후 경로 결정

    - is_relevant == "yes" → generate_answer
    - is_relevant == "no" → route_after_rewrite
    """
    if state["is_relevant"] == "yes":
        return "generate_answer"
    else:
        return "check_rewrite_count"


def route_after_rewrite_check(state: MarketAnalysisState) -> str:
    """
    [라우터 2] 재작성 횟수 확인 후 경로 결정

    개선점 (v0.2.1):
    - rewrite_count < 2 → rewrite_question (최대 2회 재작성 허용)
    - rewrite_count >= 2 → web_search_fallback
    """
    if state["rewrite_count"] < 2:
        return "rewrite_question"
    else:
        return "web_search_fallback"


def route_after_web_search_grade(state: MarketAnalysisState) -> str:
    """
    [라우터 3] 웹 검색 후 관련성 평가 결과에 따른 경로 결정

    개선점 (v0.2.1): 무한 루프 방지
    - is_relevant == "yes" → generate_answer
    - is_relevant == "no" → skip_question (더 이상 시도 안 함)
    """
    if state["is_relevant"] == "yes":
        return "generate_answer"
    else:
        return "skip_question"


def check_completion(state: MarketAnalysisState) -> str:
    """
    [라우터 4] 모든 질문 완료 여부 확인

    - 남은 질문 있음 → select_next_question
    - 모든 질문 완료 → calculate_scorecard
    """
    current_idx = state["current_question_idx"]
    total_questions = len(state["sub_questions"])

    if current_idx < total_questions:
        return "select_next_question"
    else:
        return "calculate_scorecard"


# ========== LangGraph 워크플로우 구축 ==========

def build_market_analysis_graph():
    """시장성 평가 에이전트 그래프 구축 (v0.3.0 - 산업 뉴스 추가)"""

    # StateGraph 초기화
    workflow = StateGraph(MarketAnalysisState)

    # ========== 노드 추가 ==========
    workflow.add_node("initialize", initialize_analysis)
    workflow.add_node("industry_news", search_industry_news)  # 🆕 v0.3.0
    workflow.add_node("select_question", select_next_question)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("grade", grade_relevance)
    workflow.add_node("rewrite", rewrite_question)
    workflow.add_node("web_search", web_search_fallback)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("skip", skip_question)
    workflow.add_node("scorecard", calculate_scorecard)
    workflow.add_node("industry_insights", analyze_industry_insights)  # 🆕 v0.3.0
    workflow.add_node("finalize", finalize_report)

    # 중간 라우터 노드 (조건 분기용)
    workflow.add_node("check_rewrite_count", lambda s: s)  # Pass-through 노드
    workflow.add_node("grade_web_result", grade_relevance)  # 웹 검색 결과 평가

    # ========== 엣지 연결 ==========

    # START → initialize
    workflow.add_edge(START, "initialize")

    # initialize → industry_news (🆕 v0.3.0)
    workflow.add_edge("initialize", "industry_news")

    # industry_news → select_question (🆕 v0.3.0)
    workflow.add_edge("industry_news", "select_question")

    # select_question → retrieve
    workflow.add_edge("select_question", "retrieve")

    # retrieve → grade
    workflow.add_edge("retrieve", "grade")

    # grade → [조건 분기 1]
    workflow.add_conditional_edges(
        "grade",
        route_after_relevance_grade,
        {
            "generate_answer": "generate",
            "check_rewrite_count": "check_rewrite_count"
        }
    )

    # check_rewrite_count → [조건 분기 2]
    workflow.add_conditional_edges(
        "check_rewrite_count",
        route_after_rewrite_check,
        {
            "rewrite_question": "rewrite",
            "web_search_fallback": "web_search"
        }
    )

    # rewrite → retrieve (루프백)
    workflow.add_edge("rewrite", "retrieve")

    # web_search → grade_web_result
    workflow.add_edge("web_search", "grade_web_result")

    # grade_web_result → [조건 분기 3]
    workflow.add_conditional_edges(
        "grade_web_result",
        route_after_web_search_grade,
        {
            "generate_answer": "generate",
            "skip_question": "skip"
        }
    )

    # generate / skip → [조건 분기 4: 완료 확인]
    workflow.add_conditional_edges(
        "generate",
        check_completion,
        {
            "select_next_question": "select_question",
            "calculate_scorecard": "scorecard"
        }
    )

    workflow.add_conditional_edges(
        "skip",
        check_completion,
        {
            "select_next_question": "select_question",
            "calculate_scorecard": "scorecard"
        }
    )

    # scorecard → industry_insights (🆕 v0.3.0)
    workflow.add_edge("scorecard", "industry_insights")

    # industry_insights → finalize (🆕 v0.3.0)
    workflow.add_edge("industry_insights", "finalize")

    # finalize → END
    workflow.add_edge("finalize", END)

    # 그래프 컴파일
    app = workflow.compile()

    return app


# ========== 그래프 시각화 (선택) ==========

def visualize_graph(app):
    """그래프 시각화 (langchain_teddynote 필요)"""
    try:
        from langchain_teddynote.graphs import visualize_graph
        return visualize_graph(app)
    except ImportError:
        print("⚠️ langchain_teddynote가 설치되지 않아 시각화를 건너뜁니다.")
        return None
