# app/services/pyq_service.py
# app/services/pyq_service.py

import json
import os
from typing import Dict, Any
from backend.services.llm_service import gemini_llm as llm
from langchain_core.messages import HumanMessage


def format_pyqs(pyq_text: str = "", syllabus_json: Dict[str, Any] = None) -> str:
    """
    Takes raw PYQ text + syllabus JSON and extracts questions in a single pass (no chunking).
    Topics/Subtopics are forced strictly from syllabus labels.
    """

    print("\n🛠️  [GRAPH NODE] Formatting PYQ JSON (Syllabus-Constrained Mode)...")

    if not pyq_text:
        return json.dumps({"error": "No PYQ text available."})

    if not syllabus_json:
        return json.dumps({"error": "Syllabus JSON not provided."})

    syllabus_text = json.dumps(syllabus_json, indent=2)

    prompt = f"""
You are an expert academic exam extraction system.

Your job:
Extract ONLY valid academic questions from PYQ text and label them using the provided syllabus.

STRICT RULES:

1. Question Text:
   - Extract FULL, COMPLETE question text.
   - Do NOT include question numbers or parenthesized parts like "(a)".
   - Fix broken words if present.

2. Filter Noise:
   - IGNORE instructions like "Attempt any", "Time allowed", "Max marks".
   - IGNORE headers, footers, page numbers, and section titles.
   - IGNORE statements that are not questions.
   - ONLY extract actual questions containing action verbs/interrogatives.

3. Topic & Subtopic Mapping:
   - Topics/Subtopics must be mapped strictly from the provided syllabus.
   - topics/subtopic which you will label should be strictly from syllabus as it is, no change.
   - Do NOT paraphrase, rename, infer, generalize, or create new labels.
   - If a match is unclear, choose the closest exact syllabus entry.

4. Marks:
   - Extract if explicitly present.
   - If not present, infer only from complexity: 2, 5, or 10.

5. Cleanliness:
   - Remove numbering artifacts.
   - Normalize spacing and broken words.

Return JSON in EXACT structure:

{{
    "questions": [
        {{
            "question": "Full question text here",
            "topic": "Exact Topic From Syllabus",
            "subtopic": "Exact Subtopic From Syllabus",
            "marks": 10
        }}
    ]
}}

SYLLABUS:
---
{syllabus_text}
---

PYQ TEXT:
---
{pyq_text}
---

Return ONLY valid JSON.
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        print(content)

        data = json.loads(content)

        if "questions" not in data:
            return json.dumps({"error": "Invalid JSON structure from LLM."})

        # Deduplicate questions
        seen = set()
        unique_questions = []

        for q in data["questions"]:
            q_text = str(q.get("question", "")).strip().lower()
            if q_text and q_text not in seen:
                seen.add(q_text)
                unique_questions.append(q)

        final_output = {
            "exam_info": {
                "note": "Generated using syllabus-constrained labeling."
            },
            "questions": unique_questions
        }

        print(f"✅  [PYQ FORMAT] Completed. Total Unique Questions: {len(unique_questions)}")
        return json.dumps(final_output, indent=4)

    except json.JSONDecodeError:
        return json.dumps({"error": "LLM returned invalid JSON."})

    except Exception as e:
        return json.dumps({"error": str(e)})


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

dummy_syllabus = """
| Course Code:   | Course Title   |   Credit |
|----------------|----------------|----------|
| CSC701         | Deep Learning  |        3 |

| Prerequisite: Basic mathematics and Statistical concepts, Linear algebra, Machine Learning   | Prerequisite: Basic mathematics and Statistical concepts, Linear algebra, Machine Learning                            |
|----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| Course Objectives:                                                                           | Course Objectives:                                                                                                    |
| 1                                                                                            | To learn the fundamentals of Neural Network.                                                                          |
| 2                                                                                            | To gain an in-depth understanding of training Deep Neural Networks.                                                   |
| 3                                                                                            | To acquire knowledge of advanced concepts of Convolution Neural Networks, Autoencoders and Recurrent Neural Networks. |
| 4                                                                                            | Students should be familiar with the recent trends in Deep Learning.                                                  |
| Course Outcomes:                                                                             | Course Outcomes:                                                                                                      |
| 1                                                                                            | Gain basic knowledge of Neural Networks.                                                                              |
| 2                                                                                            | Acquire in depth understanding of training Deep Neural Networks.                                                      |
| 3                                                                                            | Design appropriate DNN model for supervised, unsupervised and sequence learning applications.                         |
| 4                                                                                            | Gain familiarity with recent trends and applications of Deep Learning.                                                |

| Modul e   |     | Content                                                                                                                                                                                                                                                           | 39Hrs   |
|-----------|-----|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| 1         |     | Fundamentals of Neural Network                                                                                                                                                                                                                                    | 4       |
|           | 1.1 | History of Deep Learning, Deep Learning Success Stories, Multilayer Perceptrons (MLPs), Representation Power of MLPs, Sigmoid Neurons, Gradient Descent, Feedforward Neural Networks, Representation Power of Feedforward Neural Networks                         |         |
|           | 1.2 | Deep Networks: Three Classes of Deep Learning Basic Terminologies of Deep Learning                                                                                                                                                                                |         |
| 2         |     | Training, Optimization and Regularization of Deep Neural Network                                                                                                                                                                                                  | 10      |
|           | 2.1 | Training FeedforwardDNN Multi Layered Feed Forward Neural Network, Learning Factors, Activation functions: Tanh, Logistic, Linear, Softmax, ReLU, Leaky ReLU, Loss functions: Squared Error loss, Cross Entropy, Choosing output function and loss function       |         |
|           | 2.2 | Optimization Learning with backpropagation, Learning Parameters: Gradient Descent (GD), Stochastic and Mini Batch GD, Momentum Based GD, Nesterov Accelerated GD, AdaGrad, Adam, RMSProp                                                                          |         |
|           | 2.3 | Regularization Overview of Overfitting, Types of biases, Bias Variance Tradeoff Regularization Methods: L1, L2 regularization, Parameter sharing, Dropout, Weight Decay, Batch normalization, Early stopping, Data Augmentation, Adding noise to input and output |         |
| 3         |     | Autoencoders: Unsupervised Learning                                                                                                                                                                                                                               | 6       |
|           | 3.1 | Introduction, Linear Autoencoder, Undercomplete Autoencoder, Overcomplete Autoencoders, Regularization in Autoencoders                                                                                                                                            |         |

| 3.2   | Denoising Autoencoders, Sparse Autoencoders, Contractive Autoencoders                                                                                                                                                                                                                    |    |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----|
| 3.3   | Application of Autoencoders: Image Compression                                                                                                                                                                                                                                           |    |
|       | Convolutional Neural Networks (CNN): Supervised Learning                                                                                                                                                                                                                                 | 7  |
| 4.1   | Convolution operation, Padding, Stride, Relation between input, output and filter size, CNN architecture: Convolution layer, Pooling Layer, Weight Sharing in CNN, Fully Connected NN vs CNN, Variants of basic Convolution function, Multichannel convolution operation,2D convolution. |    |
| 4.2   | Modern Deep Learning Architectures: LeNET: Architecture, AlexNET: Architecture, ResNet : Architecture                                                                                                                                                                                    |    |
|       | Recurrent Neural Networks (RNN)                                                                                                                                                                                                                                                          | 8  |
| 5.1   | Sequence Learning Problem, Unfolding Computational graphs, Recurrent Neural Network, Bidirectional RNN, Backpropagation Through Time (BTT), Limitation of ' vanilla RNN' Vanishing and Exploding Gradients, Truncated BTT                                                                |    |
| 5.2   | Long Short Term Memory(LSTM): Selective Read, Selective write, Selective Forget, Gated Recurrent Unit (GRU)                                                                                                                                                                              |    |
|       | Recent Trends and Applications                                                                                                                                                                                                                                                           | 4  |
| 6.1   | Generative Adversarial Network (GAN): Architecture                                                                                                                                                                                                                                       |    |
| 6.2   | Applications: Image Generation, DeepFake                                                                                                                                                                                                                                                 |    |

| Textbooks:   | Textbooks:                                                                                        |
|--------------|---------------------------------------------------------------------------------------------------|
| 1            | Ian Goodfellow, Yoshua Bengio, Aaron Courville. -Deep Learningǁ, MIT Press Ltd, 2016              |
| 2            | Li Deng and Dong Yu, -Deep Learning Methods and Applicationsǁ, Publishers Inc.                    |
| 3            | Satish Kumar "Neural Networks AClassroom Approach" Tata McGraw-Hill.                              |
| 4            | JM Zurada -Introduction to Artificial Neural Systemsǁ, Jaico Publishing House                     |
| 5            | M. J. Kochenderfer, Tim A. Wheeler. -Algorithms for Optimizationǁ, MIT Press.                     |
| References:  | References:                                                                                       |
| 1            | Deep Learning from Scratch: Building with Python from First Principles- Seth Weidman by O`Reilley |
| 2            | François Chollet. -Deep learning with Python -(Vol. 361). 2018 New York: Manning.                 |
| 3            | Douwe Osinga. -Deep Learning Cookbookǁ, O'REILLY, SPDPublishers, Delhi.                           |
| 4            | Simon Haykin, Neural Network-A Comprehensive Foundation- Prentice Hall International, Inc         |
| 5            | S.N.Sivanandam and S.N.Deepa, Principles of soft computing-Wiley India                            |

## Assessment:

## Internal Assessment:

The assessment consists of two class tests of 20 marks each. The first class test is to be conducted when approx. 40% syllabus is completed and second class test when additional 40% syllabus is completed. Duration of each test shall be one hour.

## End Semester Theory Examination:

- 1 Question paper will comprise a total of six questions.
- 2 All questions carry equal marks.
- 3 Question 1 and question 6 will have questions from all modules. Remaining 4 questions will be based on the remaining 4 modules.

"""
# pyqs = format_pyqs(pyq_text, dummy_syllabus)
# print(pyqs)