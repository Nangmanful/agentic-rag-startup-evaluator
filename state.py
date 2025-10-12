"""
시장성 평가 에이전트 State 정의 (v0.2.1)
"""

from typing import TypedDict, List, Dict, Literal, Any
from typing_extensions import TypedDict as ExtTypedDict

class MarketAnalysisState(TypedDict):
    """시장성 평가 에이전트의 내부 State (v0.2.1)"""

    # ========== 입력 및 초기 설정 ==========
    document_path: str                      # [입력] 분석할 PDF 문서 경로
    startup_name: str                       # [입력] 스타트업 이름
    sub_questions: List[Dict[str, str]]     # [생성] Bessemer 기반 하위 질문 목록

    # ========== RAG 엔진 (1회 구축 후 재사용) ==========
    retriever: Any                          # [생성] FAISS Retriever 객체 (BaseRetriever)

    # ========== 루프 제어 변수 ==========
    current_question_idx: int               # [업데이트] 현재 분석 중인 질문의 인덱스
    current_question: str                   # [업데이트] 현재 분석 중인 질문 텍스트
    retrieved_docs: str                     # [업데이트] 검색된 문서 내용
    is_relevant: Literal["yes", "no"]       # [업데이트] 검색 결과 관련성 ("yes" or "no")
    rewrite_count: int                      # [업데이트] 현재 질문의 재작성 횟수 (무한 루프 방지)
    fallback_attempted: bool                # [업데이트] 웹 검색 시도 여부 (무한 루프 방지)

    # ========== 분석 결과 저장 ==========
    bessemer_answers: Dict[str, Dict[str, Any]]  # [누적] 각 Bessemer 질문에 대한 답변
    # 예시 구조:
    # {
    #     "market_size": {
    #         "question": "시장 규모는?",
    #         "answer": "100억 달러",
    #         "sources": ["page 5", "page 12"],
    #         "rewrite_count": 1,
    #         "status": "success" | "failed"
    #     }
    # }

    scorecard_result: Dict[str, Any]        # [생성] Scorecard Method 점수 및 근거
    # 예시 구조:
    # {
    #     "market_score": 115,
    #     "weight_percentage": 25,
    #     "reasoning": "급성장 시장 + 명확한 PMF",
    #     "evaluation_date": "2025-04-16"
    # }

    final_report: Dict[str, Any]            # [출력] 최종 구조화된 JSON 보고서


# 초기 State 생성 헬퍼 함수
def create_initial_state(document_path: str, startup_name: str) -> MarketAnalysisState:
    """초기 State 생성"""
    return MarketAnalysisState(
        document_path=document_path,
        startup_name=startup_name,
        sub_questions=[],
        retriever=None,
        current_question_idx=0,
        current_question="",
        retrieved_docs="",
        is_relevant="no",
        rewrite_count=0,
        fallback_attempted=False,
        bessemer_answers={},
        scorecard_result={},
        final_report={}
    )
