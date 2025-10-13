# ------------------------------------------------------------
# test_agent.py
# 경쟁사 비교 에이전트 테스트 스크립트
# ------------------------------------------------------------

import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_teddynote.messages import stream_graph, random_uuid
from langchain_teddynote.graphs import visualize_graph

from competitor_analysis_agent import build_graph, run_competitor_analysis

def test_basic_flow():
    """기본 워크플로우 테스트"""
    print("\n" + "="*80)
    print("🧪 테스트 1: 기본 워크플로우 (Qure.ai)")
    print("="*80 + "\n")

    # 예시 데이터
    startup_info = {
        "name": "Qure.ai",
        "category": "Medical AI Imaging",
        "founded": 2016,
        "location": "India"
    }

    tech_summary = """
    Qure.ai is a medical AI startup specializing in deep learning-based diagnostic solutions
    for medical imaging. Core technologies include:

    1. qXR: Chest X-ray interpretation AI (tuberculosis, pneumonia, lung nodules)
    2. qER: Head CT scan analysis for acute neurological conditions
    3. qTrack: Tuberculosis treatment monitoring

    Key Strengths:
    - FDA 510(k) cleared for qXR
    - CE marked for multiple products
    - Deployed in 70+ countries
    - Strong focus on emerging markets
    - Partnerships with major healthcare providers

    Technology Stack:
    - Deep learning (CNN-based architectures)
    - Cloud-based platform
    - DICOM integration
    """

    # 그래프 빌드
    graph = build_graph()

    # 실행 설정
    config = RunnableConfig(recursion_limit=10, configurable={"thread_id": random_uuid()})

    initial_message = HumanMessage(
        content=(
            f"Analyze competitors for {startup_info['name']}, "
            f"a {startup_info['category']} startup. "
            f"Search for main competitors and perform comparative analysis."
        )
    )

    inputs = {
        "messages": [initial_message],
        "company_name": startup_info["name"],
        "tech_summary": tech_summary,
        "core_technologies": ["Deep Learning", "Medical Imaging", "X-Ray Analysis"],
        "startup_info": startup_info,
        "competitor_list": [],
        "competitor_details": [],
        "rag_context": "",
        "competitor_analysis": {},
        "competitive_positioning": "",
        "competitive_advantages": [],
        "competitive_disadvantages": [],
        "market_position": ""
    }

    print("🚀 경쟁사 비교 에이전트 실행 시작...")
    print("-"*80 + "\n")

    # 그래프 실행 (스트리밍)
    stream_graph(
        graph,
        inputs,
        config,
        ["agent", "retrieve_rag_context", "search_more", "analyze", "parse_analysis", "format_output"]
    )
    
    # run_comepetitor_analysis 함수 사용
    # result = run_competitor_analysis(
    #     company_name=startup_info["name"],
    #     tech_summary=tech_summary,
    #     startup_info=startup_info
    # )

    print("\n" + "="*80)
    print("✅ 테스트 1 완료")
    print("="*80 + "\n")

def main():
    """메인 테스트 실행"""

    # Tavily API 키 확인
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key or tavily_key.startswith("tvly-placeholder"):
        print("\n" + "="*80)
        print("⚠️  경고: Tavily API 키가 설정되지 않았습니다!")
        print("실제 웹 검색을 수행하려면 .env 파일에 Tavily API 키를 추가하세요.")
        print("="*80 + "\n")

    print("\n" + "="*80)
    print("🔬 경쟁사 비교 에이전트 통합 테스트")
    print("="*80)
    
    test_basic_flow()

    print("\n" + "="*80)
    print("🎉 테스트 완료!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
