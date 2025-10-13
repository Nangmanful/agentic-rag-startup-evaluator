🧠 Investment Decision Sub-Agent
📌 개요

이 에이전트는 시장성 평가 결과와 경쟁사 비교 점수를 바탕으로 최종 투자 판단(YES or NO)을 자동으로 내리는 LangGraph 서브 노드입니다.
기술 요약 → 시장성 평가 → 경쟁사 비교 → 투자 판단으로 이어지는 전체 파이프라인의 마지막 단계에서 동작합니다.

🧭 동작 방식

시장성 점수와 경쟁사 점수(1~5) 를 정규화하여 최종 점수를 산출합니다.

환경 변수에 설정된 가중치와 임계값을 기준으로 YES 또는 NO를 결정합니다.

결정에 대한 신뢰도(confidence)와 근거(rationale), 리스크 요소, 다음 액션까지 함께 반환합니다.

근거 소스(evidence_sources)가 부족할 경우 보수적으로 NO를 반환합니다.

🧾 입력 형식 (State)

market_eval : 시장성 평가 결과

Bessemer 또는 Scorecard 평가 기준

정규화 점수 또는 원본 점수 포함 가능

긍정 요소 / 리스크 / 근거 출처 포함

competitor_eval : 경쟁사 비교 결과

주요 경쟁사명 및 점수(1~5)

근거 출처 포함

🧮 출력 형식 (State)

investment_decision : 최종 투자 판단 결과

decision: YES or NO

confidence: 0~1

score_breakdown: 시장성/경쟁사 점수 및 최종 점수

rationale: 판단 근거 요약

risks: 리스크 요인

next_actions: 후속 액션 제안

used_sources: 근거 소스

⚙️ 환경 변수
이름	설명	기본값
INV_DECISION_W_MARKET	시장성 평가 가중치	0.6
INV_DECISION_W_COMP	경쟁사 점수 가중치	0.4
INV_DECISION_THRESH_YES	YES 판단 기준 점수	0.62
INV_DECISION_THRESH_MAYBE	모호 구간 기준 점수	0.52
INV_DECISION_MIN_SOURCES	최소 근거 소스 개수	1
🧪 판단 로직 기준
케이스	설명	결과
최종 점수 ≥ YES 기준	투자 적합	YES
최종 점수 < 모호 기준	투자 부적합	NO
모호 구간 (기준 사이)	정책상 보수적 판단	NO
근거 소스 부족	증거 불충분	NO
📚 참고

Bessemer’s Checklist — 시장성, 문제 해결력, 고객 지불 의사, 경쟁우위 등

Scorecard Method — 창업자 역량, 시장 크기, 제품/기술력, 경쟁력, 실적 등

Bessemer Venture Partners Investment Criteria

Scorecard Valuation Method

Bill Payne Scorecard Methodology

🧑‍💻 Maintainer

Author: 김창규

Role: 투자 판단 서브 에이전트 개발

Pipeline: 기술 요약 → 시장성 평가 → 경쟁사 비교 → 투자 판단 ✅
