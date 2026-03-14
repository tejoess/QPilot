import requests
import json

url = "http://127.0.0.1:8000/verify-paper"

# Define the 4 JSON structures as dictionaries
question_paper = {
    "questions": [
        {
            "id": "1",
            "question_number": "1",
            "text": "Explain Newton's first law in detail.",
            "marks": 5,
            "blooms_level": "Understand",
            "topic": "Unit 1"
        },
        {
            "id": "2",
            "question_number": "2",
            "text": "Calculate the force of a 10kg object moving at 5m/s^2.",
            "marks": 10,
            "blooms_level": "Apply",
            "topic": "Unit 2"
        }
    ]
}

syllabus = "Unit 1, Unit 2, Unit 3, Unit 4, Unit 5"

teacher_instructions = "Focus on application based questions."

bloom_level = {
    "Remember": 20,
    "Understand": 30,
    "Apply": 30,
    "Analyze": 10,
    "Evaluate": 10,
    "Create": 0
}

# The files dictionary creates the multipart/form-data payload
# To pass text/JSON, we give it a tuple (filename, content, content-type)
files = {
    "question_paper": ("qp.json", json.dumps(question_paper["questions"]), "application/json"),
    "syllabus": ("syllabus.json", json.dumps(syllabus), "application/json"),
    "teacher_instructions": ("teacher.json", json.dumps(teacher_instructions), "application/json"),
    "bloom_level": ("bloom.json", json.dumps(bloom_level), "application/json")
}

print("Sending POST request to", url, "...")
try:
    response = requests.post(url, files=files)
    if response.status_code == 200:
        print("\nSuccess! Paper Verified.")
        print("Response JSON:\n")
        print(json.dumps(response.json(), indent=2))
    else:
        print("\nFailed with status code:", response.status_code)
        print("Error details:", response.text)
except requests.exceptions.ConnectionError:
    print("\nConnection error. Is the Uvicorn server running?")
