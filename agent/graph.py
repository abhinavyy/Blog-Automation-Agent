from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    load_topics,
    pick_next_topic,
    generate_blog,
    evaluate_blog,
    save_to_gdocs,
    update_sheet
)

def check_done(state: AgentState) -> str:
    """
    Conditional edge function from update_sheet.
    Returns "pick_next" if there are more topics to process, otherwise "end".
    """
    topics = state.get("topics", [])
    current_index = state.get("current_index", 0)
    
    if current_index >= len(topics):
        return "end"
    else:
        return "pick_next"

def get_graph():
    """
    Constructs, connects, and compiles the LangGraph StateGraph.
    """
    workflow = StateGraph(AgentState)
    
    # 1. Define nodes
    workflow.add_node("load_topics", load_topics)
    workflow.add_node("pick_next_topic", pick_next_topic)
    workflow.add_node("generate_blog", generate_blog)
    workflow.add_node("evaluate_blog", evaluate_blog)
    workflow.add_node("save_to_gdocs", save_to_gdocs)
    workflow.add_node("update_sheet", update_sheet)
    
    # 2. Set entry point
    workflow.set_entry_point("load_topics")
    
    # 3. Add linear edges
    workflow.add_edge("load_topics", "pick_next_topic")
    workflow.add_edge("pick_next_topic", "generate_blog")
    workflow.add_edge("generate_blog", "evaluate_blog")
    workflow.add_edge("evaluate_blog", "save_to_gdocs")
    workflow.add_edge("save_to_gdocs", "update_sheet")
    
    # 4. Add conditional edge from update_sheet to check if done
    workflow.add_conditional_edges(
        "update_sheet",
        check_done,
        {
            "pick_next": "pick_next_topic",
            "end": END
        }
    )
    
    return workflow.compile()
