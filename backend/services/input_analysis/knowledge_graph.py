import sys
import os

# Add project root to sys.path so this file can run standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import json
from dotenv import load_dotenv
from openai import OpenAI
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser


def _extract_first_json_object(text: str) -> str:
    """
    Extract the first complete JSON object found in a text blob.
    This is robust to LLM responses that include surrounding prose.
    """
    start = text.find("{")
    if start == -1:
        return text

    # Find a plausible end by scanning for the last matching closing brace.
    # This assumes the first object is the one we want.
    end = text.rfind("}")
    if end == -1 or end <= start:
        return text[start:]
    return text[start : end + 1]


def _parse_structured_tree_content(content: str) -> dict:
    """
    Parse the structured knowledge graph content returned by `generate_structured_tree`.
    Expected format is JSON like:
      { "Subject": "...", "Modules": [ { "Module_Name": "...", "Topics": [ ... ] } ] }
    """
    try:
        raw = _extract_first_json_object(content)
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return {"error": "Knowledge graph output was not a JSON object.", "raw": content}
    except Exception as e:
        return {"error": f"Failed to parse knowledge graph JSON: {e}", "raw": content}


def build_knowledge_graph_from_minimal_syllabus(syllabus_subset: dict, llm_client) -> dict:
    """
    Build and return a parsed knowledge graph JSON dict from a minimal syllabus subset.
    The subset should include:
      - course_name
      - modules[module_name].topics[]
    """
    structured_tree_content = generate_structured_tree(syllabus_subset, llm_client)
    if not structured_tree_content:
        return {"error": "Knowledge graph LLM returned empty content."}
    return _parse_structured_tree_content(structured_tree_content)



# Load .env from the backend directory
# env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
# load_dotenv(dotenv_path=env_path)

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def load_syllabus(file_path):
#     # Handle both relative and absolute paths
#     if not os.path.isabs(file_path):
#         # Default to backend/services/data/
#         file_path = os.path.join(os.path.dirname(__file__), "data", file_path)
    
#     with open(file_path, "r", encoding="utf-8") as file:
#         return json.load(file)

def generate_structured_tree(syllabus_data, llm):
    prompt = f"""
You are an academic curriculum formatter.

Given the syllabus JSON below, generate a clean knowledge graph for the subjects, modules and topics. 
in EXACTLY the following format:
subject name could be grand parent node.
Modules could be child nodes of subjects 
Now each unit topic is child node of each module.
Subtopic is based on revenace and hierary of the topic. 
Return this in structured knowledge graph in the JSON format. 
Ensure the subtopic is part of the topic and topic is part of the module.
Do not output general subtopics only architecture types. always output the topic name with it. for e.g "GAN architecture" can be a subtoptic, but not only "Types".
Ensure types, variants are subtopic not topic. 

Example output:

{{
  "Subject": "Artificial Intelligence",
  "Modules": [
    {{
      "Module_Name": "Machine Learning",
      "Topics": [
        {{
          "Topic_Name": "Classification",
          "Subtopics": [
            "Decision Trees",
            "K-Nearest Neighbors",
            "Support Vector Machines"
          ]
        }}
      ]
    }}
  ]
}}
Here is the syllabus JSON:

{json.dumps(syllabus_data, indent=2)}
"""

    # if not os.getenv("OPENAI_API_KEY"):
    #     return "Error: OPENAI_API_KEY not found in environment."

    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {"role": "system", "content": "You generate structured curriculum trees."},
    #         {"role": "user", "content": prompt}
    #     ],
    #     temperature=0
    # )
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content

    return content 

# def generate_knowledge_graph(syllabus_data):
#     prompt = f"""
# You are an AI curriculum analyzer.

# Given this syllabus JSON, analyze:

# 1. Concept dependencies (e.g., Probability → GAN → VAE).
# 2. Prerequisite relationships.
# 3. Logical concept hierarchy.
# 4. Cross-module dependencies.

# Return ONLY JSON in this format:

# {{
#   "nodes": [
#     {{ "id": "...", "label": "...", "type": "subject/module/topic" }}
#   ],
#   "edges": [
#     {{ "from": "...", "to": "...", "relationship": "contains/prerequisite/dependent" }}
#   ]
# }}

# Syllabus JSON:

# {json.dumps(syllabus_data, indent=2)}
# """

#     if not os.getenv("OPENAI_API_KEY"):
#         return json.dumps({"error": "OPENAI_API_KEY not found in environment."})

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "system", "content": "You generate academic knowledge graphs."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0
#     )

#     return response.choices[0].message.content.strip()

# def main():
#     try:
#         # Using the file updated in the previous step
#         filename = "ai_knowledge_base.json"
#         syllabus = {
#         "course_code": "CSC701",
#         "course_name": "Deep Learning",
#         "course_objectives": [
#             "To learn the fundamentals of Neural Network.",
#             "To gain an in-depth understanding of training Deep Neural Networks.",
#             "To acquire knowledge of advanced concepts of Convolution Neural Networks, Autoencoders and Recurrent Neural Networks.",
#             "Students should be familiar with the recent trends in Deep Learning."
#         ],
#         "course_outcomes": [
#             "Gain basic knowledge of Neural Networks.",
#             "Acquire in depth understanding of training Deep Neural Networks.",
#             "Design appropriate DNN model for supervised, unsupervised and sequence learning applications.",
#             "Gain familiarity with recent trends and applications of Deep Learning."
#         ],
#         "modules": [
#             {
#             "module_number": 1,
#             "module_name": "Fundamentals of Neural Network",
#             "weightage_hours": 4,
#             "topics": [
#                 "History of Deep Learning",
#                 "Deep Learning Success Stories",
#                 "Multilayer Perceptrons (MLPs)",
#                 "Representation Power of MLPs",
#                 "Sigmoid Neurons",
#                 "Gradient Descent",
#                 "Feedforward Neural Networks",
#                 "Representation Power of Feedforward Neural Networks",
#                 "Deep Networks: Three Classes of Deep Learning Basic Terminologies of Deep Learning"
#             ]
#             },
#             {
#             "module_number": 2,
#             "module_name": "Training, Optimization and Regularization of Deep Neural Network",
#             "weightage_hours": 10,
#             "topics": [
#                 "Training Feedforward DNN",
#                 "Multi Layered Feed Forward Neural Network",
#                 "Learning Factors",
#                 "Activation functions: Tanh, Logistic, Linear, Softmax, ReLU, Leaky ReLU",
#                 "Loss functions: Squared Error loss, Cross Entropy, Choosing output function and loss function",
#                 "Optimization",
#                 "Learning with backpropagation",
#                 "Learning Parameters: Gradient Descent (GD), Stochastic and Mini Batch GD, Momentum Based GD, Nesterov Accelerated GD, AdaGrad, Adam, RMSProp",
#                 "Regularization",
#                 "Overview of Overfitting",
#                 "Types of biases",
#                 "Bias Variance Tradeoff",
#                 "Regularization Methods: L1, L2 regularization, Parameter sharing, Dropout, Weight Decay, Batch normalization, Early stopping, Data Augmentation, Adding noise to input and output"
#             ]
#             },
#             {
#             "module_number": 3,
#             "module_name": "Autoencoders: Unsupervised Learning",
#             "weightage_hours": 6,
#             "topics": [
#                 "Introduction",
#                 "Linear Autoencoder",
#                 "Undercomplete Autoencoder",
#                 "Overcomplete Autoencoders",
#                 "Regularization in Autoencoders",
#                 "Denoising Autoencoders",
#                 "Sparse Autoencoders",
#                 "Contractive Autoencoders",
#                 "Application of Autoencoders: Image Compression"
#             ]
#             },
#             {
#             "module_number": 4,
#             "module_name": "Convolutional Neural Networks (CNN): Supervised Learning",
#             "weightage_hours": 7,
#             "topics": [
#                 "Convolution operation",
#                 "Padding",
#                 "Stride",
#                 "Relation between input, output and filter size",
#                 "CNN architecture: Convolution layer, Pooling Layer",
#                 "Weight Sharing in CNN",
#                 "Fully Connected NN vs CNN",
#                 "Variants of basic Convolution function",
#                 "Multichannel convolution operation",
#                 "2D convolution",
#                 "Modern Deep Learning Architectures: LeNET: Architecture, AlexNET: Architecture, ResNet : Architecture"
#             ]
#             },
#             {
#             "module_number": 5,
#             "module_name": "Recurrent Neural Networks (RNN)",
#             "weightage_hours": 8,
#             "topics": [
#                 "Sequence Learning Problem",
#                 "Unfolding Computational graphs",
#                 "Recurrent Neural Network",
#                 "Bidirectional RNN",
#                 "Backpropagation Through Time (BTT)",
#                 "Limitation of “vanilla RNN” Vanishing and Exploding Gradients",
#                 "Truncated BTT",
#                 "Long Short Term Memory(LSTM): Selective Read, Selective write, Selective Forget",
#                 "Gated Recurrent Unit (GRU)"
#             ]
#             },
#             {
#             "module_number": 6,
#             "module_name": "Recent Trends and Applications",
#             "weightage_hours": 4,
#             "topics": [
#                 "Generative Adversarial Network (GAN): Architecture",
#                 "Applications: Image Generation",
#                 "DeepFake"
#             ]
#             }
#         ]
#         }
        
#         # 1. Generate Tree
#         tree_output = generate_structured_tree(syllabus, llm)
#         print("\n=== GENERATED KNOWLEDGE STRUCTURE ===\n")
#         print(tree_output)

#         # 2. Generate Knowledge Graph (Requested)
#         #graph = generate_knowledge_graph(syllabus)
#         # print("\n=== GENERATED KNOWLEDGE GRAPH ===\n")
#         # print(graph)

#     except FileNotFoundError:
#         print("Error: 'ai_knowledge_base.json' not found in backend/services/data/")
#     except Exception as e:
#         print(f"An error occurred: {e}")

# if __name__ == "__main__":
#     main()