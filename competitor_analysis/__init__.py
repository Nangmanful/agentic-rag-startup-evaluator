# ------------------------------------------------------------
# __init__.py
# 경쟁사 비교 에이전트 패키지 초기화
# ------------------------------------------------------------

from .schemas import (
    CompetitorAgentState,
    CompetitorGrade,
    CompetitorAnalysisParsed,
    CompetitorAnalysisOutput,
    MARKET_POSITION_DESCRIPTIONS,
    EVALUATION_DIMENSIONS
)

from .rag_builder import (
    CompetitorRAGBuilder,
    initialize_rag
)

from .competitor_analysis_agent import (
    build_graph,
    run_competitor_analysis
)

__version__ = "1.0.0"

__all__ = [
    # Schemas
    "CompetitorAgentState",
    "CompetitorGrade",
    "CompetitorAnalysisParsed",
    "CompetitorAnalysisOutput",
    "MARKET_POSITION_DESCRIPTIONS",
    "EVALUATION_DIMENSIONS",
    # RAG
    "CompetitorRAGBuilder",
    "initialize_rag",
    # Agent
    "build_graph",
    "run_competitor_analysis",
]
