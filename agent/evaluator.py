import re
import json
from typing import Dict, Any
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Cleans up common LLM code-block markdown or leading/trailing characters
    to parse a clean JSON object.
    """
    cleaned = text.strip()
    # Strip markdown JSON fences if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    # Try to find the first '{' and last '}'
    start_idx = cleaned.find('{')
    end_idx = cleaned.rfind('}')
    if start_idx != -1 and end_idx != -1:
        cleaned = cleaned[start_idx:end_idx + 1]
        
    return json.loads(cleaned)

def run_heuristics(blog_content: str, topic: str) -> Dict[str, Any]:
    """
    Runs evaluation metrics WITHOUT calling an LLM:
      a. word_count: count words in generated_blog
      b. has_headings: count of "##" >= 3
      c. has_intro: "introduction" appears in blog (case-insensitive)
      d. keyword_hit: topic keyword appears in first 100 words
      e. passes: True if word_count > 600 and has_headings and keyword_hit
    """
    # Clean blog content
    words = blog_content.split()
    word_count = len(words)
    
    # Check for "##" headings
    # We count occurrences of ## at the start of lines or inside
    heading_count = blog_content.count("##")
    has_headings = heading_count >= 3
    
    # Check for "introduction" (case-insensitive)
    has_intro = "introduction" in blog_content.lower()
    
    # Check for keyword hit in first 100 words
    first_100_words_str = " ".join(words[:100]).lower()
    
    # Extract keywords from the topic
    # Remove common stop words and keep alphanumeric words of length >= 2
    stop_words = {
        'in', 'on', 'at', 'to', 'for', 'of', 'and', 'the', 'a', 'an', 'is', 'are', 
        'was', 'were', 'with', 'how', 'why', 'what', 'top', 'new', 'top-5', 'top 5'
    }
    topic_cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', topic).lower()
    topic_words = re.split(r'[\s-]+', topic_cleaned)
    keywords = [w for w in topic_words if len(w) >= 2 and w not in stop_words]
    
    # If no keywords left after filtering, default to all words in topic of length >= 2
    if not keywords:
        keywords = [w for w in topic_words if len(w) >= 2]
        
    keyword_hit = False
    matched_keywords = []
    for kw in keywords:
        # Check if the keyword exists as a substring or full word in the first 100 words
        if kw in first_100_words_str:
            keyword_hit = True
            matched_keywords.append(kw)
            
    # Combined pass criteria
    passes = bool(word_count > 600 and has_headings and keyword_hit)
    
    return {
        "word_count": word_count,
        "has_headings": has_headings,
        "heading_count": heading_count,
        "has_intro": has_intro,
        "keyword_hit": keyword_hit,
        "matched_keywords": matched_keywords,
        "passes": passes
    }

def run_llm_judge(llm: BaseChatModel, blog_content: str, topic: str, category: str) -> Dict[str, int]:
    """
    Calls the LLM as a judge to evaluate relevance, coherence, seo, readability,
    and actionability, returning JSON scores (1-5).
    """
    system_prompt = (
        "You are an expert editor and blog quality evaluator.\n"
        "Analyze the provided blog post and score it from 1 to 5 (integer only, 5 = excellent, 1 = poor) "
        "on five key criteria:\n"
        "1. relevance: Is the content directly relevant to the category and topic?\n"
        "2. coherence: Is the blog logically structured and easy to follow?\n"
        "3. seo: Are key terms and subheadings used effectively for search optimization?\n"
        "4. readability: Is the tone appropriate and vocabulary clear and accessible?\n"
        "5. actionability: Does the blog provide practical, actionable takeaways for decision makers?\n\n"
        "You MUST return ONLY a valid JSON object with the exact keys: "
        "'relevance', 'coherence', 'seo', 'readability', 'actionability'.\n"
        "Do not include any intro, explanation, markdown formatting, or trailing text. Only return the JSON."
    )
    
    user_prompt = (
        f"Category: {category}\n"
        f"Topic: {topic}\n\n"
        f"Blog Post Content:\n"
        f"-----------------\n"
        f"{blog_content}\n"
        f"-----------------\n"
    )
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        scores = clean_and_parse_json(response.content)
        
        # Verify and clamp scores
        valid_keys = {"relevance", "coherence", "seo", "readability", "actionability"}
        clamped_scores = {}
        for key in valid_keys:
            score = scores.get(key, 3) # default to 3 if missing
            try:
                score = int(score)
                score = max(1, min(5, score)) # clamp 1-5
            except (ValueError, TypeError):
                score = 3
            clamped_scores[key] = score
        return clamped_scores
    except Exception as e:
        # Fallback scores in case LLM judge fails
        return {
            "relevance": 0,
            "coherence": 0,
            "seo": 0,
            "readability": 0,
            "actionability": 0,
            "judge_error": str(e)
        }
