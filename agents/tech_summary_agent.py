
# agents/02_tech_summary_agent.py
# ------------------------------------------------------------
# 기술 요약 에이전트 (담당: 신민석)
# - 기존 템플릿을 최대한 유지하면서, 도메인만 "의료 AI 스타트업"으로 설명을 보강
# - ipynb가 아니라 .py로 동작하도록 구성
# - 나중에 단일 서비스로 합치기 쉽도록 구조/이름/흐름은 템플릿과 동일
# ------------------------------------------------------------

import os
from dotenv import load_dotenv

# 로깅/세션 설정
from langchain_teddynote import logging as tnote_logging
tnote_logging.langsmith("CH15-Agentic-RAG")

# Core imports
from typing import Annotated, Literal, Sequence, TypedDict
from pydantic import BaseModel, Field

# LangChain imports
from langchain import hub
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI

# LangGraph imports
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# Custom imports (opentutorial / teddynote)
from langchain_opentutorial.rag.pdf import PDFRetrievalChain
from langchain_teddynote.messages import random_uuid, stream_graph
from langchain_teddynote.models import LLMs, get_model_name

# -----------------------------
# 0) 환경 변수/모델 설정
# -----------------------------
load_dotenv()
# 템플릿과 동일한 헬퍼 사용 (추후 단일 서비스로 병합 시 호환성↑)
MODEL_NAME = get_model_name(LLMs.GPT4o_MINI)  # 필요 시 환경변수로 교체 가능 (e.g., os.getenv("OPENAI_MODEL"))

# -----------------------------
# 1) 파일 경로 설정
# -----------------------------
# 템플릿 유지: PDF 기반 RAG. 의료 AI 스타트업 관련 백서/IR/Paper 등을 data/ 폴더에 추가하세요.
# 예시 파일은 기존 템플릿의 SPRI 리포트를 그대로 남겨둡니다(삭제 X) — 도메인 파일을 추가로 넣어 확장 사용.
file_path = [
    "health.pdf",
    # 아래에 의료 AI 스타트업 관련 PDF를 추가하세요.
    # "data/medical_ai_startup_landscape_2025.pdf",
    # "data/startup_X_IR_2025Q3.pdf",
]

# -----------------------------
# 2) PDF 체인/리트리버 생성
# -----------------------------
pdf_file = PDFRetrievalChain(file_path).create_chain()
pdf_retriever = pdf_file.retriever
pdf_chain = pdf_file.chain

retriever_tool = create_retriever_tool(
    pdf_retriever,
    "pdf_retriever",
    (
        "Search and return information from domain PDFs (focus: Medical AI startups). "
        "It may include agent trends (SPRi, Dec 2024) and any added medical-AI startup docs (IR, whitepapers, papers)."
    ),
    document_prompt=PromptTemplate.from_template(
        "<document><context>{page_content}</context>"
        "<metadata><source>{source}</source><page>{page}</page></metadata></document>"
    ),
)

tools = [retriever_tool]

# -----------------------------
# 3) LangGraph State 정의
# -----------------------------
class AgentState(TypedDict):
    """에이전트 상태 정의 (템플릿 유지)"""
    messages: Annotated[Sequence[BaseMessage], add_messages]

class Grade(BaseModel):
    """관련성 평가 이진 스키마 (템플릿 유지)"""
    binary_score: str = Field(
        description="Response 'yes' if the document is relevant to the question or 'no' if it is not."
    )

# -----------------------------
# 4) 문서 관련성 평가 라우팅
# -----------------------------
def grade_documents(state) -> Literal["generate", "rewrite"]:
    """문서 관련성 평가 (템플릿 유지)"""
    model = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True)
    llm_with_tool = model.with_structured_output(Grade)

    prompt = PromptTemplate(
        template=(
            "You are a grader assessing relevance of a retrieved document to a user question.\n"
            "Here is the retrieved document:\n\n{context}\n\n"
            "Here is the user question: {question}\n"
            "If the document contains keyword(s) or semantic meaning related to the user question, "
            "grade it as relevant.\n"
            "Give a binary score 'yes' or 'no'."
        ),
        input_variables=["context", "question"],
    )

    chain = prompt | llm_with_tool

    messages = state["messages"]
    last_message = messages[-1]
    question = messages[0].content
    retrieved_docs = last_message.content

    scored_result = chain.invoke({"question": question, "context": retrieved_docs})
    score = scored_result.binary_score

    if score.strip().lower() == "yes":
        print("==== [DECISION: DOCS RELEVANT] ====")
        return "generate"
    else:
        print("==== [DECISION: DOCS NOT RELEVANT] ====")
        return "rewrite"

# -----------------------------
# 5) Agent 노드
# -----------------------------
def agent(state):
    """에이전트 (템플릿 유지)"""
    messages = state["messages"]
    model = ChatOpenAI(temperature=0, streaming=True, model=MODEL_NAME)
    model = model.bind_tools(tools)
    response = model.invoke(messages)
    return {"messages": [response]}

# -----------------------------
# 6) Rewrite 노드
# -----------------------------
def rewrite(state):
    """질문 재작성 (템플릿 유지) — 의료 AI 스타트업 질의에 유리한 개선 유도"""
    print("==== [QUERY REWRITE] ====")
    messages = state["messages"]
    question = messages[0].content

    msg = [
        HumanMessage(
            content=(
                "Look at the input and infer the underlying semantic intent.\n"
                "This system targets Medical AI startup analysis (tech stacks, FDA/CE status, data pipeline, "
                "regulatory notes, model types, clinical workflow integration). "
                "Improve the question for better retrieval.\n"
                "-----\n"
                f"{question}\n"
                "-----\n"
                "Formulate an improved question:"
            )
        )
    ]

    model = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True)
    response = model.invoke(msg)
    return {"messages": [response]}

# -----------------------------
# 7) Generate 노드 (최종 응답)
# -----------------------------
def generate(state):
    """최종 답변 생성 (템플릿 유지)"""
    messages = state["messages"]
    question = messages[0].content
    docs = messages[-1].content

    prompt = hub.pull("teddynote/rag-prompt")
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0, streaming=True)
    rag_chain = prompt | llm | StrOutputParser()

    response = rag_chain.invoke({"context": docs, "question": question})
    return {"messages": [response]}

# -----------------------------
# 8) 그래프 구성/실행 유틸
# -----------------------------
def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent)
    retrieve = ToolNode([retriever_tool])
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("rewrite", rewrite)
    workflow.add_node("generate", generate)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "retrieve", END: END},
    )
    workflow.add_conditional_edges("retrieve", grade_documents)
    workflow.add_edge("generate", END)
    workflow.add_edge("rewrite", "agent")

    return workflow.compile()

def main():
    from langchain_teddynote.graphs import visualize_graph

    graph = build_graph()
    visualize_graph(graph)
    print(graph.get_graph().draw_ascii())

    config = RunnableConfig(recursion_limit=20, configurable={"thread_id": random_uuid()})

    # 예시 1) 문서 기반 질문 (의료 AI 스타트업에도 유효한 "에이전트" 트렌드 질문)
    inputs = {"messages": [("user", "구글의 Project Astra의 핵심 기능은? 의료 AI 워크플로우에 적용 가능성은?")]}
    stream_graph(graph, inputs, config, ["agent", "rewrite", "generate"])

    # 예시 2) 문서가 없을 수도 있는 질문 (rewrite → agent 루프 확인)
    inputs = {"messages": [("user", "도널드 트럼프 대통령")]}
    stream_graph(graph, inputs, config, ["agent", "rewrite", "generate"])

if __name__ == "__main__":
    main()

