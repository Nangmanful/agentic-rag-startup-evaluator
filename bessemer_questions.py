"""
Bessemer Checklist 기반 시장성 평가 질문
Reference: Bessemer Venture Partners 투자 평가 기준
"""

# Bessemer's Checklist 기반 하위 질문 (시장성 관련)
BESSEMER_MARKET_QUESTIONS = [
    {
        "key": "market_size",
        "question": "이 스타트업의 타겟 시장 규모(TAM, Total Addressable Market)는 얼마인가? 구체적인 수치와 시장 성장률을 포함해서 답변해줘.",
        "description": "Bessemer Checklist - 시장 규모 평가"
    },
    {
        "key": "market_problem",
        "question": "이 제품이 해결하려는 시장의 구체적인 문제(Pain Point)는 무엇인가? 고객이 실제로 겪는 어려움을 중심으로 설명해줘.",
        "description": "Bessemer Checklist - 문제 적합성 평가"
    },
    {
        "key": "business_model",
        "question": "이 스타트업의 비즈니스 모델 또는 수익 모델은 무엇인가? 어떻게 돈을 버는지 명확하게 설명해줘.",
        "description": "Bessemer Checklist - 비즈니스 모델 평가"
    }
]

def get_bessemer_questions() -> list:
    """Bessemer 질문 리스트 반환"""
    return BESSEMER_MARKET_QUESTIONS
