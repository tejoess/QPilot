
# This file contains the prompt templates used for various tasks in the application.


# Syllabus Extraction Prompt

format_syllabus = """You are a strict JSON generator. Extract syllabus data and return it in the EXACT schema format provided.

DO NOT use natural language field names like "course", "units", "topics".
DO NOT add extra fields like "total_units", "course_objectives".
ONLY output fields that match the schema exactly.

MANDATORY field name requirements:
- Root level: "course_code", "course_name", "modules" (NOT "course", NOT "units")
- Module level: "module_number", "module_name", "weightage", "topics"
- Topic level: "name", "subtopics"
- Subtopic level: "name", "description"

Weightage MUST be decimal (0.20 = 20%, NOT integer 20).

INPUT SYLLABUS:
{syllabus}

OUTPUT: Follow the schema definition below EXACTLY. Use ONLY the field names from the schema."""
