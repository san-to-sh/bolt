"""LangGraph definition: plan → act → synthesize → workpaper."""

from langgraph.graph import END, StateGraph

from .nodes import (
    MCPManager,
    act_node,
    plan_node,
    set_mcp_manager,
    should_continue_acting,
    synthesize_node,
    workpaper_node,
)
from .state import AgentState


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("plan", plan_node)
    graph.add_node("act", act_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("workpaper", workpaper_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "act")
    graph.add_conditional_edges("act", should_continue_acting, {"act": "act", "synthesize": "synthesize"})
    graph.add_edge("synthesize", "workpaper")
    graph.add_edge("workpaper", END)

    return graph


async def run_procedure(procedure: dict) -> AgentState:
    """Open MCP servers, run the audit procedure through the graph, return final state."""
    async with MCPManager() as manager:
        set_mcp_manager(manager)

        graph = build_graph()
        app = graph.compile()

        initial_state: AgentState = {
            "procedure": procedure,
            "plan": "",
            "tool_calls": [],
            "evidence": {},
            "reasoning_trace": [],
            "workpaper": {},
            "act_count": 0,
        }

        final_state = await app.ainvoke(initial_state)
        return final_state
