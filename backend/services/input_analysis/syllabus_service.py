# app/services/syllabus_service.py
# app/services/nodes/syllabus_node.py

import os
import json
import re
from backend.services.prompts import format_syllabus as SYLLABUS_PROMPT
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from backend.services.schemas.llm_schemas import SyllabusOutput


def fix_syllabus_schema(data: dict) -> dict:
    """
    Transform LLM output that uses wrong field names to match our Pydantic schema.
    Common LLM mistakes: 'units' → 'modules', 'course' → 'course_name'
    """
    fixed = {}
    
    # Handle course field variations
    if "course_code" in data:
        fixed["course_code"] = data["course_code"]
    elif "code" in data:
        fixed["course_code"] = data["code"]
    else:
        fixed["course_code"] = ""
    
    if "course_name" in data:
        fixed["course_name"] = data["course_name"]
    elif "course" in data:
        fixed["course_name"] = data["course"]
    elif "name" in data:
        fixed["course_name"] = data["name"]
    else:
        fixed["course_name"] = ""
    
    # Handle modules/units variations
    if "modules" in data:
        fixed["modules"] = data["modules"]
    elif "units" in data:
        fixed["modules"] = data["units"]
    else:
        fixed["modules"] = []
    
    return fixed


def get_syllabus_json(system_instruction: str, syllabus: str):

    print("⏳ Sending request to LLM via LangChain with Pydantic Output Parser...")

    # Create output parser
    parser = PydanticOutputParser(pydantic_object=SyllabusOutput)
    format_instructions = parser.get_format_instructions()

    try:
        # Add format instructions to prompt
        formatted_prompt = system_instruction.format(syllabus=syllabus)
        formatted_prompt += f"\n\nSCHEMA DEFINITION:\n{format_instructions}\n\n"
        formatted_prompt += "CRITICAL RULES:\n"
        formatted_prompt += "1. Use ONLY field names from the schema above\n"
        formatted_prompt += "2. DO NOT use 'units', 'course', or 'total_units'\n"
        formatted_prompt += "3. MUST use 'modules', 'course_code', 'course_name'\n"
        formatted_prompt += "4. Return ONLY valid JSON matching the schema\n"
        formatted_prompt += "5. NO markdown, NO explanations, NO extra fields"
        
        response = llm.invoke([
            HumanMessage(content=formatted_prompt)
        ])

        raw_response = response.content

        print("\n--- Raw LLM Response (first 500 chars) ---")
        print(raw_response[:500])
        print("------------------------------------------\n")

        # Try parsing with Pydantic parser first
        try:
            parsed_obj = parser.parse(raw_response)
            parsed_data = parsed_obj.dict()
            print("✅ Successfully parsed with Pydantic OutputParser")
            return parsed_data
        except Exception as parse_error:
            print(f"⚠️ Pydantic parse failed: {parse_error}")
            print("Falling back to regex extraction and schema fixing...")
            
            # Fallback: regex extraction + schema transformation
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                json_str = json_match.group(0)
                parsed_data = json.loads(json_str)
                
                # Fix common LLM schema mistakes
                fixed_data = fix_syllabus_schema(parsed_data)
                print(f"✅ Parsed with regex fallback and fixed schema")
                print(f"   Detected {len(fixed_data.get('modules', []))} modules")
                return fixed_data
            else:
                print("❌ No JSON object found in response.")
                return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

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

# # Test call - uncomment to test directly
#result = get_syllabus_json(SYLLABUS_PROMPT, dummy_syllabus)
#print("Syllabus JSON result:", result)  