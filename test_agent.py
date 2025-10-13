"""
시장성 평가 에이전트 테스트 스크립트
"""

import json
import os
from dotenv import load_dotenv
from market_analyst import market_analyst_agent

# 환경 변수 로딩
load_dotenv()


def main():
    """시장성 평가 에이전트 실행"""

    print("\n" + "="*70)
    print(" 시장성 평가 에이전트")
    print("="*70)

    # 1. 기업 이름 입력 받기
    print("\n[Step 1] 분석할 기업 이름을 입력하세요")
    startup_name = input("기업 이름: ").strip()

    if not startup_name:
        print(" [ERROR] 기업 이름을 입력해야 합니다.")
        return

    # 2. data 폴더에서 PDF 파일 자동 검색
    data_folder = "data"

    if not os.path.exists(data_folder):
        print(f"\n [ERROR] '{data_folder}' 폴더가 없습니다.")
        print(" 해결 방법: data/ 폴더를 생성하고 PDF 파일을 넣어주세요.")
        return

    # data 폴더의 모든 PDF 파일 찾기
    pdf_files = [f for f in os.listdir(data_folder) if f.endswith('.pdf')]

    if not pdf_files:
        print(f"\n [ERROR] '{data_folder}' 폴더에 PDF 파일이 없습니다.")
        print(" 해결 방법: data/ 폴더에 IR 자료 PDF를 넣어주세요.")
        return

    # 3. PDF 파일 선택
    print(f"\n[Step 2] '{data_folder}' 폴더에서 발견된 PDF 파일:")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"  {i}. {pdf_file}")

    if len(pdf_files) == 1:
        # PDF가 1개면 자동 선택
        selected_pdf = pdf_files[0]
        print(f"\n → 자동 선택: {selected_pdf}")
    else:
        # PDF가 여러 개면 선택 받기
        choice = input(f"\nPDF 파일 선택 (1-{len(pdf_files)}): ").strip()

        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(pdf_files):
                selected_pdf = pdf_files[choice_idx]
            else:
                print(" [ERROR] 잘못된 선택입니다.")
                return
        except ValueError:
            print(" [ERROR] 숫자를 입력해야 합니다.")
            return

    document_path = os.path.join(data_folder, selected_pdf)

    # 4. 시장성 평가 실행
    print(f"\n[Step 3] 시장성 평가 시작")
    print(f"  - 기업: {startup_name}")
    print(f"  - 문서: {document_path}")

    try:
        result = market_analyst_agent(
            startup_name=startup_name,
            document_path=document_path
        )

        # 5. 결과 저장
        os.makedirs("outputs", exist_ok=True)
        output_filename = f"{startup_name.replace(' ', '_').replace('.', '_').lower()}_market_analysis.json"
        output_path = os.path.join("outputs", output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 6. 결과 요약 출력
        print("\n" + "="*70)
        print(" 분석 완료!")
        print("="*70)
        print(f"\n✅ 결과 저장: {output_path}")

        if "summary" in result:
            print(f"\n📊 평가 요약:")
            print(f"  - 시장성 점수: {result['summary'].get('market_score', 'N/A')}점")
            print(f"  - 성공 질문: {result['summary'].get('success_count', 0)}개")
            print(f"  - 실패 질문: {result['summary'].get('failed_count', 0)}개")

        if "industry_intelligence" in result:
            print(f"\n🌐 산업 인텔리전스:")
            print(f"  - 산업 분류: {result['industry_intelligence'].get('industry_category', 'N/A')}")
            print(f"  - 뉴스 분석: {result['industry_intelligence'].get('total_news_analyzed', 0)}개")

        print(f"\n💡 상세 결과는 {output_path} 파일을 확인하세요.")

    except FileNotFoundError as e:
        print(f"\n [ERROR] PDF 파일을 찾을 수 없습니다: {document_path}")
        print(f" 오류 상세: {e}")

    except Exception as e:
        print(f"\n [ERROR] 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
