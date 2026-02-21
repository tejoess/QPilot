# Frontend Integration Guide: QPilot (FastAPI + Next.js)

## 1. Backend Overview

Your FastAPI backend exposes:
- **Base URL**: `http://localhost:8000` (development)
- **API Endpoint**: `POST /generate-paper`
- **WebSocket Endpoint**: `ws://localhost:8000/ws/{session_id}`

---

## 2. API Specifications

### POST /generate-paper
Generates a question paper based on user inputs.

**Request Body:**
```json
{
  "subject": "Mathematics",
  "grade": "10",
  "board": "CBSE"
}
```

**Response:**
```json
{
  "status": "success",
  "file_path": "/path/to/generated/paper.pdf"
}
```

**Headers Required:**
- `Content-Type: application/json`

---

### WebSocket /ws/{session_id}
Real-time logs for paper generation progress.

**Connection URL:** `ws://localhost:8000/ws/session_1`

---

## 3. Next.js Setup Requirements

### Environment Variables (`.env.local`)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000
```

### Install Dependencies
```bash
npm install axios
# or
npm install @tanstack/react-query  # recommended for better API management
```

---

## 4. Implementation Examples

### Option A: Simple Fetch API

```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export interface GeneratePaperRequest {
  subject: string;
  grade: string;
  board: string;
}

export interface GeneratePaperResponse {
  status: string;
  file_path: string;
}

export async function generatePaper(
  data: GeneratePaperRequest
): Promise<GeneratePaperResponse> {
  const response = await fetch(`${API_BASE_URL}/generate-paper`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Failed to generate paper');
  }

  return response.json();
}
```

### Option B: Axios with Better Error Handling

```typescript
// lib/apiClient.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add interceptors for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export default apiClient;
```

```typescript
// services/paperService.ts
import apiClient from '@/lib/apiClient';

export interface GeneratePaperRequest {
  subject: string;
  grade: string;
  board: string;
}

export interface GeneratePaperResponse {
  status: string;
  file_path: string;
}

export const paperService = {
  async generatePaper(data: GeneratePaperRequest): Promise<GeneratePaperResponse> {
    const response = await apiClient.post('/generate-paper', data);
    return response.data;
  },
};
```

---

## 5. WebSocket Integration for Real-Time Logs

```typescript
// hooks/useWebSocketLogs.ts
import { useEffect, useState, useRef } from 'react';

export function useWebSocketLogs(sessionId: string) {
  const [logs, setLogs] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_BASE_URL}/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [sessionId]);

  return { logs, isConnected };
}
```

---

## 6. Complete Component Example

```typescript
// app/generate/page.tsx
'use client';

import { useState } from 'react';
import { paperService } from '@/services/paperService';
import { useWebSocketLogs } from '@/hooks/useWebSocketLogs';

export default function GeneratePaperPage() {
  const [formData, setFormData] = useState({
    subject: '',
    grade: '',
    board: '',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { logs, isConnected } = useWebSocketLogs('session_1');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await paperService.generatePaper(formData);
      setResult(response.file_path);
    } catch (err) {
      setError('Failed to generate paper. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Generate Question Paper</h1>

      <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
        <div>
          <label className="block mb-2">Subject</label>
          <input
            type="text"
            name="subject"
            value={formData.subject}
            onChange={handleChange}
            className="w-full border p-2 rounded"
            required
          />
        </div>

        <div>
          <label className="block mb-2">Grade</label>
          <input
            type="text"
            name="grade"
            value={formData.grade}
            onChange={handleChange}
            className="w-full border p-2 rounded"
            required
          />
        </div>

        <div>
          <label className="block mb-2">Board</label>
          <select
            name="board"
            value={formData.board}
            onChange={handleChange}
            className="w-full border p-2 rounded"
            required
          >
            <option value="">Select Board</option>
            <option value="CBSE">CBSE</option>
            <option value="ICSE">ICSE</option>
            <option value="State Board">State Board</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Generating...' : 'Generate Paper'}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-4 p-4 bg-green-100 text-green-700 rounded">
          Paper generated successfully! File: {result}
        </div>
      )}

      {/* Real-time Logs */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-2">
          Generation Logs {isConnected ? '🟢' : '🔴'}
        </h2>
        <div className="bg-gray-900 text-green-400 p-4 rounded h-64 overflow-y-auto font-mono text-sm">
          {logs.map((log, index) => (
            <div key={index}>{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## 7. Backend Setup Instructions for Frontend Team

**Run the FastAPI backend:**
```bash
# From the QPilot directory
cd backend
uvicorn main:backend --reload --port 8000
```

**Check if backend is running:**
- Visit: `http://localhost:8000/docs` (FastAPI Swagger UI)

---

## 8. CORS Configuration (Backend Side)

⚠️ **Important**: The backend needs CORS enabled for Next.js frontend to communicate.

**Tell your backend team to add this to `main.py`:**
```python
from fastapi.middleware.cors import CORSMiddleware

backend = FastAPI()

# Add CORS middleware
backend.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 9. Best Practices for Frontend Team

### Error Handling
```typescript
try {
  const response = await paperService.generatePaper(data);
  // Success handling
} catch (error) {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 422) {
      // Validation error
    } else if (error.response?.status === 500) {
      // Server error
    }
  }
}
```

### Loading States
- Show loading spinner during API calls
- Disable submit button while processing
- Display progress using WebSocket logs

### Form Validation
- Validate inputs before sending to backend
- Match the backend schema requirements

---

## 10. API Testing Tools

**For testing before frontend is ready:**
- **Postman/Insomnia**: Test REST API endpoints
- **WebSocket Client**: Test WebSocket connection (e.g., `websocat` or browser extensions)

**Example cURL:**
```bash
curl -X POST http://localhost:8000/generate-paper \
  -H "Content-Type: application/json" \
  -d '{"subject":"Math","grade":"10","board":"CBSE"}'
```

---

## 11. Project Structure Recommendation

```
nextjs-frontend/
├── app/
│   ├── generate/
│   │   └── page.tsx
│   └── layout.tsx
├── components/
│   ├── PaperForm.tsx
│   └── LogsViewer.tsx
├── services/
│   └── paperService.ts
├── hooks/
│   └── useWebSocketLogs.ts
├── lib/
│   └── apiClient.ts
├── types/
│   └── api.ts
└── .env.local
```

---

## 12. TypeScript Types (Shared Understanding)

```typescript
// types/api.ts
export interface PaperGenerationRequest {
  subject: string;
  grade: string;
  board: string;
}

export interface PaperGenerationResponse {
  status: 'success' | 'error';
  file_path: string;
}
```

---

## 13. Deployment Considerations

**Production Environment Variables:**
```env
NEXT_PUBLIC_API_BASE_URL=https://api.qpilot.com
NEXT_PUBLIC_WS_BASE_URL=wss://api.qpilot.com
```

**Backend CORS Update:**
```python
allow_origins=[
    "http://localhost:3000",  # Development
    "https://qpilot.vercel.app",  # Production
]
```

---

## Quick Start Checklist for Frontend Team

- [ ] Clone/setup Next.js project
- [ ] Install dependencies (`axios` or `react-query`)
- [ ] Create `.env.local` with API URLs
- [ ] Implement API service layer
- [ ] Create WebSocket hook for logs
- [ ] Build form component with validation
- [ ] Test with running backend
- [ ] Handle errors and loading states
- [ ] Ensure backend has CORS enabled

---

## Contact & Support

For any questions or issues with the backend integration, please reach out to the backend team or refer to the FastAPI documentation at `http://localhost:8000/docs` when the server is running.
