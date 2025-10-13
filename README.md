# AI 스타트업 투자 평가 에이전트 (AI Startup Investment Evaluation Agent)

본 프로젝트는 전문 투자 심사역처럼 협업하는 AI 에이전트 팀을 구축하여, AI 스타트업의 투자 가치를 자동으로 분석하고 평가 보고서를 생성하는 실습 프로젝트입니다.

## 🚀 Overview

-   **Objective**: AI 스타트업의 기술력, 시장성, 경쟁 구도 등을 종합적으로 분석하여 투자 적합성을 판단하고, 근거 기반의 상세 보고서를 생성합니다.
-   **Method**: **Agentic RAG**와 **Multi-Agent Collaboration** 시스템을 **LangGraph** 프레임워크를 기반으로 설계했습니다.
-   **Core Engine**: 각 분석 에이전트는 **"자기 수정(Self-Correction)"** 능력을 갖춘 RAG 엔진을 탑재하여, 분석의 정확성과 신뢰도를 극대화합니다.

## ✨ Features

-   **다중 에이전트 협업 워크플로우**: `기술 분석`, `시장성 평가` 등 각 분야 전문가 에이전트들이 유기적으로 협업하여 복잡한 투자 평가 업무를 자동화합니다.
-   **근거 기반의 심층 분석 (Advanced RAG)**:
    -   PDF 문서(IR 자료, 시장 보고서 등)의 내용을 분석하여 모든 평가 결과에 **출처(Citation)를 명시**합니다.
    -   **Query Rewrite**: 검색 품질이 낮을 경우, 에이전트가 스스로 질문을 개선하여 재검색을 시도합니다.
    -   **Web Search Fallback**: 문서에 정보가 없을 경우, 웹 검색을 통해 데이터를 보충하여 정보 누락을 최소화합니다.
-   **자동화된 투자 판단 및 보고**: `Bessemer Checklist`와 `Scorecard Method`를 기반으로 정량적 평가를 수행하고, 그 결과에 따라 후속 작업을 스스로 결정하여 최종 보고서를 생성합니다.

## 🛠️ Tech Stack

| Category | Details | Purpose |
| :--- | :--- | :--- |
| **Framework** | LangGraph, LangChain | 상태 기반의 자율 에이전트 워크플로우 설계 및 실행 |
| **LLM** | OpenAI GPT-4o-mini | 답변 생성, 관련성 평가, 질문 재작성, 인사이트 분석 |
| **Embedding** | OpenAI text-embedding-3-small | 문서 벡터화를 통한 의미 기반 검색 |
| **Vector Store** | FAISS (Facebook AI Similarity Search) | 로컬 환경에서의 빠르고 효율적인 벡터 검색 |
| **Web Search** | Tavily Search | PDF에 정보가 없을 때 실시간 웹 정보 검색 |
| **Evaluation**| GroundednessChecker | 검색된 정보와 질문 간의 관련성 자동 평가 |

## 🤖 Agents

본 시스템은 다음과 같은 전문가 에이전트들로 구성된 팀으로 작동합니다.

-   **`기술 요약 에이전트`**: 스타트업의 핵심 기술, 적용 가능성, 리스크를 RAG 기반으로 분석하고 요약합니다.
-   **`시장성 평가 에이전트`**: `Bessemer Checklist`와 `Scorecard Method`를 기준으로 시장의 잠재력을 정성적/정량적으로 평가합니다.
-   **`경쟁사 비교 에이전트`**: 웹 검색과 RAG를 결합하여 경쟁 구도와 시장 내 포지셔닝을 분석합니다.
-   **`투자 판단 에이전트`**: 각 전문가 에이전트의 분석 결과를 종합하여 최종 투자 추천 여부(`Invest` / `Hold`)를 결정합니다.
-   **기타**: `스타트업 탐색 에이전트`, `보고서 생성 에이전트`가 전체 워크플로우를 지원합니다.

## 🏛️ Architecture

본 에이전트 시스템은 **LangGraph**를 사용하여 아래와 같은 상태 기반의 워크플로우로 설계되었습니다. `투자 판단` 에이전트의 결과에 따라 흐름이 동적으로 분기되는 **조건부 엣지(Conditional Edge)**가 핵심입니다.

```mermaid
graph TD
    A[START] --> B[스타트업 탐색]
    B --> C[기술 요약]
    C --> D[시장성 평가]
    D --> E[경쟁사 비교]
    E --> F[투자 판단]
    F -->|Invest| G[보고서 생성]
    F -->|Hold| B
    G --> H[END]


## Directory Structure
├── data/                  # 스타트업 PDF 문서
├── agents/                # 평가 기준별 Agent 모듈
├── prompts/               # 프롬프트 템플릿
├── outputs/               # 평가 결과 저장
├── app.py                 # 실행 스크립트
├── test.py                # Agent 테스트 스크립트
└── README.md

## Contributors 
- 김재민: 시장성 평가 에이전트 구현
- 김창규: 투자 판단 에이전트 & 보고서 생성 에이전트 구현
- 신민석: 기술 요약 에이전트 구현
- 이시언: 스타트업 정보 수집
- 정광진: 경쟁사 비교 에이전트 구현
