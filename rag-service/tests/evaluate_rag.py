import pandas as pd
import json
import requests
import time

API_URL = "http://127.0.0.1/rag/search"

golden_data = [
    {"question": "What command is used to install FastAPI with standard dependencies?", "ground_truth": "The command is pip install 'fastapi[standard]'. It is recommended to use quotes to ensure it works across all terminals."},
    {"question": "Which two libraries form the foundation of FastAPI?", "ground_truth": "FastAPI is built on Starlette for the web parts and Pydantic for the data parts."},
    {"question": "Where can I find the automatic interactive Swagger UI documentation in FastAPI?", "ground_truth": "The interactive API documentation provided by Swagger UI is available at http://127.0.0.1:8000/docs."},
    {"question": "What are the main features of the FastAPI framework?", "ground_truth": "Key features include automatic documentation (OpenAPI), Python type hints for validation, Pydantic model support, asynchronous (async/await) support, dependency injection, and built-in security (OAuth2, JWT)."},
    {"question": "How do you add LangChain using the uv package manager?", "ground_truth": "You can add LangChain using the command uv add langchain."},
    {"question": "Provide an example of initializing a GPT-5.4 model using LangChain.", "ground_truth": "Use from langchain.chat_models import init_chat_model and then initialize it with model = init_chat_model('openai:gpt-5.4')."},
    {"question": "What is LangGraph and when should it be used?", "ground_truth": "LangGraph is a framework for building controllable and complex agent workflows, used for advanced customization or agent orchestration."},
    {"question": "Which LangChain tool is designed for agent evaluations and observability?", "ground_truth": "LangSmith is the tool used for agent evaluations, observability, and debugging LLM applications."},
    {"question": "What are 'Deep Agents' according to the LangChain ecosystem?", "ground_truth": "Deep Agents are agents that can plan, use subagents, and leverage file systems to complete complex tasks."},
    {"question": "How does LangChain handle real-time data augmentation?", "ground_truth": "LangChain connects LLMs to diverse data sources and internal systems using its library of integrations with model providers, vector stores, and retrievers."},
    {"question": "Why does FastAPI use Python type hints?", "ground_truth": "FastAPI uses type hints to validate inputs, generate automatic documentation, and make the code more readable and less error-prone."},
    {"question": "Does LangChain allow swapping between different LLM models?", "ground_truth": "Yes, LangChain's abstractions allow developers to swap models in and out easily as the industry evolves without losing momentum."},
    {"question": "What platform is used to scale stateful agent workflows in LangChain?", "ground_truth": "LangSmith Deployment is the platform used to deploy and scale long-running, stateful agent workflows."},
    {"question": "Does the documentation specify how to connect FastAPI to a PostgreSQL database?", "ground_truth": "No, the provided documentation does not contain specific instructions or examples for connecting to a PostgreSQL database."},
    {"question": "What is the core purpose of the LangChain framework?", "ground_truth": "The core purpose is to simplify AI application development by chaining together components and integrations while future-proofing the technology stack."}
]

def run_my_rag(question: str):
    """
    Simulates a cURL request to Nginx/FastAPI for global search.
    """
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": question,
        "top_k": 10  
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status() 
        
        data = response.json()
        
        answer = data.get("answer", "")
        contexts = data.get("contexts", [])
        
        return answer, contexts
        
    except requests.exceptions.RequestException as e:
        print(f"API Error for question '{question}': {e}")
        return "ERROR", []

results = []

print("Starting RAG evaluation\n")

for i, item in enumerate(golden_data, 1):
    q = item["question"]
    print(f"[{i}/{len(golden_data)}] Processing: {q}")
    
    answer, contexts = run_my_rag(q)
    
    results.append({
        "question": q,
        "answer": answer,
        "contexts": contexts,
        "ground_truth": item["ground_truth"]
    })
    
    time.sleep(1)

df = pd.DataFrame(results)

with open("rag_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print("\nDone! File 'rag_test_results.json' is ready.")