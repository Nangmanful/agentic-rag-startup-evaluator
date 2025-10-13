# 🧠 Investment Decision Sub-Agent

## 📌 개요
이 에이전트는 **시장성 평가 결과**와 **경쟁사 비교 점수**를 바탕으로 최종 투자 판단(`YES` 또는 `NO`)을 자동으로 내리는 **LangGraph 서브 노드**입니다.  
기술 요약 → 시장성 평가 → 경쟁사 비교 → 투자 판단으로 이어지는 전체 파이프라인의 마지막 단계에서 동작합니다.

---

## 🧭 동작 방식
- 시장성 평가 점수와 경쟁사 비교 점수를 정규화하여 최종 점수를 계산합니다.  
- 환경 변수에 정의된 가중치와 임계값을 기준으로 투자 판단 결과(`YES` 또는 `NO`)를 반환합니다.  
- Confidence(신뢰도)는 점수 간 정렬도, 최종 점수와 임계값 거리, 근거 소스 개수를 기준으로 계산합니다.  
- 근거 소스가 최소 기준에 미달하면 자동으로 NO로 처리합니다.  
- 최종 결과에는 판단 근거, 리스크, 다음 액션, 근거 소스가 함께 포함됩니다.

---

## 🧾 입력 형식 (State)

| 키 | 설명 |
|----|------|
| `market_eval` | 시장성 평가 결과 (`Bessemer` 또는 `Scorecard` 방식)<br> 정규화 점수, 긍정 요소, 리스크, 근거 출처 포함 |
| `competitor_eval` | 경쟁사 비교 결과<br> 각 경쟁사의 점수(1~5) 및 근거 출처 포함 |

---

## 🧮 출력 형식 (State)

| 키 | 설명 |
|----|------|
| `investment_decision.decision` | 최종 판단 결과 (`YES` or `NO`) |
| `investment_decision.confidence` | 0~1 범위의 신뢰도 |
| `investment_decision.score_breakdown` | 시장성, 경쟁사 점수 및 최종 점수 |
| `investment_decision.rationale` | 판단 근거 요약 |
| `investment_decision.risks` | 리스크 요인 |
| `investment_decision.next_actions` | 후속 액션 제안 |
| `investment_decision.used_sources` | 근거 소스 리스트 |

---

## ⚙️ 환경 변수

| 이름 | 설명 | 기본값 |
|------|------|--------|
| `INV_DECISION_W_MARKET` | 시장성 평가 가중치 | `0.6` |
| `INV_DECISION_W_COMP` | 경쟁사 점수 가중치 | `0.4` |
| `INV_DECISION_THRESH_YES` | YES 판단 기준 점수 | `0.62` |
| `INV_DECISION_THRESH_MAYBE` | 모호 구간 기준 점수 | `0.52` |
| `INV_DECISION_MIN_SOURCES` | 최소 근거 소스 개수 | `1` |

---

## 🧪 판단 로직 기준

| 케이스 | 설명 | 결과 |
|--------|------|------|
| 최종 점수 ≥ YES 기준 | 투자 적합 | YES |
| 최종 점수 < 모호 기준 | 투자 부적합 | NO |
| 모호 구간 (기준 사이) | 정책상 보수적 판단 | NO |
| 근거 소스 부족 | 증거 불충분 | NO |

---

## 📚 참고

- **Bessemer’s Checklist** — 시장성, 문제 해결력, 고객 지불 의사, 경쟁우위 등  
- **Scorecard Method** — 창업자 역량, 시장 크기, 제품/기술력, 경쟁력, 실적 등  
- [Bessemer Venture Partners Investment Criteria](https://www.joinleland.com/library/a/the-key-factors-bessemer-venture-partners-considers-for-technology-startups)  
- [Scorecard Valuation Method](https://eqvista.com/scorecard-valuation-method-explained/)  
- [Bill Payne Scorecard Methodology](https://angelcapitalassociation.org/blog/blog-scorecard-valuation-methodology-rev-2019-establishing-the-valuation-of-pre-revenue-start-up-companies/)

---

## 🧑‍💻 Maintainer

- **Author:** 김창규  
- **Role:** 투자 판단 서브 에이전트 개발  
- **Pipeline:** 기술 요약 → 시장성 평가 → 경쟁사 비교 → 투자 판단 ✅
