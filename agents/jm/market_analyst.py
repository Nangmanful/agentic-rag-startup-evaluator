"""
시장성 평가 에이전트 메인 인터페이스
메인 그래프에서 호출되는 market_analyst_agent 함수 제공
"""

from jm.agents.state import create_initial_state
from jm.agents.graph import build_market_analysis_graph


def market_analyst_agent(startup_name: str, document_path: str) -> dict:
    """
    시장성 평가 에이전트 실행 함수

    이 함수는 메인 그래프의 "market_eval" 노드에서 호출됩니다.

    Args:
        startup_name: 스타트업 이름
        document_path: 분석할 PDF 문서 경로

    Returns:
        dict: 최종 분석 보고서
        {
            "startup_name": str,
            "analysis_type": str,
            "bessemer_checklist": dict,
            "scorecard_method": dict,
            "summary": dict
        }
    """

    print("\n" + "="*70)
    print(f" 시장성 평가 에이전트 시작: {startup_name}")
    print("="*70)

    # 1. 초기 State 생성
    initial_state = create_initial_state(
        document_path=document_path,
        startup_name=startup_name
    )

    # 2. 시장성 평가 그래프 구축
    market_graph = build_market_analysis_graph()

    # 3. 그래프 실행 (recursion_limit 설정)
    try:
        result = market_graph.invoke(
            initial_state,
            config={"recursion_limit": 100}  # 기본 25 → 50으로 증가
        )

        # 4. 최종 보고서 추출
        final_report = result.get("final_report", {})

        print("\n" + "="*70)
        print(" 시장성 평가 완료!")
        print("="*70)

        return final_report

    except Exception as e:
        print(f"\n [ERROR] 시장성 평가 중 오류 발생: {e}")
        return {
            "startup_name": startup_name,
            "error": str(e),
            "status": "failed"
        }


# 메인 그래프 State와 통합할 때 사용하는 래퍼 함수
def market_analyst_node(state: dict) -> dict:
    """
    메인 그래프의 State와 통합하기 위한 래퍼 함수

    메인 그래프 State 예시:
    {
        "startup_name": str,
        "startup_info": dict,
        "tech_summary": dict,
        "market_analysis": dict,  # ← 이 에이전트가 채울 부분
        ...
    }

    Usage in main graph:
        from market_analyst import market_analyst_node
        main_workflow.add_node("market_eval", market_analyst_node)
    """

    # 메인 State에서 필요한 정보 추출
    startup_name = state.get("startup_name", "Unknown")
    document_path = state.get("document_path", f"data/{startup_name}_IR.pdf")

    # 시장성 평가 실행
    market_analysis = market_analyst_agent(
        startup_name=startup_name,
        document_path=document_path
    )

    # 메인 State 업데이트
    return {
        "market_analysis": market_analysis
    }


if __name__ == "__main__":
    # 테스트 실행
    print("시장성 평가 에이전트 테스트 실행")

    # 테스트용 더미 데이터
    test_result = market_analyst_agent(
        startup_name="Test Startup",
        document_path="data/test_ir.pdf"
    )

    print("\n[테스트 결과]")
    print(test_result)
