from google import genai
from google.genai import types
import graphviz
import re
import os
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """You are a Graph Transpiler. Your ONLY job is to analyze a question about a graph/network and output valid Graphviz DOT code.

ANALYSIS RULES:
1. Identify all nodes (entities, people, locations, or labeled items)
2. Identify all edges (connections, relationships, links between nodes)
3. Determine if the graph is directed (arrows/flow) or undirected (plain connections)
4. Detect if edges have weights or labels

OUTPUT RULES:
- Output ONLY valid DOT code. No explanation, no markdown, no backticks.
- Use "digraph G" for directed graphs, "graph G" for undirected
- Use descriptive node labels if names are given
- For weighted edges use: A -- B [label="5"]
- Apply rankdir=LR for left-to-right flow, TB for top-to-bottom trees
- Style nodes: node [shape=circle, style=filled, fillcolor="#AED6F1", fontname="Helvetica"]
- Style edges: edge [fontsize=10]

FEW-SHOT EXAMPLES:

Input: "A social media network. 8 is connected to 5 and 7. 5 is connected to 4 and 6. 4 connects to 3 and 1. 6 connects to 7 and 9. 2 connects to 1 and 3."
Output:
graph G {
  node [shape=circle, style=filled, fillcolor="#AED6F1", fontname="Helvetica"]
  8 -- 5; 8 -- 7;
  5 -- 4; 5 -- 6;
  4 -- 3; 4 -- 1;
  6 -- 7; 6 -- 9;
  2 -- 1; 2 -- 3;
}

Input: "Nodes A, B, C, D, E, F, G, H. B connects to C, D, A. D connects to E and A. E connects to G, H, F. H connects to G."
Output:
graph G {
  node [shape=circle, style=filled, fillcolor="#A9DFBF", fontname="Helvetica"]
  B -- C; B -- D; B -- A;
  D -- E; D -- A;
  E -- G; E -- H; E -- F;
  H -- G;
}

Input: "A directed workflow: Start -> Parse -> Validate -> Process. Validate can also go to Error. Error goes back to Parse."
Output:
digraph G {
  rankdir=LR
  node [shape=box, style=filled, fillcolor="#FAD7A0", fontname="Helvetica"]
  Start -> Parse -> Validate -> Process;
  Validate -> Error;
  Error -> Parse;
}

Input: "A weighted graph: A to B costs 4, A to C costs 2, B to C costs 1, B to D costs 5, C to D costs 8."
Output:
graph G {
  node [shape=circle, style=filled, fillcolor="#D7BDE2", fontname="Helvetica"]
  A -- B [label="4"]
  A -- C [label="2"]
  B -- C [label="1"]
  B -- D [label="5"]
  C -- D [label="8"]
}

Now analyze the user's question and output ONLY the DOT code."""


def question_to_dot(question: str) -> str:
    """
    Step 1 & 2: Send question to Gemini, get back DOT code.
    """
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    raw = response.text.strip()
    cleaned = re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()
    return cleaned


def dot_to_image(dot_code: str, output_path: str = "graph", fmt: str = "png") -> str:
    """
    Step 3: Render DOT code to an image using Graphviz.
    Returns the final output file path.
    """
    # Detect graph type from DOT code
    source = graphviz.Source(dot_code)
    source.format = fmt
    output_file = source.render(filename=output_path, cleanup=True)
    return output_file


def generate_graph(question: str, output_path: str = "graph", fmt: str = "png") -> dict:
    """
    Full pipeline: question -> DOT code -> image file.

    Args:
        question:    Plain text or descriptive graph question
        output_path: Output file path (without extension)
        fmt:         Output format — 'png', 'svg', 'pdf'

    Returns:
        dict with 'dot_code' and 'output_file' keys
    """
    print(f"\n[1/3] Analyzing question...")
    dot_code = question_to_dot(question)
    print(f"      DOT code generated ({len(dot_code)} chars)")
    print(f"\n--- DOT CODE ---\n{dot_code}\n----------------\n")

    print(f"[2/3] Rendering graph to {fmt.upper()}...")
    output_file = dot_to_image(dot_code, output_path=output_path, fmt=fmt)
    print(f"[3/3] Done! Saved to: {output_file}")

    return {
        "dot_code": dot_code,
        "output_file": output_file,
    }


# ── Example usage ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    examples = [
        {
            "question": "Nodes A, B, C, D, E, F, G, H. B connects to C, D, and A. D connects to E and A. E connects to G, H, and F. H connects to G.",
            "output": "output/graph_undirected",
        },
        {
            "question": "A social media network: 8 is connected to 5 and 7. 5 connects to 4 and 6. 4 connects to 3 and 1. 6 connects to 7 and 9. 2 connects to 1 and 3.",
            "output": "output/graph_social",
        },
        {
            "question": "A directed workflow: Login -> Dashboard. Dashboard -> Profile and Settings. Profile -> EditProfile. Settings -> Logout. EditProfile -> Dashboard.",
            "output": "output/graph_directed",
        },
        {
            "question": "Weighted graph: City A to B costs 4, A to C costs 2, B to D costs 5, C to D costs 8, C to E costs 3, D to E costs 1.",
            "output": "output/graph_weighted",
        },
    ]

    os.makedirs("output", exist_ok=True)

    for i, ex in enumerate(examples, 1):
        print(f"\n{'='*50}")
        print(f"Example {i}: {ex['question'][:60]}...")
        result = generate_graph(
            question=ex["question"],
            output_path=ex["output"],
            fmt="png",
        )
        time.sleep(5)  # avoid rate limits