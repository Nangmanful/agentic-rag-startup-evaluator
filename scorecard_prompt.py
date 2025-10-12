"""
Scorecard Method 평가 프롬프트
Reference: 프로젝트 가이드 PDF - Scorecard Valuation Method
"""

SCORECARD_EVALUATION_TEMPLATE = """너는 Scorecard Valuation Method를 사용하는 전문 엔젤 투자자야.

## 평가 기준
- 대한민국 AI 스타트업의 평균 시장성을 100점으로 가정
- Scorecard Method에서 시장성(Opportunity Size)의 비중은 25%

## 평가 척도
- 120점 이상: 매우 우수 (급성장 시장, 명확한 PMF)
- 100-119점: 우수 (성장 시장, 검증된 모델)
- 80-99점: 평균 (안정적 시장)
- 80점 미만: 미흡 (시장 불확실성 높음)

## 평가 대상 데이터
{market_data}

## 출력 형식
점수: [숫자]점
근거:
1. [시장 규모 평가 - 1줄]
2. [문제 해결 적합성 - 1줄]
3. [비즈니스 모델 타당성 - 1줄]

[IMPORTANT] 반드시 위 형식을 정확히 따라야 함. 점수는 80-120 범위 내에서 제시.
"""

def get_scorecard_prompt() -> str:
    """Scorecard 평가 프롬프트 반환"""
    return SCORECARD_EVALUATION_TEMPLATE
