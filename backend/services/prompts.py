
# This file contains the prompt templates used for various tasks in the application.


# Syllabus Extraction Prompt

format_syllabus = """You are a strict JSON extractor. Extract syllabus information from the given text and return ONLY valid JSON matching the schema exactly.

EXTRACTION RULES:
- Extract exactly what is present in the syllabus. Do NOT infer or fabricate missing data.
- If a field is not found in the syllabus, set it to null.
- Weightage = number of hours if hours are mentioned (as integer), otherwise null.
- Topics should be a flat list of topic/subtopic names found under each module.
- Course objectives and outcomes are numbered lists — extract each as a plain string in an array.

MANDATORY FIELD NAMES (do not rename these):
- Root: "course_code", "course_name", "course_objectives", "course_outcomes", "modules"
- Module: "module_number", "module_name", "weightage_hours", "topics"
- Topic: plain string (just the topic name, not a nested object)

EXAMPLE OUTPUT STRUCTURE:
{{
  "course_code": "CSC701",
  "course_name": "Deep Learning",
  "course_objectives": [
    "To learn the fundamentals of Neural Networks.",
    "To gain understanding of training Deep Neural Networks."
  ],
  "course_outcomes": [
    "Gain basic knowledge of Neural Networks.",
    "Acquire in depth understanding of training Deep Neural Networks."
  ],
  "modules": [
    {{
      "module_number": 1,
      "module_name": "Fundamentals of Neural Network",
      "weightage_hours": 4,
      "topics": [
        "History of Deep Learning",
        "Multilayer Perceptrons (MLPs)",
        "Sigmoid Neurons",
        "Gradient Descent",
        "Feedforward Neural Networks"
      ]
    }}
  ]
}}

INPUT SYLLABUS:
{syllabus}

OUTPUT: Return ONLY the JSON object. No markdown, no explanation, no extra fields."""