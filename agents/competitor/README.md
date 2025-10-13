# Competitor Agent Module

경쟁사 비교 에이전트 패키지는 Tavily 웹 검색과 OpenAI LLM을 조합해 스타트업의 경쟁 구도를 평가합니다. LangGraph 워크플로우로 검색 → 분석 → 요약을 자동화하고, 최종 결과를 `CompetitorAnalysisOutput` 스키마로 제공합니다.

## Directory

```
agents/competitor/
├── competitor_analysis_agent.py  # LangGraph 파이프라인과 노드 정의
├── prompts.py                    # 경쟁사 분석/파싱 프롬프트 템플릿
├── schemas.py                    # 상태 및 출력 스키마 (Pydantic)
├── test_agent.py                 # 단일 에이전트 실행 스크립트
└── requirements.txt              # 로컬 개발 시 필요한 추가 패키지 목록
```

## Highlights
- Tavily 기반 경쟁사/시장 정보 검색 (`search_competitors`, `fetch_competitor_details` 도구)
- 정보 충분성 평가 후 추가 검색 여부를 결정하는 LangGraph 조건 분기
- 6개 평가 차원(기술·장벽·성장·파트너십·검증·브랜드)과 요약을 포함한 구조화 출력
- `run_competitor_analysis()` 함수로 외부 워크플로우에서도 쉽게 호출 가능

## Quick Start

```bash
cd agents/competitor
python test_agent.py
```

필수 환경 변수: `OPENAI_API_KEY`, `TAVILY_API_KEY`
