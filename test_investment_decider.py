# test_investment_decider.py
from agent_module import investment_decider_node

# ─────────────── 테스트 입력 데이터 ───────────────
state = {
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
        "positives": ["헬스케어 시장 성장세", "기술 독창성", "탄탄한 팀 구성"],
        "risks": ["규제 리스크 존재"],
        "evidence_sources": ["https://example.com/report1", "https://example.com/report2"]
    },
    "competitor_eval": {
        "target_name": "TestTarget",
        "items": [
            {"name": "CompetitorA", "rating": 4},
            {"name": "CompetitorB", "rating": 3},
            {"name": "CompetitorC", "rating": 5}
        ],
        "evidence_sources": ["https://example.com/competitor"]
    }
}

# ─────────────── 테스트 실행 ───────────────
result = investment_decider_node(state)

# ─────────────── 결과 출력 ───────────────
import json
print(json.dumps(result, indent=2, ensure_ascii=False))
