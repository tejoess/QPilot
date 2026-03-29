import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from the backend directory
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_syllabus(file_path):
    # Handle both relative and absolute paths
    if not os.path.isabs(file_path):
        # Default to backend/services/data/
        file_path = os.path.join(os.path.dirname(__file__), "data", file_path)
    
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def generate_structured_tree(syllabus_data):
    prompt = f"""
You are an academic curriculum formatter.

Given the syllabus JSON below, generate a clean hierarchical tree structure 
in EXACTLY the following format:

Subject Name
 └── Module 1: Module Name
       └── Topic: Topic Name
             └── Subtopic: Subtopic Name

Rules:
- Use EXACT indentation.
- Use the └── symbol exactly as shown.
- Do NOT return JSON.
- Do NOT add explanations.
- Return ONLY the formatted tree.

Here is the syllabus JSON:

{json.dumps(syllabus_data, indent=2)}
"""

    if not os.getenv("OPENAI_API_KEY"):
        return "Error: OPENAI_API_KEY not found in environment."

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You generate structured curriculum trees."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()

def generate_knowledge_graph(syllabus_data):
    prompt = f"""
You are an AI curriculum analyzer.

Given this syllabus JSON, analyze:

1. Concept dependencies (e.g., Probability → GAN → VAE).
2. Prerequisite relationships.
3. Logical concept hierarchy.
4. Cross-module dependencies.

Return ONLY JSON in this format:

{{
  "nodes": [
    {{ "id": "...", "label": "...", "type": "subject/module/topic" }}
  ],
  "edges": [
    {{ "from": "...", "to": "...", "relationship": "contains/prerequisite/dependent" }}
  ]
}}

Syllabus JSON:

{json.dumps(syllabus_data, indent=2)}
"""

    if not os.getenv("OPENAI_API_KEY"):
        return json.dumps({"error": "OPENAI_API_KEY not found in environment."})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You generate academic knowledge graphs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()

def main():
    try:
        # Using the file updated in the previous step
        filename = "ai_knowledge_base.json"
        syllabus = load_syllabus(filename)
        
        # 1. Generate Tree
        tree_output = generate_structured_tree(syllabus)
        print("\n=== GENERATED KNOWLEDGE STRUCTURE ===\n")
        print(tree_output)

        # 2. Generate Knowledge Graph (Requested)
        graph = generate_knowledge_graph(syllabus)
        print("\n=== GENERATED KNOWLEDGE GRAPH ===\n")
        print(graph)

    except FileNotFoundError:
        print("Error: 'ai_knowledge_base.json' not found in backend/services/data/")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()