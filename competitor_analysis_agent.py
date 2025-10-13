# ------------------------------------------------------------
# 경쟁사 비교 에이전트 (담당: 정광진)
# - 기존 기술 요약 에이전트 템플릿을 최대한 유지
# - 기술 요약 에이전트의 output을 입력으로 받아 경쟁사 비교 수행
# - TavilySearch를 활용한 실시간 웹 검색으로 경쟁사 정보 수집
# - 5점 척도 평가 출력
# ------------------------------------------------------------

import os
import json
from dotenv import load_dotenv

# 로깅/세션 설정
from langchain_teddynote import logging as tnote_logging
tnote_logging.langsmith("CH15-Competitor-Analysis")

# Core imports
from typing import Annotated, Literal, Sequence, TypedDict
from pydantic import BaseModel, Field

# LangChain imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# LangGraph imports
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# Custom imports (teddynote)
from langchain_teddynote.messages import random_uuid, stream_graph
from langchain_teddynote.models import LLMs, get_model_name
from langchain_teddynote.tools.tavily import TavilySearch

# -----------------------------
# 0) 환경 변수/모델 설정
# -----------------------------
load_dotenv()
MODEL_NAME = get_model_name(LLMs.GPT_4o_mini)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# -----------------------------
# 1) 도구 정의: Tavily Web Search
# -----------------------------
@tool
def search_competitors(query: str) -> str:
    """
    Search for competitors in the same industry/category using Tavily web search.
    Use this to find competing startups and their basic information.
    
    Args:
        query: Search query (e.g., "Qure.ai competitors medical AI imaging")
    
    Returns:
        Competitor information from web search results
    """
    try:
        tavily_tool = TavilySearch()
        search_results = tavily_tool.search(
            query=query,
            topic="general",  # 일반 주제 (경쟁사 정보)
            days=365,  # 최근 1년 내 정보
            max_results=5,  # 최대 5개 결과
            format_output=True,  # 결과 포맷팅
        )
        
        # 검색 결과를 문자열로 결합
        formatted_results = "\n\n".join(search_results)
        return f"Web search results for: {query}\n\n{formatted_results}"
        
    except Exception as e:
        # 에러 발생 시 기본 메시지 반환
        return f"Error searching for competitors: {str(e)}\nPlease try with a different query."

@tool
def fetch_competitor_details(competitor_name: str, focus_area: str = "technology funding partnerships") -> str:
    """
    Fetch detailed information about a specific competitor using Tavily web search.
    Use this after identifying competitors to get more detailed information.
    
    Args:
        competitor_name: Name of the competitor company
        focus_area: Specific areas to focus on (default: "technology funding partnerships")
    
    Returns:
        Detailed company information from web search
    """
    try:
        tavily_tool = TavilySearch()
        
        # 여러 측면에서 검색하여 종합적인 정보 수집
        queries = [
            f"{competitor_name} technology products features",
            f"{competitor_name} funding investment valuation",
            f"{competitor_name} FDA approval CE mark certification",
            f"{competitor_name} partnerships customers"
        ]
        
        all_results = []
        for query in queries[:2]:  # 처음 2개 쿼리만 실행 (토큰 절약)
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

# 도구 리스트
tools = [search_competitors, fetch_competitor_details]

# -----------------------------
# 2) LangGraph State 정의
# -----------------------------
class AgentState(TypedDict):
    """에이전트 상태 정의 - 기존 템플릿 유지 + 확장"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    startup_info: dict  # 기술 요약 에이전트에서 받은 스타트업 정보
    tech_summary: str   # 기술 요약 에이전트의 출력
    competitor_list: list  # 발견된 경쟁사 리스트
    competitor_analysis: dict  # 경쟁사 비교 분석 결과
    final_score: int  # 최종 5점 척도 점수

class CompetitorGrade(BaseModel):
    """경쟁사 정보 충분성 평가 스키마"""
    binary_score: str = Field(
        description="Response 'yes' if sufficient competitor information is gathered, or 'no' if more information is needed."
    )

class CompetitiveScore(BaseModel):
    """경쟁력 평가 점수 스키마"""
    score: int = Field(
        description="Competitive score from 1 to 5",
        ge=1,
        le=5
    )
    reasoning: str = Field(
        description="Reasoning for the score"
    )

# -----------------------------
# 3) 경쟁사 정보 충분성 평가
# -----------------------------
def grade_competitor_info(state) -> Literal["analyze", "search_more"]:
    """경쟁사 정보가 충분한지 평가 (기존 grade_documents 패턴)"""
    model = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True)
    llm_with_tool = model.with_structured_output(CompetitorGrade)

    prompt = PromptTemplate(
        template=(
            "You are evaluating whether sufficient competitor information has been gathered.\n"
            "Startup: {startup_name}\n"
            "Tech Summary: {tech_summary}\n\n"
            "Gathered Information:\n{competitor_info}\n\n"
            "Evaluate if we have enough information about:\n"
            "1. At least 3 competitors identified\n"
            "2. Key technology details for each\n"
            "3. Market position/funding information\n\n"
            "If sufficient, respond 'yes'. If need more details, respond 'no'."
        ),
        input_variables=["startup_name", "tech_summary", "competitor_info"],
    )

    chain = prompt | llm_with_tool

    messages = state["messages"]
    startup_info = state.get("startup_info", {})
    tech_summary = state.get("tech_summary", "")
    competitor_info = messages[-1].content if messages else ""

    scored_result = chain.invoke({
        "startup_name": startup_info.get("name", "Unknown"),
        "tech_summary": tech_summary,
        "competitor_info": competitor_info
    })
    
    score = scored_result.binary_score

    if score.strip().lower() == "yes":
        print("==== [DECISION: SUFFICIENT COMPETITOR INFO] ====")
        return "analyze"
    else:
        print("==== [DECISION: NEED MORE COMPETITOR INFO] ====")
        return "search_more"

# -----------------------------
# 4) Agent 노드 (도구 사용 판단)
# -----------------------------
def agent(state):
    """에이전트 - 경쟁사 검색 도구 사용 결정 (기존 agent 패턴)"""
    messages = state["messages"]
    model = ChatOpenAI(temperature=0, streaming=True, model=MODEL_NAME)
    model = model.bind_tools(tools)
    response = model.invoke(messages)
    return {"messages": [response]}

# -----------------------------
# 5) Search More 노드 (추가 검색)
# -----------------------------
def search_more(state):
    """경쟁사 정보 부족 시 추가 검색 (기존 rewrite 패턴)"""
    print("==== [SEARCHING MORE COMPETITORS] ====")
    messages = state["messages"]
    startup_info = state.get("startup_info", {})
    competitor_list = state.get("competitor_list", [])

    startup_name = startup_info.get("name", "Unknown")
    category = startup_info.get("category", "AI")
    
    # 이전 검색 결과 분석
    has_competitor_names = any("competitor" in msg.content.lower() for msg in messages if hasattr(msg, 'content'))
    
    if has_competitor_names and len([msg for msg in messages if "Detailed information" in str(msg.content)]) < 2:
        # 경쟁사 이름은 있지만 상세 정보가 부족한 경우
        msg = [
            HumanMessage(
                content=(
                    f"Get detailed information about the main competitors of {startup_name}. "
                    f"Focus on their technology, FDA/CE certifications, funding rounds, "
                    f"and key partnerships. Search for recent news and updates."
                )
            )
        ]
    else:
        # 경쟁사 리스트 자체가 부족한 경우
        msg = [
            HumanMessage(
                content=(
                    f"Search for the top competitors of {startup_name} in the {category} industry. "
                    f"Find companies that offer similar products or services in medical imaging AI, "
                    f"diagnostic AI, or healthcare AI. Include information about their technology, "
                    f"market position, and funding."
                )
            )
        ]

    model = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True)
    response = model.invoke(msg)
    return {"messages": [response]}

# -----------------------------
# 6) Analyze 노드 (비교 분석)
# -----------------------------
def analyze(state):
    """경쟁사 비교 분석 수행"""
    print("==== [ANALYZING COMPETITORS] ====")
    messages = state["messages"]
    startup_info = state.get("startup_info", {})
    tech_summary = state.get("tech_summary", "")
    
    # 수집된 경쟁사 정보 추출
    competitor_info = "\n\n".join([
        msg.content for msg in messages 
        if hasattr(msg, 'content') and isinstance(msg.content, str)
    ])

    prompt = ChatPromptTemplate.from_template(
        """You are a venture capital analyst performing competitive analysis.

**Target Startup:**
Name: {startup_name}
Category: {category}
Technology Summary: {tech_summary}

**Competitor Information:**
{competitor_info}

**Analysis Framework:**
Compare the target startup against competitors across these dimensions:

1. Technology Differentiation (30%)
   - Unique technical capabilities
   - Innovation level
   - Technical barriers

2. Market Entry Barriers (25%)
   - Patents and IP
   - Regulatory approvals (FDA, CE, etc.)
   - Network effects

3. Funding & Growth (20%)
   - Total funding raised
   - Growth trajectory
   - Financial stability

4. Partnerships & Ecosystem (15%)
   - Strategic partnerships
   - Customer base
   - Market penetration

5. Validation & Certification (5%)
   - Clinical validations
   - Regulatory approvals
   - Published research

6. Brand Recognition (5%)
   - Market presence
   - Industry reputation

**Output Format:**
Provide a comprehensive comparison analysis with:
- Key strengths vs competitors
- Key weaknesses vs competitors
- Competitive positioning (Leader/Strong Challenger/Competitive/Weak/Very Weak)
- Specific evidence for each dimension
"""
    )

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0, streaming=True)
    chain = prompt | llm | StrOutputParser()

    response = chain.invoke({
        "startup_name": startup_info.get("name", "Target Startup"),
        "category": startup_info.get("category", "Technology"),
        "tech_summary": tech_summary,
        "competitor_info": competitor_info
    })

    return {"messages": [response], "competitor_analysis": {"analysis": response}}

# -----------------------------
# 7) Evaluate 노드 (5점 척도 평가)
# -----------------------------
def evaluate(state):
    """최종 경쟁력 점수 산출 (1-5점)"""
    print("==== [EVALUATING COMPETITIVE SCORE] ====")
    competitor_analysis = state.get("competitor_analysis", {})
    analysis_text = competitor_analysis.get("analysis", "")

    model = ChatOpenAI(temperature=0, model=MODEL_NAME)
    llm_with_structure = model.with_structured_output(CompetitiveScore)

    prompt = PromptTemplate(
        template=(
            "Based on the competitive analysis below, assign a score from 1 to 5:\n\n"
            "5 (Outstanding): Clear competitive advantage across most dimensions\n"
            "4 (Strong): Notable advantages, minor weaknesses\n"
            "3 (Competitive): On par with competitors, some differentiation\n"
            "2 (Weak): Behind competitors in most areas\n"
            "1 (Very Weak): Significant disadvantages, unclear differentiation\n\n"
            "Analysis:\n{analysis}\n\n"
            "Provide score (1-5) and reasoning."
        ),
        input_variables=["analysis"],
    )

    chain = prompt | llm_with_structure
    result = chain.invoke({"analysis": analysis_text})

    print(f"==== COMPETITIVE SCORE: {result.score}/5 ====")
    print(f"Reasoning: {result.reasoning}")

    return {
        "final_score": result.score,
        "competitor_analysis": {
            **competitor_analysis,
            "score": result.score,
            "reasoning": result.reasoning
        }
    }

# -----------------------------
# 8) 그래프 구성
# -----------------------------
def build_graph():
    """LangGraph 워크플로우 구성 (기존 템플릿 패턴)"""
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("agent", agent)
    retrieve = ToolNode(tools)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("search_more", search_more)
    workflow.add_node("analyze", analyze)
    workflow.add_node("evaluate", evaluate)

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
    
    # analyze 후 evaluate로
    workflow.add_edge("analyze", "evaluate")
    
    # evaluate 후 종료
    workflow.add_edge("evaluate", END)

    return workflow.compile()

# -----------------------------
# 9) 메인 실행 함수
# -----------------------------
def main():
    """메인 실행 함수"""
    from langchain_teddynote.graphs import visualize_graph

    # Tavily API 키 확인
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key.startswith("tvly-placeholder"):
        print("\n" + "="*80)
        print("⚠️  경고: Tavily API 키가 설정되지 않았습니다!")
        print("실제 웹 검색을 수행하려면 .env 파일에 다음을 추가하세요:")
        print("TAVILY_API_KEY=your_actual_tavily_api_key_here")
        print("="*80 + "\n")

    graph = build_graph()
    
    # 그래프 시각화
    visualize_graph(graph)
    print(graph.get_graph().draw_ascii())

    # 실행 설정
    config = RunnableConfig(
        recursion_limit=25,
        configurable={"thread_id": random_uuid()}
    )

    # ========================================
    # 예시 1: 기술 요약 에이전트의 output 시뮬레이션
    # ========================================
    startup_info = {
        "name": "Qure.ai",
        "category": "Medical AI Imaging",
        "founded": 2016,
        "location": "India"
    }

    tech_summary = """
    Qure.ai is a medical AI startup specializing in deep learning-based diagnostic solutions 
    for medical imaging. Core technologies include:
    
    1. qXR: Chest X-ray interpretation AI (tuberculosis, pneumonia, lung nodules)
    2. qER: Head CT scan analysis for acute neurological conditions
    3. qTrack: Tuberculosis treatment monitoring
    
    Key Strengths:
    - FDA 510(k) cleared for qXR
    - CE marked for multiple products
    - Deployed in 70+ countries
    - Strong focus on emerging markets
    - Partnerships with major healthcare providers
    
    Technology Stack:
    - Deep learning (CNN-based architectures)
    - Cloud-based platform
    - DICOM integration
    - Automated workflow integration
    """

    initial_message = HumanMessage(
        content=(
            f"Analyze competitors for {startup_info['name']}, "
            f"a {startup_info['category']} startup. "
            f"Search the web to find major competitors and compare their competitive position. "
            f"Focus on medical AI imaging companies with FDA/CE approvals."
        )
    )

    inputs = {
        "messages": [initial_message],
        "startup_info": startup_info,
        "tech_summary": tech_summary,
        "competitor_list": [],
        "competitor_analysis": {},
        "final_score": 0
    }

    print("\n" + "="*80)
    print("🔍 경쟁사 비교 에이전트 실행 시작 (Tavily Web Search)")
    print("="*80 + "\n")

    # 그래프 실행 (스트리밍)
    stream_graph(
        graph, 
        inputs, 
        config, 
        ["agent", "search_more", "analyze", "evaluate"]
    )

    print("\n" + "="*80)
    print("✅ 경쟁사 비교 에이전트 실행 완료")
    print("="*80 + "\n")

    # ========================================
    # 최종 결과 출력 함수
    # ========================================
    def print_final_results(final_state):
        """최종 분석 결과 출력"""
        print("\n" + "="*80)
        print("📊 최종 경쟁사 비교 분석 결과")
        print("="*80)
        
        analysis = final_state.get("competitor_analysis", {})
        score = final_state.get("final_score", 0)
        
        print(f"\n🎯 경쟁력 점수: {score}/5")
        print(f"\n📝 평가 근거:\n{analysis.get('reasoning', 'N/A')}")
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
