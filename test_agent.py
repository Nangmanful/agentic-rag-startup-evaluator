"""
시장성 평가 에이전트 테스트 스크립트
"""

import json
from dotenv import load_dotenv
from market_analyst import market_analyst_agent

# 환경 변수 로딩
load_dotenv()


def test_market_analyst():
    """시장성 평가 에이전트 테스트"""

    print("\n" + "="*70)
    print("🧪 시장성 평가 에이전트 테스트 시작")
    print("="*70)

    # ========== 테스트 케이스 1: Qure.ai (의료 AI 스타트업) ==========
    print("\n[테스트 케이스 1] Qure.ai")

    # PDF 파일 경로 (실제 파일이 있어야 함)
    # 주의: data/ 폴더에 Qure.ai IR 자료 PDF를 준비해야 합니다.
    document_path = "data/qure.ai.pdf"

    try:
        result = market_analyst_agent(
            startup_name="Qure.ai",
            document_path=document_path
        )

        # 결과 출력
        print("\n" + "="*70)
        print("📊 분석 결과")
        print("="*70)
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # 결과 저장
        output_path = "outputs/qure_ai_market_analysis.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 결과 저장 완료: {output_path}")

    except FileNotFoundError as e:
        print(f"\n❌ [ERROR] PDF 파일을 찾을 수 없습니다: {document_path}")
        print("📝 해결 방법:")
        print("   1. data/ 폴더에 'qure_ai_ir.pdf' 파일 준비")
        print("   2. 또는 GPTs (Consensus, Scholar GPT)로 IR 자료 생성")
        print("   3. 파일 경로를 실제 파일 경로로 수정")

    except Exception as e:
        print(f"\n❌ [ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


def test_with_sample_pdf():
    """샘플 PDF로 빠른 테스트"""

    print("\n" + "="*70)
    print("🧪 샘플 PDF 테스트")
    print("="*70)

    # 샘플 PDF 경로 (독립 실행 시 수정 필요)
    # 옵션 1: market-analysis-agent가 skala-gai 하위에 있을 때
    #sample_pdf = "../16-AgenticRAG/data/SPRi AI Brief_Special_AI Agent_241209_F.pdf"

    # 옵션 2: market-analysis-agent를 독립 실행할 때
    sample_pdf = "data/qure.ai.pdf"  # 샘플 PDF를 data/ 폴더에 복사

    try:
        result = market_analyst_agent(
            startup_name="Sample AI Agent Company",
            document_path=sample_pdf
        )

        print("\n✅ 샘플 테스트 성공!")
        print(f"   시장성 점수: {result['summary']['market_score']}점")
        print(f"   성공 질문: {result['summary']['success_count']}개")
        print(f"   실패 질문: {result['summary']['failed_count']}개")

    except Exception as e:
        print(f"\n❌ [ERROR] 샘플 테스트 실패: {e}")


if __name__ == "__main__":
    print("="*70)
    print("시장성 평가 에이전트 테스트 스위트")
    print("="*70)

    # 테스트 선택
    print("\n테스트 옵션:")
    print("1. Qure.ai 테스트 (data/qure_ai_ir.pdf 필요)")
    print("2. 샘플 PDF 테스트 (16-AgenticRAG 폴더 사용)")

    choice = input("\n선택 (1 or 2): ").strip()

    if choice == "1":
        test_market_analyst()
    elif choice == "2":
        test_with_sample_pdf()
    else:
        print("❌ 잘못된 선택입니다.")
