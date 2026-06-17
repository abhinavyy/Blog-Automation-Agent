from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    topics: List[Dict[str, Any]]  # All unprocessed rows loaded from Google Sheet
    current_index: int            # Pointer to the active topic
    current_topic: str            # Topic string for current row
    current_category: str         # Category for current row
    generated_blog: str           # Blog content produced by LLM
    doc_link: str                 # Google Docs URL after saving
    eval_score: Dict[str, Any]    # Quality metrics dict
    errors: List[str]             # Any node-level errors
    completed: List[str]          # Doc links of finished topics
