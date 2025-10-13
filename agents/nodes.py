"""
시장성 평가 에이전트 노드 함수들 (v0.2.1)
Reference: 16-AgenticRAG, 21-Agent, 22-LangGraph
"""

import re
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_teddynote.evaluator import GroundednessChecker
from langchain_teddynote.tools.tavily import TavilySearch

from agents.state import MarketAnalysisState
from prompts.bessemer_questions import get_bessemer_questions
from prompts.query_rewrite_prompt import get_query_rewrite_prompt
from prompts.scorecard_prompt import get_scorecard_prompt
from utils.rag_tools import setup_rag_pipeline, retrieve_with_sources


# ========== 노드 1: 초기화 ==========
def initialize_analysis(state: MarketAnalysisState) -> Dict:
    """
    [노드 1: 초기화] RAG 엔진 구축 및 Bessemer 질문 생성

    작업:
    1. PDF 로딩, 텍스트 분할, FAISS 벡터 스토어 구축 (1회만)
    2. Bessemer 질문 리스트 생성
    3. State에 retriever와 질문 저장

    Reference: 16-AgenticRAG/01-NaiveRAG.ipynb
    """

    print("\n" + "="*60)
    print(" [MarketAgent] 초기화: RAG 엔진 구축 시작")
    print("="*60)

    # 1. RAG 파이프라인 구축 (핵심 개선: 1회만 실행)
    try:
        retriever = setup_rag_pipeline(state["document_path"])
    except Exception as e:
        print(f" [ERROR] RAG 파이프라인 구축 실패: {e}")
        # 실패 시 더미 retriever 반환 (에러 처리)
        retriever = None

    # 2. Bessemer 질문 생성
    sub_questions = get_bessemer_questions()

    print(f"\n [초기화] Bessemer 질문 {len(sub_questions)}개 준비 완료:")
    for i, q in enumerate(sub_questions, 1):
        print(f"  {i}. {q['key']}: {q['question'][:50]}...")

    # 3. State 업데이트
    return {
        "retriever": retriever,
        "sub_questions": sub_questions,
        "current_question_idx": 0,
        "rewrite_count": 0,
        "fallback_attempted": False,
        "bessemer_answers": {}
    }


# ========== 노드 1.5: 산업 뉴스 검색 (v0.3.0) ==========
def search_industry_news(state: MarketAnalysisState) -> Dict:
    """
    [노드 1.5: 산업 뉴스 검색] 스타트업 산업의 최근 뉴스 수집

    작업:
    1. PDF에서 산업 카테고리 자동 추출 (예: "Healthcare AI", "Fintech")
    2. 3가지 뉴스 쿼리 실행:
       - 시장 동향: "{industry} market trends 2025"
       - 경쟁사: "{industry} startup funding news"
       - 규제: "{industry} regulation policy changes"
    3. 최근 3일 뉴스만 수집 (days=3)
    4. 결과를 industry_news에 저장

    Reference: 16-AgenticRAG/03-WebSearch.ipynb
    """

    print("\n" + "="*60)
    print(" [MarketAgent] 산업 뉴스 검색 시작")
    print("="*60)

    # 1. 산업 카테고리 추출 (간단한 LLM 호출)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    retriever = state["retriever"]

    if retriever is None:
        print(" [WARNING] Retriever가 없어 산업 분류를 건너뜁니다.")
        return {
            "industry_category": "General",
            "industry_news": {
                "industry": "General",
                "search_date": "2025-10-13",
                "news_categories": {}
            }
        }

    # Retriever로 첫 페이지 검색
    try:
        first_docs = retriever.invoke(
            "What industry does this company belong to? medical, fintech, e-commerce, AI, etc."
        )
        from utils.rag_tools import format_docs
        context = format_docs(first_docs)

        prompt = f"""Based on this document, identify the industry category in 2-3 words:

{context[:1000]}

Return ONLY the industry name (e.g., "Healthcare AI", "Fintech", "E-commerce SaaS")"""

        industry = llm.invoke(prompt).content.strip()
        print(f"\n [산업 분류] {industry}")

    except Exception as e:
        print(f" [WARNING] 산업 분류 실패: {e}, 기본값 사용")
        industry = "Technology"

    # 2. Tavily 검색 도구 초기화
    tavily_tool = TavilySearch(max_results=5)

    # 3. 3가지 뉴스 쿼리 실행
    news_queries = {
        "market_trends": f"{industry} market trends growth 2025",
        "competitor_moves": f"{industry} startup funding investment news",
        "regulatory_changes": f"{industry} regulation policy changes"
    }

    industry_news = {
        "industry": industry,
        "search_date": "2025-10-13",
        "news_categories": {}
    }

    for category, query in news_queries.items():
        print(f"\n [뉴스 검색] {category}: {query}")

        try:
            search_results = tavily_tool.search(
                query=query,
                topic="news",           # 뉴스 주제로 한정
                days=3,                 # 최근 3일
                max_results=5,          # 각 카테고리당 5개
                format_output=True      # 포맷팅된 출력
            )

            industry_news["news_categories"][category] = search_results
            print(f" ✅ {len(search_results)}개 뉴스 수집 완료")

        except Exception as e:
            print(f" ⚠️ {category} 검색 실패: {e}")
            industry_news["news_categories"][category] = []

    # 4. 요약 통계
    total_news = sum(len(v) for v in industry_news["news_categories"].values())
    print(f"\n [검색 완료] 총 {total_news}개 산업 뉴스 수집")

    return {
        "industry_category": industry,
        "industry_news": industry_news
    }


# ========== 노드 2: 다음 질문 선택 ==========
def select_next_question(state: MarketAnalysisState) -> Dict:
    """
    [노드 2: 질문 선택] 다음 분석할 Bessemer 질문 선택

    Reference: 21-Agent/21-Multi-ReportAgent.ipynb (current_section 패턴)
    """

    current_idx = state["current_question_idx"]
    sub_questions = state["sub_questions"]

    if current_idx >= len(sub_questions):
        # 모든 질문 완료
        print("\n✅ [질문 선택] 모든 Bessemer 질문 분석 완료!")
        return {}

    # 다음 질문 선택
    current_q = sub_questions[current_idx]

    print("\n" + "-"*60)
    print(f"📝 [질문 선택] ({current_idx + 1}/{len(sub_questions)}) {current_q['key']}")
    print(f"   질문: {current_q['question']}")
    print("-"*60)

    # State 업데이트
    return {
        "current_question": current_q["question"],
        "rewrite_count": 0,  # 질문이 바뀌면 재작성 카운터 리셋
        "fallback_attempted": False  # 웹 검색 플래그도 리셋
    }


# ========== 노드 3: 문서 검색 ==========
def retrieve_documents(state: MarketAnalysisState) -> Dict:
    """
    [노드 3: 검색] State에 저장된 Retriever로 문서 검색

    개선점: retriever를 매번 생성하지 않고 State에서 재사용

    Reference: 16-AgenticRAG/01-NaiveRAG.ipynb
    """

    print(f"\n [문서 검색] 질문: {state['current_question'][:50]}...")

    retriever = state["retriever"]

    if retriever is None:
        print(" [ERROR] Retriever가 초기화되지 않았습니다.")
        return {"retrieved_docs": "", "is_relevant": "no"}

    # 문서 검색 (출처 포함)
    try:
        formatted_docs, sources = retrieve_with_sources(
            retriever,
            state["current_question"]
        )

        print(f" [문서 검색] {len(sources)}개 출처에서 관련 문서 검색 완료")
        print(f"   출처: {sources[:3]}")  # 최대 3개만 출력

        return {"retrieved_docs": formatted_docs}

    except Exception as e:
        print(f" [ERROR] 문서 검색 실패: {e}")
        return {"retrieved_docs": "", "is_relevant": "no"}


# ========== 노드 4: 관련성 평가 ==========
def grade_relevance(state: MarketAnalysisState) -> Dict:
    """
    [노드 4: 관련성 평가] 검색 결과가 질문과 관련 있는지 평가

    Reference: 16-AgenticRAG/02-RelevanceCheck.ipynb
    """

    print(f"\n⚖️ [관련성 평가] 검색 결과 평가 중...")

    # GroundednessChecker 생성 (02-RelevanceCheck.ipynb 패턴)
    checker = GroundednessChecker(
        # LLM을 함수 내에서 초기화
        llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
        target="question-retrieval"
    ).create()

    try:
        # 관련성 체크
        response = checker.invoke({
            "question": state["current_question"],
            "context": state["retrieved_docs"]
        })

        relevance = response.score  # "yes" or "no"

        print(f" [관련성 평가] 결과: {relevance}")

        return {"is_relevant": relevance}

    except Exception as e:
        print(f" [ERROR] 관련성 평가 실패: {e}")
        return {"is_relevant": "no"}


# ========== 노드 5: 질문 재작성 ==========
def rewrite_question(state: MarketAnalysisState) -> Dict:
    """
    [노드 5: 질문 재작성] 관련성 낮을 때 질문 개선

    Reference: 16-AgenticRAG/04-QueryRewrite.ipynb
    """

    print(f"\n [질문 재작성] 재작성 시도 중... (횟수: {state['rewrite_count'] + 1})")

    # Query Rewrite 프롬프트
    rewrite_prompt = get_query_rewrite_prompt()
    question_rewriter = (
        rewrite_prompt |
        ChatOpenAI(model="gpt-4o-mini", temperature=0) | # LLM을 함수 내에서 초기화
        StrOutputParser()
    )

    try:
        # 질문 재작성
        rewritten_question = question_rewriter.invoke({
            "question": state["current_question"]
        })

        print(f"✅ [질문 재작성] 완료")
        print(f"   원본: {state['current_question'][:50]}...")
        print(f"   재작성: {rewritten_question[:50]}...")

        return {
            "current_question": rewritten_question,
            "rewrite_count": state["rewrite_count"] + 1
        }

    except Exception as e:
        print(f" [ERROR] 질문 재작성 실패: {e}")
        return {"rewrite_count": state["rewrite_count"] + 1}


# ========== 노드 6: 웹 검색 Fallback ==========
def web_search_fallback(state: MarketAnalysisState) -> Dict:
    """
    [노드 6: 웹 검색] PDF 검색 실패 시 웹 검색으로 대안 계획 실행

    Reference: 16-AgenticRAG/03-WebSearch.ipynb
    """

    print(f"\n🌐 [웹 검색] PDF에서 정보 부족, Tavily 웹 검색 시도 중...")

    tavily_tool = TavilySearch(max_results=3)

    try:
        # 웹 검색 실행
        search_results = tavily_tool.search(
            query=state["current_question"],
            topic="general",
            max_results=3,
            format_output=True
        )

        # 검색 결과를 문서 형식으로 변환
        web_docs = "\n\n".join(search_results)

        print(f" [웹 검색] 완료 (검색 결과 {len(search_results)}개)")

        return {
            "retrieved_docs": web_docs,
            "fallback_attempted": True
        }

    except Exception as e:
        print(f" [ERROR] 웹 검색 실패: {e}")
        return {
            "retrieved_docs": "",
            "fallback_attempted": True
        }


# ========== 노드 7: 답변 생성 ==========
def generate_answer(state: MarketAnalysisState) -> Dict:
    """
    [노드 7: 답변 생성] 검색된 문서를 바탕으로 답변 생성 (출처 포함)

    Reference: 16-AgenticRAG/01-NaiveRAG.ipynb
    """

    print(f"\n💬 [답변 생성] LLM 답변 생성 중...")

    # 답변 생성 프롬프트 (시장성 평가 특화 v0.3.0)
    answer_prompt = f"""너는 벤처캐피탈 투자심사역(Investment Analyst)이야. 스타트업의 시장성을 평가하기 위해 정확하고 구체적인 데이터를 추출해야 해.

## 평가 원칙
1. **정량적 데이터 우선**: 숫자, 퍼센트, 금액 등 구체적인 수치 필수
2. **비교 기준 제시**: 경쟁사, 업계 평균, 성장률 등 상대적 위치 명시
3. **시간 프레임 명확화**: 언제의 데이터인지, 미래 전망은 몇 년 후인지 명시
4. **출처 신뢰성**: 페이지 번호, 섹션명 반드시 포함

## 질문
{state['current_question']}

## 문서
{state['retrieved_docs']}

## 답변 형식 (반드시 준수)
- **핵심 답변**: [1-2줄 요약, 구체적 수치 포함]
- **상세 분석**:
  - 정량 데이터: [구체적 숫자, 단위, 시점]
  - 비교 분석: [경쟁사/업계 대비 위치]
  - 성장 전망: [향후 예상, 근거]
- **출처**: [페이지 번호, 섹션명]

[주의] 문서에 정보가 없으면 "문서에서 해당 정보를 찾을 수 없음"이라고 명시하고 추측하지 마.
"""

    try:
        response = ChatOpenAI(model="gpt-4o-mini", temperature=0).invoke(answer_prompt)
        answer = response.content

        print(f" [답변 생성] 완료")
        print(f"   답변 미리보기: {answer[:100]}...")

        # 현재 질문의 키 추출
        current_idx = state["current_question_idx"]
        question_key = state["sub_questions"][current_idx]["key"]

        # bessemer_answers에 저장
        bessemer_answers = state["bessemer_answers"]
        bessemer_answers[question_key] = {
            "question": state["current_question"],
            "answer": answer,
            "rewrite_count": state["rewrite_count"],
            "fallback_used": state["fallback_attempted"],
            "status": "success"
        }

        return {
            "bessemer_answers": bessemer_answers,
            "current_question_idx": state["current_question_idx"] + 1  # 다음 질문으로
        }

    except Exception as e:
        print(f" [ERROR] 답변 생성 실패: {e}")
        return {}


# ========== 노드 8: 질문 스킵 (실패 케이스 처리) ==========
def skip_question(state: MarketAnalysisState) -> Dict:
    """
    [노드 8: 질문 스킵] 웹 검색도 실패한 경우 답변 불가 처리

    개선점: v0.2.1에서 추가된 안전장치
    """

    print(f"\n [질문 스킵] 데이터 부족으로 답변 불가 처리")

    # 현재 질문의 키 추출
    current_idx = state["current_question_idx"]
    question_key = state["sub_questions"][current_idx]["key"]

    # bessemer_answers에 실패 기록
    bessemer_answers = state["bessemer_answers"]
    bessemer_answers[question_key] = {
        "question": state["current_question"],
        "answer": "데이터 부족으로 답변 불가",
        "rewrite_count": state["rewrite_count"],
        "fallback_used": state["fallback_attempted"],
        "status": "failed"
    }

    return {
        "bessemer_answers": bessemer_answers,
        "current_question_idx": state["current_question_idx"] + 1  # 다음 질문으로
    }


# ========== 노드 9: Scorecard 점수 계산 ==========
def calculate_scorecard(state: MarketAnalysisState) -> Dict:
    """
    [노드 9: 점수 계산] Scorecard Method로 시장성 점수 산출

    Reference: 프로젝트 가이드 PDF - Scorecard Method
    """

    print("\n" + "="*60)
    print("📊 [Scorecard] 시장성 점수 계산 중...")
    print("="*60)

    # Bessemer 답변 종합
    bessemer_answers = state["bessemer_answers"]

    market_data = f"""
[시장 규모 (TAM)]
{bessemer_answers.get('market_size', {}).get('answer', 'N/A')}

[해결하는 문제]
{bessemer_answers.get('market_problem', {}).get('answer', 'N/A')}

[비즈니스 모델]
{bessemer_answers.get('business_model', {}).get('answer', 'N/A')}
"""

    # Scorecard 평가 프롬프트
    scorecard_prompt = get_scorecard_prompt()
    evaluation_prompt = scorecard_prompt.format(market_data=market_data)

    try:
        response = ChatOpenAI(model="gpt-4o-mini", temperature=0).invoke(evaluation_prompt)
        evaluation_text = response.content

        # 점수 파싱 (정규표현식)
        score_match = re.search(r"점수:\s*(\d+)점", evaluation_text)
        market_score = int(score_match.group(1)) if score_match else 100

        # 근거 추출
        reasoning_match = re.search(r"근거:(.*)", evaluation_text, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else evaluation_text

        print(f"\n✅ [Scorecard] 계산 완료")
        print(f"   시장성 점수: {market_score}점 (비중 25%)")
        print(f"   근거: {reasoning[:100]}...")

        scorecard_result = {
            "market_score": market_score,
            "weight_percentage": 25,
            "weighted_contribution": market_score * 0.25,
            "reasoning": reasoning,
            "evaluation_method": "Scorecard Valuation Method",
            "evaluation_date": "2025-04-16"
        }

        return {"scorecard_result": scorecard_result}

    except Exception as e:
        print(f" [ERROR] Scorecard 계산 실패: {e}")
        return {
            "scorecard_result": {
                "market_score": 100,
                "error": str(e)
            }
        }


# ========== 노드 9.5: 산업 인사이트 분석 (v0.3.0) ==========
def analyze_industry_insights(state: MarketAnalysisState) -> Dict:
    """
    [노드 9.5: 산업 인사이트 분석] 수집된 뉴스를 LLM으로 요약 분석

    위치: calculate_scorecard 직후, finalize_report 직전

    작업:
    1. 수집된 뉴스를 LLM에게 제공
    2. 투자 관점에서 핵심 인사이트 3가지 추출
    3. Bessemer 답변과 연결하여 시장 타이밍 평가
    """

    print("\n" + "="*60)
    print(" [MarketAgent] 산업 인사이트 분석 시작")
    print("="*60)

    industry_news = state.get("industry_news", {})
    industry_category = state.get("industry_category", "Unknown")
    bessemer_answers = state["bessemer_answers"]

    # 뉴스가 없으면 스킵
    if not industry_news or not industry_news.get("news_categories"):
        print(" [WARNING] 수집된 뉴스가 없어 인사이트 분석을 건너뜁니다.")
        return {
            "industry_insights": {
                "summary": "산업 뉴스 데이터 부족으로 인사이트 분석 불가",
                "news_count": 0,
                "analysis_date": industry_news.get("search_date", "N/A")
            }
        }

    # 뉴스 텍스트 통합
    all_news_text = []
    for category, news_list in industry_news["news_categories"].items():
        if news_list:
            all_news_text.append(f"### {category.replace('_', ' ').title()}")
            all_news_text.extend(news_list[:3])  # 각 카테고리에서 최대 3개만

    news_context = "\n\n".join(all_news_text)

    # Bessemer 답변 요약
    market_size_answer = bessemer_answers.get('market_size', {}).get('answer', 'N/A')[:200]
    differentiation_answer = bessemer_answers.get('differentiation', {}).get('answer', 'N/A')[:200]

    # LLM 프롬프트
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""너는 벤처 투자 전문가야. 아래 산업 뉴스를 분석하고, 투자 관점에서 핵심 인사이트 3가지를 추출해줘.

## 분석 대상 스타트업 정보
- 산업: {industry_category}
- 시장 규모: {market_size_answer}
- 경쟁 우위: {differentiation_answer}

## 최근 3일 산업 뉴스
{news_context[:4000]}

## 출력 형식 (반드시 준수)
**핵심 인사이트 1**: [1-2줄로 요약]
**핵심 인사이트 2**: [1-2줄로 요약]
**핵심 인사이트 3**: [1-2줄로 요약]

**투자 타이밍 평가**: [현재 시장 상황이 이 스타트업 투자에 유리한지 2줄로 평가]
"""

    try:
        insights = llm.invoke(prompt).content

        print(f"\n✅ [인사이트 분석 완료]")
        print(f"   {insights[:150]}...")

        return {
            "industry_insights": {
                "summary": insights,
                "news_count": sum(len(v) for v in industry_news["news_categories"].values()),
                "analysis_date": industry_news["search_date"]
            }
        }

    except Exception as e:
        print(f" [ERROR] 인사이트 분석 실패: {e}")
        return {
            "industry_insights": {
                "summary": f"인사이트 분석 중 오류 발생: {str(e)}",
                "news_count": 0,
                "analysis_date": industry_news.get("search_date", "N/A")
            }
        }


# ========== 노드 10: 최종 보고서 생성 ==========
def finalize_report(state: MarketAnalysisState) -> Dict:
    """
    [노드 10: 최종 보고] 모든 분석 결과를 JSON 보고서로 구조화

    Reference: 21-Agent/21-Multi-ReportAgent.ipynb
    """

    print("\n" + "="*60)
    print("📄 [최종 보고서] JSON 보고서 생성 중...")
    print("="*60)

    # 기본 보고서 구조
    final_report = {
        "startup_name": state["startup_name"],
        "analysis_type": "Market Analysis (시장성 평가)",
        "analysis_date": "2025-04-16",
        "bessemer_checklist": state["bessemer_answers"],
        "scorecard_method": state["scorecard_result"],
        "summary": {
            "market_score": state["scorecard_result"].get("market_score", 0),
            "weight_percentage": 25,
            "success_count": sum(
                1 for ans in state["bessemer_answers"].values()
                if ans.get("status") == "success"
            ),
            "failed_count": sum(
                1 for ans in state["bessemer_answers"].values()
                if ans.get("status") == "failed"
            )
        }
    }

    # 🆕 v0.3.0: 산업 뉴스 인텔리전스 섹션 추가
    industry_news = state.get("industry_news", {})
    industry_insights = state.get("industry_insights", {})

    if industry_news and industry_news.get("news_categories"):
        # 각 카테고리에서 상위 3개 뉴스만 포함
        key_trends = industry_news["news_categories"].get("market_trends", [])[:3]
        competitor_activity = industry_news["news_categories"].get("competitor_moves", [])[:3]
        regulatory_updates = industry_news["news_categories"].get("regulatory_changes", [])[:2]

        final_report["industry_intelligence"] = {
            "industry_category": state.get("industry_category", "Unknown"),
            "news_summary": industry_insights.get("summary", "인사이트 분석 없음"),
            "total_news_analyzed": industry_insights.get("news_count", 0),
            "key_trends": key_trends,
            "competitor_activity": competitor_activity,
            "regulatory_updates": regulatory_updates,
            "search_date": industry_news.get("search_date", "N/A")
        }
    else:
        # 뉴스 데이터가 없는 경우
        final_report["industry_intelligence"] = {
            "industry_category": state.get("industry_category", "Unknown"),
            "news_summary": "산업 뉴스 데이터 없음",
            "total_news_analyzed": 0,
            "key_trends": [],
            "competitor_activity": [],
            "regulatory_updates": [],
            "search_date": "N/A"
        }

    print(f"\n✅ [최종 보고서] 생성 완료")
    print(f"   성공: {final_report['summary']['success_count']}개 질문")
    print(f"   실패: {final_report['summary']['failed_count']}개 질문")
    print(f"   시장성 점수: {final_report['summary']['market_score']}점")
    print(f"   산업 뉴스: {final_report['industry_intelligence']['total_news_analyzed']}개 분석")

    return {"final_report": final_report}
