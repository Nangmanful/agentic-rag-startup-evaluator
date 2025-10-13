# Market Analysis Agent

시장성 평가 에이전트 패키지는 Bessemer/Scorecard 프레임워크를 기반으로 스타트업의 시장 기회와 리스크를 구조화합니다. PDF IR 자료와 산업 뉴스를 RAG로 결합하고 LangGraph로 질문·답변 루프를 제어합니다.

## Directory

```
agents/market/
├── market_analyst.py   # 메인 진입점 및 LangGraph 래퍼
├── agents/             # LangGraph 노드/상태/그래프 정의
├── prompts/            # 질문 재작성·스코어카드 등 프롬프트 템플릿
├── utils/              # PDF RAG 파이프라인 유틸리티
├── outputs/            # 예시 출력(JSON) 보관
└── requirements.txt    # 모듈별 추가 의존성
```

## Workflow Overview
1. **Initialize** – `utils/rag_tools.py`로 PDF(기본: `agents/resources/docs`)를 임베딩하고 FAISS retriever 구성
2. **Question Loop** – Bessemer 질문을 순회하며 문서 검색 → 관련성 평가 → 필요 시 질문 재작성/웹 검색 수행
3. **Scorecard & Insights** – 점수 계산, 산업 뉴스 요약, 최종 보고서(`final_report`) 생성

## Quick Start

```bash
cd agents/market
python -m market_analyst
```

환경 변수: `OPENAI_API_KEY`, `TAVILY_API_KEY`
