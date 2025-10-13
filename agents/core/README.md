# Core Agents

`agents/core/`는 투자 평가 파이프라인의 핵심 에이전트들을 모아 놓은 패키지입니다. 기술 요약, 투자 판단, 보고서 생성 같은 공통 모듈이 위치하며 `orchestrator.py`가 전체 그래프를 조립합니다.

## Directory

```
agents/core/
├── tech_summary_agent.py      # PDF 기반 기술 요약 LangGraph
├── estimation_agent.py        # 시장/경쟁 스코어를 바탕으로 투자 판단
├── report_generator_agent.py  # ReportLab을 이용한 PDF 리포트 렌더링
├── orchestrator.py            # 전체 파이프라인을 묶는 LangGraph 오케스트레이터
└── __init__.py                # 재사용 가능한 엔트리포인트 노출
```

## Responsibilities
- **Tech Summary Agent**: `agents/resources/docs/`에 있는 IR/PDF 자료를 RAG로 읽고 핵심 기술 서사를 구성합니다.
- **Investment Decider**: 시장성/경쟁 분석 결과를 정규화 점수로 변환 후 YES/MAYBE/NO 판단을 반환합니다.
- **Report Generator**: 투자 판단·시장 분석·경쟁사 분석을 합쳐 PDF 보고서를 생성합니다.
- **Orchestrator**: 기술 요약 → 시장성 평가 → 경쟁사 분석 → 투자 판단 → 보고서 생성 순서를 LangGraph로 묶어 실행합니다.

## Run Orchestrator

```bash
cd agents
python -m agents.core.orchestrator
```

환경 변수
- `OPENAI_API_KEY`, `TAVILY_API_KEY`
- `INV_DECISION_*` (선택) 투자 판단 가중치/임계값
