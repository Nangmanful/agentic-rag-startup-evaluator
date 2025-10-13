"""
Bessemer Checklist 기반 시장성 평가 질문
Reference: Bessemer Venture Partners 투자 평가 기준
"""

# Bessemer's Checklist 기반 하위 질문 (시장성 관련)
BESSEMER_MARKET_QUESTIONS = [
    {
        "key": "market_size",
        "question": "이 시장은 얼마나 큰가? 타겟 시장 규모(TAM)와 성장률을 구체적인 수치로 답변해줘.",
        "description": "Bessemer Checklist - 시장 규모 평가"
    },
    {
        "key": "market_problem",
        "question": "제품이 시장의 실제 문제를 해결하는가? 고객이 겪는 Pain Point와 이 제품의 솔루션을 설명해줘.",
        "description": "Bessemer Checklist - 문제 해결 적합성"
    },
    {
        "key": "customer_willingness_to_pay",
        "question": "고객이 실제로 이 제품에 비용을 지불할 이유가 있는가? 가격 책정과 고객 가치 제안을 분석해줘.",
        "description": "Bessemer Checklist - 지불 의사 평가"
    },
    {
        "key": "differentiation",
        "question": "경쟁사 보다 뚜렷한 차별성이 있는가? 주요 경쟁사와 비교하여 이 스타트업만의 독특한 강점을 설명해줘.",
        "description": "Bessemer Checklist - 경쟁 우위 분석"
    },
    {
        "key": "revenue_model",
        "question": "수익 모델은 명확한가? 어떻게 돈을 벌고, 수익성이 확보될 수 있는지 설명해줘.",
        "description": "Bessemer Checklist - 수익 모델 평가"
    },
    {
        "key": "risks",
        "question": "기술, 운영, 법률적 리스크는 무엇인가? 이 스타트업이 직면할 수 있는 주요 위험 요소를 분석해줘.",
        "description": "Bessemer Checklist - 리스크 분석"
    }
]

def get_bessemer_questions() -> list:
    """Bessemer 질문 리스트 반환"""
    return BESSEMER_MARKET_QUESTIONS
