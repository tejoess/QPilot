# app/services/pyq_service.py
import json
import re
import os
from typing import List, Dict, Any
from backend.services.llm_service import gemini_llm as llm
from langchain_core.messages import HumanMessage


def format_pyqs(pyq_text: str = "") -> str:
    """
    Takes raw PYQ text, splits it into chunks, and extracts questions with high fidelity.
    Focuses on Question Text, Topic, Subtopic, and Marks.
    """
    print(f"\n🛠️  [GRAPH NODE] Formatting PYQ JSON (High Quality Mode)...")
    
    if not pyq_text:
        return json.dumps({"error": "No text available."})

    # Chunk size config
    chunk_size = 6000  
    overlap = 1000  # Increased overlap to capture context for topics
    
    all_questions = []
    
    # Split text into chunks
    chunks = []
    if len(pyq_text) <= chunk_size:
        chunks = [pyq_text]
    else:
        for i in range(0, len(pyq_text), chunk_size - overlap):
            chunks.append(pyq_text[i:i+chunk_size])
            
    print(f"   📊 Processing {len(chunks)} chunks for {len(pyq_text)} chars...")
    
    for i, chunk in enumerate(chunks):
        print(f"   🔄 Processing Chunk {i+1}/{len(chunks)}...")
        
        prompt = f"""
        You are an expert exam extraction system. Extract valid academic questions from the text below.
        
        STRICT RULES:
        1. **Question Text**: Extract the FULL, COMPLETE question text. Do NOT include the question number or any parenthesized parts like "(a)" in the text.
        2. **Filter Noise**: 
           - IGNORE exam instructions like "Attempt any", "compulsory", "Time allow", "Max marks".
           - IGNORE headers, footers, page numbers, or section titles.
           - IGNORE statements that are not questions (e.g., "The input to the layer has 32 channels...").
           - **ONLY extract items that are actual questions** starting with or containing action verbs/interrogatives (e.g., Explain, Define, Calculate, Discuss, Design, Differentiate, What, Why, How).
        3. **Topic/Subtopic**: Infer the technical Topic and Subtopic. Use specific technical terms (e.g., "CNN Architecture", "Gradient Descent", "GANs").
        4. **Marks**: Extract marks if explicitly present (e.g. "[10]", "10"). 
            if marks are not explicitly mentioned, mark it 2,5 or 10 based on the complexity of the question.
        5. **Cleanliness**: Fix broken words (e.g. "Net- work" -> "Network").
        
        Ignored Fields: Do NOT extract Question Numbers.
        
        Return a JSON object with this EXACT structure:
        {{
            "questions": [
                {{
                    "question": "Full question text here",
                    "topic": "Specific Technical Topic",
                    "subtopic": "Specific Sub-concept",
                    "marks": 10
                }}
            ]
        }}
        
        Text Chunk:
        ---
        {chunk}
        ---
        
        Return ONLY valid JSON.
        """
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            print(content)
            
            # json_match = re.search(r'\{[\s\S]*\}', content)
            
            # if json_match:
            #     try:
            #         data = json.loads(json_match.group(0))
                    
            #         if "questions" in data and isinstance(data["questions"], list):
            #             # Filter out empty or garbage questions
            #             valid_qs = [
            #                 q for q in data["questions"] 
            #                 if q.get("question") and len(str(q["question"])) > 5
            #             ]
            #             all_questions.extend(valid_qs)
            #             print(f"      ✅ Chunk {i+1}: Extracted {len(valid_qs)} questions.")
            #     except json.JSONDecodeError:
            #         print(f"      ❌ Chunk {i+1}: JSON Decode Error.")
            # else:
            #     print(f"      ❌ Chunk {i+1}: No JSON found.")
                    
        except Exception as e:
            print(f"      ❌ Warning in chunk {i+1}: {e}")

    # Remove duplicates based on question text
    seen_questions = set()
    unique_questions = []
    
    for q in all_questions:
        # Normalize text for deduplication comparison (lower case, stripped)
        q_text_norm = str(q.get("question", "")).strip().lower()
        if q_text_norm and q_text_norm not in seen_questions:
            seen_questions.add(q_text_norm)
            unique_questions.append(q)
    
    # Final Output
    final_output = {
        "exam_info": {
            "note": "Aggregated from extracted chunks."
        },
        "questions": unique_questions
    }
    
    print(f"✅  [PYQ FORMAT] Completed. Total Unique Questions: {len(unique_questions)}")
    return json.dumps(final_output, indent=4)


pyq_text ="""
Based on the provided documents, here is the extracted text from the previous year's question papers for the **Deep Learning (42371)** course.

---

## **Deep Learning - Examination Paper 1 (Dec 2023)**

**Duration:** 3 Hours | **Max Marks:** 80 

**Instructions:**

* Question No. 1 is compulsory.


* Attempt any three questions out of the remaining five.


* Assume suitable data, if required and state it clearly.



### **Questions**

* Q1. Attempt any four: 


* a. Design AND gate using Perceptron.


* b. Suppose we have  input-output pairs. Our goal is to find parameters that predict the output  from the input  according to . Calculate the sum-of-squared error function . Derive the gradient descent update rule .


* c. Explain dropout. How does it solve the problem of overfitting? 


* d. Explain denoising autoencoder model.


* e. Describe sequence learning problem.




* **Q2.**
* a. Explain Gated Recurrent Unit (GRU) in detail.


* b. What is an activation function? Describe any four activation functions.




* **Q3.**
* a. Explain CNN architecture in detail. Calculate parameters for a layer with input , ten  filters, stride 1, and pad 2.


* b. Explain early stopping, batch normalization, and data augmentation.




* **Q4.**
* a. Explain RNN architecture in detail.


* b. Explain the working of Generative Adversarial Network (GAN).




* **Q5.**
* a. Explain Stochastic Gradient Descent and momentum-based gradient descent optimization techniques.


* b. Explain LSTM architecture.




* **Q6.**
* a. Describe LeNet architecture.


* b. Explain vanishing and exploding gradient in RNNs.





---

## **Deep Learning - Examination Paper 2 (Nov 2024)**

**Duration:** 3 Hours | **Max Marks:** 80 

### **Questions**

* Q1. Attempt any four: 


* a. Comment on the Representation Power of MLPs.
* b. Explain Gradient Descent in Deep Learning.
* c. Explain the dropout method and its advantages.
* d. What are Denoising Autoencoders?
* e. Explain Pooling operation in CNN.


* **Q2.**
* a. What are the Three Classes of Deep Learning? Explain each.
* b. Explain and analyze the architectural components of AlexNet CNN.


* **Q3.**
* a. What are the different types of Gradient Descent methods? Explain any three.
* b. Differentiate between the architecture of LSTM and GRU networks.


* **Q4.**
* a. Explain the key components of an RNN.
* b. Calculate the total number of parameters in a CNN layer: Input 32 channels (), 64 filters (), stride 1, no padding.


* **Q5.**
* a. Comment on the significance of Loss functions and explain different types.
* b. Explain any three types of Autoencoders.


* **Q6.**
* a. What is the significance of Activation Functions? Explain types used in NN.
* b. Explain GAN architecture and its applications.



---

## **Deep Learning - Examination Paper 3 (June 2025)**

**Duration:** 3 Hours | **Max Marks:** 80 

### **Questions**

* Q1. Attempt any four: 


* a. Explain basic architecture of feedforward neural network.


* b. Explain regularization in neural network.


* c. Explain types of neural network.


* d. Explain the concept of overfitting and under fitting.


* e. Explain basic working of CNN.




* **Q2.**
* a. Explain the gradient descent algorithm and discuss types in detail.


* b. Explain the working and types of autoencoders in detail.




* **Q3.**
* a. Draw and explain any two modern deep learning architectures.


* b. Differentiate between the LSTM and GRU network.




* **Q4.**
* a. Explain working of RNN with a diagram and how they suit sequential data.


* b. Compare standard RNN with LSTM for long-term dependencies; provide a real-world application.




* **Q5.**
* a. Discuss the role of Loss functions. Compare MSE and Cross-Entropy Loss.


* b. Explain architecture of GAN in detail and its applications.




* **Q6.**
* a. Explain the significance and types of Activation Functions.


* b. Explain the learning process (forward/backpropagation, optimization) in NN.





Would you like me to solve any of the specific numerical problems or architectural explanations from these papers?
"""


# pyqs = format_pyqs(pyq_text)
# print(pyqs)