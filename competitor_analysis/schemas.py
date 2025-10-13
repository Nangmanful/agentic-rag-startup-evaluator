# ------------------------------------------------------------
# schemas.py
# Pydantic 스키마 정의 - 입출력 인터페이스 및 평가 스키마
# ------------------------------------------------------------

from typing import Annotated, List, Dict, Sequence
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# -----------------------------
# LangGraph State 정의
# -----------------------------
class CompetitorAgentState(TypedDict):
    """경쟁사 비교 에이전트 상태 정의"""
    # 입력 (다른 에이전트로부터)
    company_name: str
    tech_summary: str
    core_technologies: List[str]
    startup_info: dict

    # 내부 상태
    messages: Annotated[Sequence[BaseMessage], add_messages]
    competitor_list: List[Dict]  # [{name, url, description}, ...]
    competitor_details: List[Dict]  # 상세 정보
    rag_context: str  # RAG에서 검색한 산업 컨텍스트
    competitor_analysis: dict  # 비교 분석 결과

    # 출력 (투자 판단 에이전트)
    competitive_positioning: str  # Leader/Strong Challenger/Competitive/Weak/Very Weak
    competitive_advantages: List[str]
    competitive_disadvantages: List[str]
    market_position: str  # 호환성을 위해 유지


# -----------------------------
# 평가 스키마
# -----------------------------
class CompetitorGrade(BaseModel):
    """경쟁사 정보 충분성 평가 스키마"""
    binary_score: str = Field(
        description="Response 'yes' if sufficient competitor information is gathered, or 'no' if more information is needed."
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the decision"
    )

# -----------------------------
# 분석 결과 파싱 스키마
# -----------------------------
class CompetitorAnalysisParsed(BaseModel):
    """경쟁사 분석 결과 파싱 스키마"""
    competitive_positioning: str = Field(
        description="Overall market position: Leader/Strong Challenger/Competitive/Weak/Very Weak"
    )
    competitive_advantages: List[str] = Field(
        description="List of 3-5 key competitive advantages with evidence"
    )
    competitive_disadvantages: List[str] = Field(
        description="List of 3-5 key competitive disadvantages with evidence"
    )
    competitive_summary: str = Field(
        description="2-3 sentence summary of competitive position and outlook"
    )


# -----------------------------
# 출력 스키마 (투자 판단 에이전트용)
# -----------------------------
class CompetitorAnalysisOutput(BaseModel):
    """경쟁사 비교 에이전트 최종 출력 스키마"""
    competitors_found: List[str] = Field(
        description="List of main competitors identified"
    )
    competitive_positioning: str = Field(
        description="Overall market position assessment (Leader/Strong Challenger/Competitive/Weak/Very Weak)"
    )
    competitive_advantages: List[str] = Field(
        description="Key competitive advantages vs competitors (3-5 items with evidence)"
    )
    competitive_disadvantages: List[str] = Field(
        description="Key competitive disadvantages vs competitors (3-5 items with evidence)"
    )
    dimension_analysis: Dict[str, str] = Field(
        description="Dimension-by-dimension comparative analysis (6 dimensions)"
    )
    competitive_summary: str = Field(
        description="2-3 sentence summary of competitive position and outlook"
    )
    full_analysis: str = Field(
        description="Complete competitive analysis text"
    )


# -----------------------------
# Market Position 설명
# -----------------------------
MARKET_POSITION_DESCRIPTIONS = {
    "Leader": {
        "description": "시장 선도 기업",
        "criteria": "Most dimensions show clear advantages, strong differentiation"
    },
    "Strong Challenger": {
        "description": "강력한 도전자",
        "criteria": "Notable advantages in key dimensions, competitive positioning"
    },
    "Competitive": {
        "description": "경쟁력 있는 포지션",
        "criteria": "On par with competitors, some differentiation exists"
    },
    "Weak": {
        "description": "약한 포지션",
        "criteria": "Behind competitors in most areas, limited advantages"
    },
    "Very Weak": {
        "description": "매우 약한 포지션",
        "criteria": "Significant disadvantages, unclear differentiation"
    }
}


# -----------------------------
# 평가 차원 가중치
# -----------------------------
EVALUATION_DIMENSIONS = {
    "technology_differentiation": {
        "weight": 0.30,
        "description": "Unique technical capabilities, innovation level, technical barriers"
    },
    "market_entry_barriers": {
        "weight": 0.25,
        "description": "Patents/IP, regulatory approvals (FDA, CE, etc.), network effects"
    },
    "funding_and_growth": {
        "weight": 0.20,
        "description": "Total funding raised, growth trajectory, financial stability"
    },
    "partnerships_ecosystem": {
        "weight": 0.15,
        "description": "Strategic partnerships, customer base, market penetration"
    },
    "validation_certification": {
        "weight": 0.05,
        "description": "Clinical validations, regulatory approvals, published research"
    },
    "brand_recognition": {
        "weight": 0.05,
        "description": "Market presence, industry reputation"
    }
}
