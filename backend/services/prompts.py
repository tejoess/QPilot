
# This file contains the prompt templates used for various tasks in the application.


# Syllabus Extraction Prompt

format_syllabus = """
You are an expert syllabus analyzer. Extract the syllabus structure from the following text and return a single, structured JSON object.

Here is the required JSON format:
{{
    "course": "Course Name",
    "total_units": <Total number of units>,
    "units": [
        {{
            "unit_number": <Unit Number (e.g., 1)>,
            "unit_name": "Unit Name",
            "weightage": <Weightage (as a number, e.g., 20)>,
            "topics": [
                {{
                    "topic": "Topic Name",
                    "subtopics": ["Subtopic 1", "Subtopic 2"],
                    "bloom_level": "e.g., Remember, Understand, Apply",
                    
                }}
            ]
        }}
    ],
    "course_outcomes": ["Course Outcome 1", "Course Outcome 2"],
    "course_objectives": ["Course Objective 1", "Course Objective 2"]
}}

Syllabus Text:
---
{dummy_syllabus}
---

Return ONLY the single, complete JSON object. Do not add any other text or markdown formatting.
"""
