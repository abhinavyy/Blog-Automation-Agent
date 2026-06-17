import os
from typing import Dict, Any
from agent.state import AgentState
from utils.gsheets_handler import read_unprocessed_topics_from_sheets, update_blog_link_in_sheets
from utils.gdocs_handler import create_doc
from utils.llm_factory import get_llm
from agent.evaluator import run_heuristics, run_llm_judge
from langchain_core.messages import SystemMessage, HumanMessage

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEET_RANGE = os.getenv("GOOGLE_SHEET_RANGE", "Sheet1!A:D")

def load_topics(state: AgentState) -> Dict[str, Any]:
    """
    Reads topics from the configured Google Sheet.
    Filters rows where the Link column is empty.
    """
    try:
        # Initialize lists in state
        errors = state.get("errors") or []
        completed = state.get("completed") or []
        
        if not GOOGLE_SHEET_ID:
            raise ValueError("GOOGLE_SHEET_ID is not set in .env. Please configure it.")
        
        print(f"Loading topics from Google Sheet: {GOOGLE_SHEET_ID} (Range: {GOOGLE_SHEET_RANGE})...")
        topics = read_unprocessed_topics_from_sheets(GOOGLE_SHEET_ID, GOOGLE_SHEET_RANGE)
            
        return {
            "topics": topics,
            "current_index": 0,
            "current_topic": "",
            "current_category": "",
            "generated_blog": "",
            "doc_link": "",
            "eval_score": {},
            "errors": errors,
            "completed": completed
        }
    except Exception as e:
        err_msg = f"Failed to load topics from Google Sheets: {str(e)}"
        print(f"ERROR: {err_msg}")
        errors = state.get("errors") or []
        errors.append(err_msg)
        return {
            "topics": [],
            "current_index": 0,
            "errors": errors
        }

def pick_next_topic(state: AgentState) -> Dict[str, Any]:
    """
    Pulls topics[current_index] from state and sets current_topic and current_category.
    Resets temporary fields for the current topic.
    """
    try:
        topics = state.get("topics", [])
        idx = state.get("current_index", 0)
        
        if idx < len(topics):
            current = topics[idx]
            return {
                "current_topic": current["topic"],
                "current_category": current["category"],
                "generated_blog": "",
                "doc_link": "",
                "eval_score": {}
            }
        return {}
    except Exception as e:
        err_msg = f"Error in pick_next_topic: {str(e)}"
        errors = state.get("errors", [])
        errors.append(err_msg)
        return {"errors": errors}

def generate_blog(state: AgentState) -> Dict[str, Any]:
    """
    Loads system prompt and calls LLM to generate the blog post.
    """
    topic = state.get("current_topic")
    category = state.get("current_category")
    errors = state.get("errors", [])

    if not topic:
        return {}

    try:
        # Read system prompt
        prompt_path = os.path.join("prompts", "blog_writer.txt")
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"System prompt file not found at {prompt_path}")
            
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        llm = get_llm()
        
        user_message = f"Category: {category}\nTopic: {topic}\n\nWrite the blog post now."
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        print(f"Generating blog post for topic: '{topic}'...")
        response = llm.invoke(messages)
        generated_blog = response.content
        
        return {
            "generated_blog": generated_blog
        }
    except Exception as e:
        err_msg = f"Error generating blog for '{topic}': {str(e)}"
        print(f"ERROR: {err_msg}")
        errors.append(err_msg)
        return {
            "generated_blog": "",
            "errors": errors
        }

def evaluate_blog(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates blog content using heuristics and an LLM-as-judge.
    Skips if generation failed.
    """
    blog_content = state.get("generated_blog")
    topic = state.get("current_topic")
    category = state.get("current_category")
    errors = state.get("errors", [])

    if not blog_content or not topic:
        # Skip if no blog was generated
        return {}

    try:
        # Run local heuristics
        heuristics_score = run_heuristics(blog_content, topic)
        
        # Run LLM judge
        llm = get_llm()
        judge_scores = run_llm_judge(llm, blog_content, topic, category)
        
        # Merge results
        eval_score = {**heuristics_score, **judge_scores}
        
        return {
            "eval_score": eval_score
        }
    except Exception as e:
        err_msg = f"Error evaluating blog for '{topic}': {str(e)}"
        print(f"ERROR: {err_msg}")
        errors.append(err_msg)
        return {
            "eval_score": {"error": str(e)},
            "errors": errors
        }

def save_to_gdocs(state: AgentState) -> Dict[str, Any]:
    """
    Saves the generated blog to Google Docs and marks it shareable.
    Skips if generation failed.
    """
    blog_content = state.get("generated_blog")
    topic = state.get("current_topic")
    errors = state.get("errors", [])

    if not blog_content or not topic:
        # Skip if no blog was generated
        return {}

    try:
        print(f"Saving blog to Google Docs: '{topic}'...")
        doc_link = create_doc(title=topic, content=blog_content)
        print(f"Doc saved successfully: {doc_link}")
        return {
            "doc_link": doc_link
        }
    except Exception as e:
        err_msg = f"Error saving Google Doc for '{topic}': {str(e)}"
        print(f"ERROR: {err_msg}")
        errors.append(err_msg)
        return {
            "doc_link": "",
            "errors": errors
        }

def update_sheet(state: AgentState) -> Dict[str, Any]:
    """
    Updates the blog link and date in Google Sheets, increments current_index,
    and appends the doc link to completed.
    """
    topics = state.get("topics", [])
    idx = state.get("current_index", 0)
    doc_link = state.get("doc_link", "")
    completed = state.get("completed", [])
    errors = state.get("errors", [])

    if idx >= len(topics):
        return {}

    current_item = topics[idx]
    row_idx = current_item.get("row_index")
    topic_name = current_item.get("topic")

    try:
        if doc_link:
            print(f"Updating Google Sheet row {row_idx} for topic '{topic_name}' with link: {doc_link}")
            update_blog_link_in_sheets(GOOGLE_SHEET_ID, row_idx, doc_link, GOOGLE_SHEET_RANGE)
            completed.append(doc_link)
        else:
            print(f"Skipping update for row {row_idx} ('{topic_name}') due to previous errors.")
    except Exception as e:
        err_msg = f"Error updating Google Sheets at row {row_idx} for '{topic_name}': {str(e)}"
        print(f"ERROR: {err_msg}")
        errors.append(err_msg)

    # Always increment index to move to next topic
    return {
        "current_index": idx + 1,
        "completed": completed,
        "errors": errors
    }
