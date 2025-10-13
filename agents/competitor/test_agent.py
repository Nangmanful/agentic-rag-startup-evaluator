# ------------------------------------------------------------
# test_agent.py
# 경쟁사 비교 에이전트 테스트 스크립트
# ------------------------------------------------------------

import os
import json
from dotenv import load_dotenv
load_dotenv()

from langchain_core.runnables import RunnableConfig
from langchain_teddynote.messages import random_uuid

from competitor_analysis_agent import run_competitor_analysis

def test_basic_flow():
    """기본 워크플로우 테스트"""
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

    # 실행 설정
    config = RunnableConfig(recursion_limit=10, configurable={"thread_id": random_uuid()})

    print("🚀 경쟁사 비교 에이전트 실행 시작...\n")
    
    result = run_competitor_analysis(
        company_name=startup_info["name"],
        tech_summary=tech_summary,
        startup_info=startup_info,
        config=config,
    )
    
    final_output = result.get("final_output")
    
    print("\n" + "="*80)
    if final_output:
          print("🧩 CompetitorAnalysisOutput:")
          print(json.dumps(final_output, ensure_ascii=False, indent=2))
    else:
        print("⚠️ final_output이 생성되지 않았습니다.")
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
    print("🔬 경쟁사 비교 에이전트 통합 테스트 (Qure.ai)")
    print("="*80)
    
    test_basic_flow()

    print("\n" + "="*80)
    print("🎉 테스트 완료!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
