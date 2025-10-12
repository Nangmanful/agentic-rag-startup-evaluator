# graph_investment.py
try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    from langgraph import StateGraph, START, END

from agent_module import investment_decider_node

g = StateGraph(dict)

# 노드 등록
g.add_node("investment_decider", investment_decider_node)

# ✅ 엔트리포인트(시작 엣지) 추가
g.add_edge(START, "investment_decider")

# 종료 엣지
g.add_edge("investment_decider", END)

graph = g.compile()
