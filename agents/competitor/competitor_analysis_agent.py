# ------------------------------------------------------------
# competitor_analysis_agent.py
# 경쟁사 비교 에이전트 메인 로직
# - 원본 코드의 구조를 유지하면서 모듈화
# - RAG 통합 준비
# ------------------------------------------------------------

import os
import re
from typing import Literal, Optional
from dotenv import load_dotenv

# 로깅/세션 설정
from langchain_teddynote import logging as tnote_logging
tnote_logging.langsmith("CH15-Competitor-Analysis")

# LangChain imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# LangGraph imports
from langgraph.graph import END, START, StateGraph

# ToolNode 대체: 직접 구현 (langgraph 0.6+에서 ToolNode가 제거됨)
from langchain_core.messages import AIMessage, ToolMessage
from typing import Sequence

def create_tool_node(tools: Sequence):
    """도구 실행 노드 생성 (ToolNode 대체)"""
    tools_by_name = {tool.name: tool for tool in tools}

    def tool_node(state):
        """도구 실행"""
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage) or not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"messages": []}

        tool_messages = []
        for tool_call in last_message.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if tool:
                try:
                    result = tool.invoke(tool_call["args"])
                    tool_messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                    )
                except Exception as e:
                    tool_messages.append(
                        ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call["id"])
                    )

        return {"messages": tool_messages}

    return tool_node

def tools_condition(state):
    """도구 사용 여부 판단 (tools_condition 대체)"""
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

# Custom imports
from langchain_teddynote.messages import random_uuid, stream_graph
from langchain_teddynote.models import LLMs, get_model_name
from langchain_teddynote.tools.tavily import TavilySearch

# Local imports
from .schemas import (
    CompetitorAgentState,
    CompetitorGrade,
    CompetitorAnalysisParsed,
    CompetitorAnalysisOutput
)
from .prompts import (
    GRADE_COMPETITOR_INFO_PROMPT,
    COMPETITOR_ANALYSIS_PROMPT,
    PARSE_ANALYSIS_PROMPT
)
# -----------------------------
# 환경 변수 설정
# -----------------------------
load_dotenv()
MODEL_NAME = get_model_name(LLMs.GPT4o_MINI)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# -----------------------------
# 도구 정의
# -----------------------------
@tool
def search_competitors(query: str) -> str:
    """
    Search for competitors using Tavily web search.

    Args:
        query: Search query for finding competitors

    Returns:
        Competitor information from web search
    """
    try:
        tavily_tool = TavilySearch()
        search_results = tavily_tool.search(
            query=query,
            topic="general",
            days=365,
            max_results=5,
            format_output=True,
        )
        formatted_results = "\n\n".join(search_results)
        return f"Web search results for: {query}\n\n{formatted_results}"
    except Exception as e:
        return f"Error searching competitors: {str(e)}"


@tool
def fetch_competitor_details(competitor_name: str, focus_area: str = "technology funding") -> str:
    """
    Fetch detailed information about a specific competitor.

    Args:
        competitor_name: Name of the competitor
        focus_area: Focus areas for search

    Returns:
        Detailed competitor information
    """
    try:
        tavily_tool = TavilySearch()
        queries = [
            f"{competitor_name} technology products features",
            f"{competitor_name} funding investment valuation",
        ]

        all_results = []
        for query in queries:
            search_results = tavily_tool.search(
                query=query,
                topic="general",
                days=365,
                max_results=3,
                format_output=True,
            )
            all_results.extend(search_results)

        formatted_results = "\n\n".join(all_results)
        return f"Detailed information about {competitor_name}:\n\n{formatted_results}"
    except Exception as e:
        return f"Error fetching details for {competitor_name}: {str(e)}"


tools = [search_competitors, fetch_competitor_details]


# -----------------------------
# 노드 함수들
# -----------------------------
def agent(state):
    """에이전트 - 도구 사용 결정"""
    messages = state["messages"]
    model = ChatOpenAI(temperature=0, streaming=True, model=MODEL_NAME)
    model = model.bind_tools(tools)
    response = model.invoke(messages)
    return {"messages": [response]}


def grade_competitor_info(state) -> Literal["analyze", "search_more"]:
    """경쟁사 정보 충분성 평가"""
    model = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True)
    llm_with_tool = model.with_structured_output(CompetitorGrade)

    messages = state["messages"]
    startup_info = state.get("startup_info", {})
    tech_summary = state.get("tech_summary", "")

    # 메시지에서 경쟁사 정보 추출
    competitor_info = "\n\n".join([
        msg.content for msg in messages
        if hasattr(msg, 'content') and isinstance(msg.content, str)
    ])

    scored_result = llm_with_tool.invoke(
        GRADE_COMPETITOR_INFO_PROMPT.format(
            startup_name=startup_info.get("name", "Unknown"),
            category=startup_info.get("category", "Technology"),
            tech_summary=tech_summary,
            competitor_info=competitor_info
        )
    )

    decision = scored_result.binary_score.strip().lower()

    if decision == "yes":
        print("==== [DECISION: SUFFICIENT COMPETITOR INFO] ====")
        return "analyze"
    else:
        print("==== [DECISION: NEED MORE COMPETITOR INFO] ====")
        return "search_more"


def search_more(state):
    """추가 경쟁사 정보 검색"""
    print("==== [SEARCHING MORE COMPETITORS] ====")
    messages = state["messages"]
    startup_info = state.get("startup_info", {})

    startup_name = startup_info.get("name", "Unknown")
    category = startup_info.get("category", "AI")

    # 정보 부족 판단
    has_details = any("Detailed information" in str(msg.content) for msg in messages)

    if has_details:
        # 더 많은 경쟁사 찾기
        msg_content = (
            f"Search for additional competitors of {startup_name} in the {category} industry. "
            f"Find companies with similar products and compare their market position."
        )
    else:
        # 기존 경쟁사 상세 정보 수집
        msg_content = (
            f"Get detailed information about the main competitors of {startup_name}. "
            f"Focus on their technology, FDA/CE certifications, funding, and partnerships."
        )

    msg = [HumanMessage(content=msg_content)]
    model = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True)
    response = model.invoke(msg)
    return {"messages": [response]}


def analyze(state):
    """경쟁사 비교 분석"""
    print("==== [ANALYZING COMPETITORS] ====")
    messages = state["messages"]
    startup_info = state.get("startup_info", {})
    tech_summary = state.get("tech_summary", "")
    rag_context = "Industry context not provided."

    # 경쟁사 정보 추출
    competitor_info = "\n\n".join([
        msg.content for msg in messages
        if hasattr(msg, 'content') and isinstance(msg.content, str)
    ])

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0, streaming=True)
    chain = COMPETITOR_ANALYSIS_PROMPT | llm | StrOutputParser()

    response = chain.invoke({
        "startup_name": startup_info.get("name", "Target Startup"),
        "category": startup_info.get("category", "Technology"),
        "tech_summary": tech_summary,
        "competitor_info": competitor_info,
        "rag_context": rag_context
    })

    return {
        "messages": [AIMessage(content=response)],
        "competitor_analysis": {
            "analysis": response,
            "target_startup": startup_info.get("name", "Target Startup")
        }
    }


def parse_analysis(state):
    """분석 결과 파싱"""
    print("==== [PARSING ANALYSIS RESULTS] ====")
    competitor_analysis = state.get("competitor_analysis", {})
    analysis_text = competitor_analysis.get("analysis", "")

    model = ChatOpenAI(temperature=0, model=MODEL_NAME)
    llm_with_structure = model.with_structured_output(CompetitorAnalysisParsed)

    result = llm_with_structure.invoke(
        PARSE_ANALYSIS_PROMPT.format(analysis=analysis_text)
    )

    print(f"==== COMPETITIVE POSITIONING: {result.competitive_positioning} ====")
    print(f"Advantages: {len(result.competitive_advantages)} identified")
    print(f"Disadvantages: {len(result.competitive_disadvantages)} identified")

    return {
        "competitive_positioning": result.competitive_positioning,
        "competitive_advantages": result.competitive_advantages,
        "competitive_disadvantages": result.competitive_disadvantages,
        "competitor_analysis": {
            **competitor_analysis,
            "positioning": result.competitive_positioning,
            "advantages": result.competitive_advantages,
            "disadvantages": result.competitive_disadvantages,
            "summary": result.competitive_summary
        }
    }


def format_output(state):
    """최종 출력 포맷팅 (투자 판단 에이전트용)"""
    print("==== [FORMATTING OUTPUT] ====")

    # 상태에서 필요한 정보 추출
    messages = state["messages"]
    competitor_analysis = state.get("competitor_analysis", {})
    analysis_text = competitor_analysis.get("analysis", "")

    startup_name = competitor_analysis.get("target_startup", state.get("company_name", ""))

    def extract_competitors(text: str) -> list:
        patterns = [
            r"[Cc]ompetitors?\s+(?:like|such as|include|including)\s+([^.;]+)",
            r"[Vv]ersus\s+([^.;]+)",
            r"[Vv]s\.?\s+([^.;]+)",
            r"[Cc]ompared to\s+([^.;]+)",
        ]
        names = set()
        for pattern in patterns:
            for match in re.findall(pattern, text):
                parts = re.split(r",| and ", match)
                for raw_name in parts:
                    cleaned = raw_name.strip().strip(".:;")
                    if not cleaned:
                        continue
                    name_match = re.match(
                        r"([A-Z][A-Za-z0-9\.\-&]*(?:\s+[A-Z][A-Za-z0-9\.\-&]*)*)",
                        cleaned
                    )
                    if not name_match:
                        continue
                    candidate = name_match.group(1).strip()
                    if startup_name and candidate.lower() == startup_name.lower():
                        continue
                    if len(candidate) < 2:
                        continue
                    names.add(candidate)
        return sorted(names)

    competitors_found = []
    for source_text in [
        analysis_text,
        " ".join(state.get("competitive_advantages", [])),
        " ".join(state.get("competitive_disadvantages", [])),
    ]:
        competitors_found.extend(extract_competitors(source_text))

    if competitors_found:
        unique_competitors = []
        seen = set()
        for name in competitors_found:
            norm = name.lower()
            if norm not in seen:
                seen.add(norm)
                unique_competitors.append(name)
        competitors_found = unique_competitors[:5]
    else:
        competitors_found = ["No specific competitors identified"]

    # 6개 차원 분석 추출 (분석 텍스트에서 각 차원 섹션 추출)
    dimension_analysis = {}
    dimension_keywords = [
        "Technology Differentiation",
        "Market Entry Barriers",
        "Funding & Growth",
        "Partnerships & Ecosystem",
        "Validation & Certification",
        "Brand Recognition"
    ]

    for keyword in dimension_keywords:
        pattern = re.compile(
            rf"\*\*{re.escape(keyword)}.*?\*\*\s*(.*?)(?=\n\*\*|\Z)",
            re.DOTALL
        )
        match = pattern.search(analysis_text)
        if match:
            dimension_text = match.group(1).strip()
            dimension_analysis[keyword] = dimension_text or "Not analyzed"
        else:
            dimension_analysis[keyword] = "Not analyzed"

    output = CompetitorAnalysisOutput(
        competitors_found=competitors_found[:5] if competitors_found else ["No specific competitors identified"],
        competitive_positioning=state.get("competitive_positioning", competitor_analysis.get("positioning", "Competitive")),
        competitive_advantages=state.get("competitive_advantages", competitor_analysis.get("advantages", [])),
        competitive_disadvantages=state.get("competitive_disadvantages", competitor_analysis.get("disadvantages", [])),
        dimension_analysis=dimension_analysis,
        competitive_summary=competitor_analysis.get("summary", "No summary available"),
        full_analysis=analysis_text
    )

    print(f"📊 Final Output - Positioning: {output.competitive_positioning}")
    print(f"   Advantages: {len(output.competitive_advantages)}")
    print(f"   Disadvantages: {len(output.competitive_disadvantages)}")

    return {"final_output": output.dict()}


# -----------------------------
# 그래프 구성
# -----------------------------
def build_graph():
    """LangGraph 워크플로우 구성"""
    workflow = StateGraph(CompetitorAgentState)

    # 노드 추가
    workflow.add_node("agent", agent)
    retrieve = create_tool_node(tools)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("search_more", search_more)
    workflow.add_node("analyze", analyze)
    workflow.add_node("parse_analysis", parse_analysis)
    workflow.add_node("format_output", format_output)

    # 엣지 정의
    workflow.add_edge(START, "agent")

    # agent 후 조건부 분기
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "retrieve", END: END},
    )

    # retrieve 후 정보 충분성 평가
    workflow.add_conditional_edges(
        "retrieve",
        grade_competitor_info,
        {"analyze": "analyze", "search_more": "search_more"}
    )

    # search_more 후 다시 agent로
    workflow.add_edge("search_more", "agent")

    # analyze 후 parse_analysis
    workflow.add_edge("analyze", "parse_analysis")

    # parse_analysis 후 format_output으로
    workflow.add_edge("parse_analysis", "format_output")

    # format_output 후 종료
    workflow.add_edge("format_output", END)

    return workflow.compile()


# -----------------------------
# 그래프 실행 함수
# -----------------------------
def run_competitor_analysis(
    company_name: str,
    tech_summary: str,
    startup_info: dict,
    config: Optional[RunnableConfig] = None
):
    """
    경쟁사 비교 분석 실행

    Args:
        company_name: 회사명
        tech_summary: 기술 요약 (기술 요약 에이전트 출력)
        startup_info: 스타트업 정보 딕셔너리
        config: LangGraph 실행 설정

    Returns:
        최종 분석 결과
    """
    graph = build_graph()

    # 기본 config 생성
    if config is None:
        config = RunnableConfig(
            recursion_limit=25,
            configurable={"thread_id": random_uuid()}
        )

    initial_message = HumanMessage(
        content=(
            f"Analyze competitors for {company_name}, "
            f"a {startup_info.get('category', 'AI')} startup. "
            f"Search for main competitors and perform comparative analysis."
        )
    )

    inputs = {
        "messages": [initial_message],
        "company_name": company_name,
        "tech_summary": tech_summary,
        "core_technologies": [],
        "startup_info": startup_info,
        "competitor_list": [],
        "competitor_details": [],
        "competitor_analysis": {},
        "competitive_positioning": "",
        "competitive_advantages": [],
        "competitive_disadvantages": [],
        "market_position": "",
        "final_output": {}
    }

    # 그래프 실행
    final_state = graph.invoke(inputs, config)

    return final_state


if __name__ == "__main__":
    print("=" * 80)
    print("⚠️  이 파일은 모듈로 사용되도록 설계되었습니다.")
    print("실행하려면 test_agent.py를 사용하세요.")
    print("=" * 80)
