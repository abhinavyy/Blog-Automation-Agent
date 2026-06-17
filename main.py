import sys
from dotenv import load_dotenv
from agent.graph import get_graph
from utils.gdocs_handler import get_gdocs_service
from utils.llm_factory import get_llm

def main():
    # 1. Load environment variables
    load_dotenv()
    
    print("=========================================")
    print("   LANGGRAPH BLOG AUTOMATION AGENT       ")
    print("=========================================\n")
    
    # 2. Check LLM configuration
    print("Checking LLM configuration...")
    try:
        llm = get_llm()
        print("[OK] LLM initialized successfully.\n")
    except Exception as e:
        print(f"[ERROR] Error initializing LLM: {str(e)}")
        print("Please check your .env configuration and try again.")
        sys.exit(1)
        
    # 3. Check and authenticate Google Docs API
    print("Checking Google Docs authentication...")
    try:
        docs_service, drive_service = get_gdocs_service()
        print("[OK] Google Docs and Drive services initialized successfully.\n")
    except FileNotFoundError as e:
        print(f"[ERROR] Google Credentials file missing: {str(e)}")
        print("\nTo fix this:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Create a project and enable 'Google Docs API' and 'Google Drive API'")
        print("3. Configure OAuth Consent Screen (external, add testing users if in Desktop mode)")
        print("4. Go to Credentials -> Create Credentials -> OAuth client ID (Desktop app)")
        print("5. Download the JSON and save it as 'credentials/google_creds.json'")
        print("\nExiting agent workflow...")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error initializing Google API: {str(e)}")
        sys.exit(1)

    # 4. Compile the Graph
    print("Compiling LangGraph workflow...")
    try:
        graph = get_graph()
        print("[OK] LangGraph compiled successfully.\n")
    except Exception as e:
        print(f"[ERROR] Error compiling graph: {str(e)}")
        sys.exit(1)
        
    # 5. Run the graph
    watch_mode = "--watch" in sys.argv
    initial_state = {
        "topics": [],
        "current_index": 0,
        "current_topic": "",
        "current_category": "",
        "generated_blog": "",
        "doc_link": "",
        "eval_score": {},
        "errors": [],
        "completed": []
    }
    
    if watch_mode:
        import time
        print("Running in WATCH mode. Monitoring for new topics every 60 seconds...")
        print("Press Ctrl+C to stop.\n")
        try:
            while True:
                # Copy initial state and run clean workflow
                run_state = initial_state.copy()
                run_state["errors"] = []
                run_state["completed"] = []
                
                final_state = graph.invoke(run_state)
                topics = final_state.get("topics", [])
                completed = final_state.get("completed", [])
                errors = final_state.get("errors", [])
                
                if len(topics) > 0:
                    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] [WATCH] Processed {len(topics)} topic(s).")
                    if completed:
                        print(f"  Successfully published: {len(completed)}")
                        for link in completed:
                            print(f"    - {link}")
                    if errors:
                        print(f"  Errors encountered: {len(errors)}")
                        for err in errors:
                            print(f"    - {err}")
                
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nWatch mode stopped by user. Exiting...")
            sys.exit(0)
    else:
        print("Starting processing workflow (single-run)...")
        try:
            final_state = graph.invoke(initial_state)
        except Exception as e:
            print(f"[ERROR] Workflow execution failed catastrophically: {str(e)}")
            sys.exit(1)
            
        # 6. Print final summary
        print("\n=========================================")
        print("           WORKFLOW SUMMARY              ")
        print("=========================================")
        
        topics = final_state.get("topics", [])
        completed = final_state.get("completed", [])
        errors = final_state.get("errors", [])
        
        total_topics = len(topics)
        succeeded_count = len(completed)
        failed_count = total_topics - succeeded_count
        
        print(f"Total topics processed: {total_topics}")
        print(f"Successfully published: {succeeded_count}")
        print(f"Failed / Skipped:       {failed_count}")
        
        if completed:
            print("\nPublished Google Docs Links:")
            for idx, link in enumerate(completed, 1):
                print(f"  {idx}. {link}")
                
        if errors:
            print("\nEncountered Errors:")
            for idx, err in enumerate(errors, 1):
                print(f"  {idx}. {err}")
                
        print("=========================================\n")

if __name__ == "__main__":
    main()
