import json
from QP_Verifier.question_paper_verifier import evaluate_question_paper

dummy_data = {
    "syllabus": "Unit 1, Unit 2, Unit 3, Unit 4, Unit 5",
    "teacher_input": "Focus on application based questions.",
    "blooms_target_distribution": {
        "Remember": 20,
        "Understand": 30,
        "Apply": 30,
        "Analyze": 10,
        "Evaluate": 10,
        "Create": 0
    },
    "question_paper": [
        {
            "id": "1",
            "question_number": "1",
            "text": "Explain Newton's first law.",
            "marks": 5,
            "blooms_level": "Understand",
            "topic": "Unit 1"
        },
        {
            "id": "2",
            "question_number": "2",
            "text": "Calculate the force.",
            "marks": 10,
            "blooms_level": "Apply",
            "topic": "Unit 2"
        }
    ]
}

print("Running evaluate_question_paper...")
result = evaluate_question_paper(dummy_data)
print(json.dumps(result, indent=2))
