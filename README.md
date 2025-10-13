# AI Startup Investment Evaluation Agent
본 프로젝트는 인공지능 스타트업에 대한 투자 가능성을 자동으로 평가하는 에이전트를 설계하고 구현한 실습 프로젝트입니다.
#### Class 1, Team 1
##### Member:
김재민, 김창규, 신민석, 이시언, 정광진

## Overview

- Objective : AI 스타트업의 기술력, 시장성, 리스크 등을 기준으로 투자 적합성 분석
- Method : AI Agent + Agentic RAG 
- Tools : 도구A, 도구B, 도구C

## Features
- Tavily 웹 검색 도구를 활용해 최신 경쟁사·시장 정보를 실시간 수집하고 의사결정 LLM에 전달
- 정보 충분성 평가→추가 탐색 분기로 이어지는 LangGraph 기반 조건형 워크플로우
- 6개 핵심 차원(기술·시장장벽·성장성·파트너십·검증·브랜드)별 비교 분석과 포지셔닝 결과 자동 산출

## Tech Stack 

| Category   | Details                      |
|------------|------------------------------|
| Framework  | LangGraph, LangChain, Python |
| LLM        | GPT-4o-mini via OpenAI API   |
| Retrieval  | Tavily Web Search API        |

## Agents
- 기술 요약 에이전트: 
- 시장성 평가 에이전트: 헬스케어/의료 AI Start-Up의 기술자료 PDF를 수집 → RAG 기반 요약/정리 → 구조화 출력까지,
                   LangGraph로 오케스트레이션하며, FAISS retriever와 OpenAI GPT-4o-mini를 결합하여 Agent의 품질을 향상
- 경쟁사 비교 에이전트: 초기 사용자 프롬프트를 받아 경쟁사 검색→정보 보강→LLM 비교 분석→구조화 출력까지 LangGraph로 오케스트레이션하며, Tavily 도구와 OpenAI 모델을 결합해 투자 인사이트를 생성
- 투자 판단 에이전트: 
- 보고서 생성 에이전트: 

## Architecture
(그래프 이미지)

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
