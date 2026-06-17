import os
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

def get_llm():
    """
    Factory function to retrieve ChatGroq or ChatOllama LLM instance
    based on the LLM_PROVIDER environment variable.
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower().strip()
    
    if provider == "groq":
        # Lazy import to avoid loading issues if the package is not used
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or "your_key_here" in api_key:
            raise ValueError(
                "GROQ_API_KEY is not set or is using the default placeholder in .env. "
                "Please configure a valid API key."
            )
        model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
        return ChatGroq(
            api_key=api_key,
            model_name=model,
            temperature=0.7
        )
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        model = os.getenv("OLLAMA_MODEL", "llama3")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.7
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Must be either 'groq' or 'ollama'."
        )
