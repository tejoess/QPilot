# QPilot API Testing Guide - Postman

The backend has been split into **3 separate APIs** that work sequentially:

1. **`POST /analyze-syllabus`** - Upload/paste syllabus → Get parsed syllabus data
2. **`POST /analyze-pyqs`** - Upload/paste PYQs → Get parsed questions
3. **`POST /generate-paper`** - Generate question paper from analyzed data

---

## 🚀 Quick Start

### Prerequisites
1. **Start Backend Server:**
   ```bash
   cd C:\Users\Tejas\Desktop\QPilot
   uvicorn backend.main:backend --reload
   ```
   Server runs at: `http://127.0.0.1:8000`

2. **Open Postman** (or any API client)

---

## 📌 API 1: Analyze Syllabus

### Method: `POST`
### URL: `http://127.0.0.1:8000/analyze-syllabus`

### Option A: Upload PDF File

**Body Type:** `form-data`

| Key | Type | Value |
|-----|------|-------|
| `file` | File | Select your syllabus PDF file |

**Example:**
```
Key: file
Type: File
Value: Browse and select C:\path\to\syllabus.pdf
```

### Option B: Paste Text

**Body Type:** `form-data`

| Key | Type | Value |
|-----|------|-------|
| `text` | Text | Paste your syllabus content here |

**Example Text Content:**
```
Key: text
Type: Text
Value: 
Course Code: CS701
Course Name: Deep Learning
Total Credits: 4

Module 1: Introduction to Neural Networks (20%)
- Perceptron and Multi-Layer Perceptron
- Activation Functions (Sigmoid, ReLU, Tanh)
- Backpropagation Algorithm
- Gradient Descent Optimization

Module 2: Convolutional Neural Networks (25%)
- Convolution Operation and Pooling
- CNN Architectures (LeNet, AlexNet, VGG)
- Transfer Learning
- Image Classification Applications

Module 3: Recurrent Neural Networks (25%)
- RNN Architecture and Vanishing Gradients
- LSTM and GRU Networks
- Sequence Modeling
- Text Processing Applications

Module 4: Advanced Topics (30%)
- Generative Adversarial Networks
- Autoencoders and Variational Autoencoders
- Attention Mechanisms and Transformers
- Model Optimization and Deployment
```

### Full Response Example:
```json
{
  "status": "success",
  "session_id": "7f8e9d0c-1b2a-3c4d-5e6f-7a8b9c0d1e2f",
  "syllabus": {
    "course_code": "CS701",
    "course_name": "Deep Learning",
    "modules": [
      {
        "module_number": "Module 1",
        "module_name": "Introduction to Neural Networks",
        "weightage": 0.20,
        "topics": [
          {
            "topic_name": "Perceptron and Multi-Layer Perceptron",
            "subtopics": ["Perceptron basics", "MLP architecture"],
            "bloom_level": "understand"
          },
          {
            "topic_name": "Activation Functions",
            "subtopics": ["Sigmoid", "ReLU", "Tanh"],
            "bloom_level": "understand"
          },
          {
            "topic_name": "Backpropagation Algorithm",
            "subtopics": ["Forward pass", "Backward pass", "Weight updates"],
            "bloom_level": "apply"
          },
          {
            "topic_name": "Gradient Descent Optimization",
            "subtopics": ["SGD", "Mini-batch", "Learning rate"],
            "bloom_level": "apply"
          }
        ]
      },
      {
        "module_number": "Module 2",
        "module_name": "Convolutional Neural Networks",
        "weightage": 0.25,
        "topics": [
          {
            "topic_name": "Convolution Operation and Pooling",
            "subtopics": ["Convolution filters", "Max pooling", "Average pooling"],
            "bloom_level": "understand"
          },
          {
            "topic_name": "CNN Architectures",
            "subtopics": ["LeNet", "AlexNet", "VGG"],
            "bloom_level": "remember"
          },
          {
            "topic_name": "Transfer Learning",
            "subtopics": ["Pre-trained models", "Fine-tuning"],
            "bloom_level": "apply"
          },
          {
            "topic_name": "Image Classification Applications",
            "subtopics": ["Object detection", "Image segmentation"],
            "bloom_level": "analyze"
          }
        ]
      },
      {
        "module_number": "Module 3",
        "module_name": "Recurrent Neural Networks",
        "weightage": 0.25,
        "topics": [
          {
            "topic_name": "RNN Architecture and Vanishing Gradients",
            "subtopics": ["RNN structure", "Vanishing gradient problem"],
            "bloom_level": "understand"
          },
          {
            "topic_name": "LSTM and GRU Networks",
            "subtopics": ["LSTM cells", "GRU cells", "Forget gates"],
            "bloom_level": "apply"
          },
          {
            "topic_name": "Sequence Modeling",
            "subtopics": ["Time series prediction", "Sequence generation"],
            "bloom_level": "apply"
          },
          {
            "topic_name": "Text Processing Applications",
            "subtopics": ["Sentiment analysis", "Machine translation"],
            "bloom_level": "analyze"
          }
        ]
      },
      {
        "module_number": "Module 4",
        "module_name": "Advanced Topics",
        "weightage": 0.30,
        "topics": [
          {
            "topic_name": "Generative Adversarial Networks",
            "subtopics": ["GAN architecture", "Generator", "Discriminator"],
            "bloom_level": "apply"
          },
          {
            "topic_name": "Autoencoders and Variational Autoencoders",
            "subtopics": ["Encoder-decoder", "Latent space", "VAE"],
            "bloom_level": "apply"
          },
          {
            "topic_name": "Attention Mechanisms and Transformers",
            "subtopics": ["Self-attention", "Multi-head attention", "BERT", "GPT"],
            "bloom_level": "understand"
          },
          {
            "topic_name": "Model Optimization and Deployment",
            "subtopics": ["Model compression", "Quantization", "Edge deployment"],
            "bloom_level": "analyze"
          }
        ]
      }
    ]
  },
  "message": "Syllabus analyzed successfully"
}
```

**⚠️ IMPORTANT: Save the `session_id` from the response!** You'll need it for the next API.

---

## 📌 API 2: Analyze PYQs

### Method: `POST`
### URL: `http://127.0.0.1:8000/analyze-pyqs`

### Required Fields:

**Body Type:** `form-data`

| Key | Type | Value | Required |
|-----|------|-------|----------|
| `syllabus_session_id` | Text | Session ID from API 1 | ✅ Yes |
| `file` | File | PYQ PDF file | One of file/text |
| `text` | Text | Paste PYQ content | One of file/text |

### Option A: Upload PYQ PDF

```
Key: syllabus_session_id
Type: Text
Value: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Key: file
Type: File
Value: Browse and select C:\path\to\pyqs.pdf
```

### Option B: Paste PYQ Text

```
Key: syllabus_session_id
Type: Text
Value: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Key: text
Type: Text
Value: 
Q1. Explain the concept of backpropagation.
Q2. What are activation functions?
...
```

### Response:
```json
{
  "status": "success",
  "session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "pyqs": {
    "exam_info": {...},
    "questions": [
      {
        "id": "pyq_001",
        "question": "Explain backpropagation",
        "topic": "Training Neural Networks",
        "subtopic": "Backpropagation",
        "marks": 5
      }
    ]
  },
  "total_questions": 8,
  "message": "PYQs analyzed successfully"
}
```

**⚠️ IMPORTANT: Save this `session_id` too!** You'll need both session IDs for paper generation.

---

## 📌 API 3: Generate Paper

### Method: `POST`
### URL: `http://127.0.0.1:8000/generate-paper`

### Required Fields:

**Body Type:** `form-data`

| Key | Type | Value | Default | Required |
|-----|------|-------|---------|----------|
| `syllabus_session_id` | Text | Session ID from API 1 | - | ✅ Yes |
| `pyqs_session_id` | Text | Session ID from API 2 | - | ✅ Yes |
| `total_marks` | Text | Total marks for paper | 80 | No |
| `total_questions` | Text | Number of questions | 10 | No |
| `bloom_remember` | Text | Remember % (0-100) | 20 | No |
| `bloom_understand` | Text | Understand % (0-100) | 30 | No |
| `bloom_apply` | Text | Apply % (0-100) | 30 | No |
| `bloom_analyze` | Text | Analyze % (0-100) | 20 | No |
| `bloom_evaluate` | Text | Evaluate % (0-100) | 0 | No |
| `bloom_create` | Text | Create % (0-100) | 0 | No |
| `paper_pattern` | Text | JSON string of sections | Auto-generated | No |
| `teacher_input` | Text | Custom instructions | "Standard difficulty" | No |

**⚠️ Note:** Bloom taxonomy levels must sum to 100 if provided.

### Example Request 1: Basic (Minimal Fields)

```
Key: syllabus_session_id
Type: Text
Value: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Key: pyqs_session_id
Type: Text
Value: b2c3d4e5-f6a7-8901-bcde-f12345678901

Key: total_marks
Type: Text
Value: 80

Key: total_questions
Type: Text
Value: 10
```

### Example Request 2: With Bloom Taxonomy

```
Key: syllabus_session_id
Type: Text
Value: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Key: pyqs_session_id
Type: Text
Value: b2c3d4e5-f6a7-8901-bcde-f12345678901

Key: total_marks
Type: Text
Value: 80

Key: total_questions
Type: Text
Value: 10

Key: bloom_remember
Type: Text
Value: 15

Key: bloom_understand
Type: Text
Value: 25

Key: bloom_apply
Type: Text
Value: 35

Key: bloom_analyze
Type: Text
Value: 20

Key: bloom_evaluate
Type: Text
Value: 5

Key: bloom_create
Type: Text
Value: 0

Key: teacher_input
Type: Text
Value: Focus on practical applications and real-world examples. Include questions on recent developments in deep learning.
```

### Example Request 3: With Custom Paper Pattern

```
Key: syllabus_session_id
Type: Text
Value: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Key: pyqs_session_id
Type: Text
Value: b2c3d4e5-f6a7-8901-bcde-f12345678901

Key: total_marks
Type: Text
Value: 100

Key: total_questions
Type: Text
Value: 15

Key: paper_pattern
Type: Text
Value: {
  "sections": [
    {
      "section_name": "Section A",
      "section_description": "Multiple Choice Questions",
      "question_count": 5,
      "marks_per_question": 2
    },
    {
      "section_name": "Section B",
      "section_description": "Short Answer Questions",
      "question_count": 5,
      "marks_per_question": 6
    },
    {
      "section_name": "Section C",
      "section_description": "Long Answer Questions",
      "question_count": 5,
      "marks_per_question": 12
    }
  ]
}

Key: bloom_remember
Type: Text
Value: 20

Key: bloom_understand
Type: Text
Value: 25

Key: bloom_apply
Type: Text
Value: 30

Key: bloom_analyze
Type: Text
Value: 15

Key: bloom_evaluate
Type: Text
Value: 10

Key: bloom_create
Type: Text
Value: 0

Key: teacher_input
Type: Text
Value: Emphasize conceptual understanding over rote memorization. Include diagrams where appropriate.
```

### Response:
```json
{
  "status": "success",
  "session_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "paper": {
    "blueprint_metadata": {...},
    "sections": [
      {
        "section_name": "Section A",
        "questions": [...]
      },
      {
        "section_name": "Section B",
        "questions": [...]
      }
    ]
  },
  "verification": {
    "rating": 8.5,
    "verdict": "ACCEPTED"
  },
  "pdf_path": "backend/services/data/c3d4e5f6.../final_question_paper.pdf",
  "message": "Question paper generated successfully"
}
```

---

## 📂 Data Storage

All intermediate files are stored in:
```
backend/services/data/{session_id}/
```

**Syllabus Session** contains:
- `syllabus_raw.txt` - Original text
- `syllabus.json` - Parsed structure

**PYQ Session** contains:
- `pyqs_raw.txt` - Original text
- `pyqs.json` - Parsed questions

**Paper Session** contains:
- `blueprint.json`
- `blueprint_verification.json`
- `draft_paper.json`
- `paper_verification.json`
- `final_paper.json`
- `final_question_paper.pdf` (TODO)
- `session_summary.json`

---

## 🎯 Complete Testing Workflow

### Step 1: Analyze Syllabus
1. Open Postman
2. Create `POST` request to `http://127.0.0.1:8000/analyze-syllabus`
3. Select `Body` → `form-data`
4. Add field `file` (type: File) → browse and select syllabus PDF
5. Click **Send**
6. **Copy the `session_id`** from response

### Step 2: Analyze PYQs
1. Create new `POST` request to `http://127.0.0.1:8000/analyze-pyqs`
2. Select `Body` → `form-data`
3. Add fields:
   - `syllabus_session_id` (type: Text) → paste session ID from Step 1
   - `file` (type: File) → browse and select PYQ PDF
4. Click **Send**
5. **Copy the `session_id`** from response

### Step 3: Generate Paper
1. Create new `POST` request to `http://127.0.0.1:8000/generate-paper`
2. Select `Body` → `form-data`
3. Add fields:
   - `syllabus_session_id` → paste from Step 1
   - `pyqs_session_id` → paste from Step 2
   - `total_marks` → 80
   - `total_questions` → 10
4. Click **Send**
5. Check response for generated paper

---

## ⚠️ Error Handling

### Common Errors:

**400 Bad Request:**
```json
{
  "detail": "Either 'file' or 'text' must be provided"
}
```
**Solution:** Provide either file upload OR text content, not both or none.

**404 Not Found:**
```json
{
  "detail": "Syllabus session {id} not found"
}
```
**Solution:** Verify the session_id exists. Check `backend/services/data/` folder.

**500 Internal Server Error:**
```json
{
  "detail": "Syllabus analysis failed: <error details>"
}
```
**Solution:** Check backend terminal logs for detailed error messages.

---

## 📝 Tips

1. **Use Collections:** Create a Postman Collection with all 3 APIs for easy testing
2. **Environment Variables:** Store session IDs as Postman environment variables
3. **Save Responses:** Use Postman's "Save Response" feature to inspect full JSON
4. **Check Logs:** Monitor backend terminal for detailed processing logs
5. **Session Files:** Inspect generated JSON files in `backend/services/data/{session_id}/`

---

## 🔗 WebSocket Support

For real-time progress updates, connect to:
```
ws://127.0.0.1:8000/ws/{session_id}
```

Use a WebSocket client or browser console:
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/YOUR_SESSION_ID');
ws.onmessage = (event) => console.log(event.data);
```

---

## 🚦 Testing Without Files

If you don't have PDFs, use the text option:

**Syllabus Text Example:**
```
Course: Deep Learning
Module 1: Neural Networks (20%)
- Topic: Backpropagation
- Topic: Activation Functions
Module 2: CNN (25%)
- Topic: Convolution Operation
```

**PYQ Text Example:**
```
1. Explain backpropagation algorithm. [10 marks]
2. What are activation functions? List 4 types. [5 marks]
3. Describe CNN architecture. [10 marks]
```

---

## ✅ Success Checklist

- [ ] Backend server is running
- [ ] Can successfully call `/analyze-syllabus`
- [ ] Received `session_id` in response
- [ ] Can successfully call `/analyze-pyqs` with previous session ID
- [ ] Received second `session_id`
- [ ] Can successfully call `/generate-paper` with both session IDs
- [ ] Generated paper JSON is returned
- [ ] Files are saved in `backend/services/data/` folders

---

**Need Help?** Check backend terminal logs for detailed error messages and processing status!
