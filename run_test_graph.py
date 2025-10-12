# run_test_graph.py
from graph_investment import graph

# 테스트용 state
init_state = {
    "market_eval": {
        "method": "scorecard",
        "scorecard": {
            "management_team": 8,
            "market_size": 9,
            "product_technology": 7,
            "competitive_environment": 6,
            "marketing_sales": 8,
            "need_for_additional_investment": 7
        },
        "positives": ["헬스케어 시장 성장세", "기술 독창성"],
        "risks": ["규제 리스크"],
        "evidence_sources": ["https://example.com/report1"]
    },
    "competitor_eval": {
        "target_name": "테스트 타겟",
        "items": [
            {"name": "CompetitorA", "rating": 4},
            {"name": "CompetitorB", "rating": 5}
        ],
        "evidence_sources": ["https://example.com/competitor"]
    }
}

# LangGraph 실행
final_state = graph.invoke(init_state)

# 결과 확인
import json
print(json.dumps(final_state, indent=2, ensure_ascii=False))
