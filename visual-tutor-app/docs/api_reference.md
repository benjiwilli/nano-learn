# Visual Tutor - API Reference

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## Authentication

Currently, the API does not require authentication. Future versions will implement JWT-based auth.

---

## REST Endpoints

### Health Check

```http
GET /health
```

**Response**
```json
{
  "status": "healthy",
  "service": "visual-tutor-api",
  "version": "1.0.0"
}
```

---

### Snap and Explain

Process an annotated image and generate a visual explanation.

```http
POST /api/v1/snap-and-explain
```

**Request Body**
```json
{
  "image": "base64_encoded_image_data",
  "annotations": [
    {
      "type": "circle",
      "x": 0.5,
      "y": 0.5,
      "radius": 0.1,
      "color": "#FF0000",
      "stroke_width": 2
    },
    {
      "type": "text",
      "x": 0.6,
      "y": 0.4,
      "text": "?",
      "color": "#0000FF",
      "stroke_width": 2
    }
  ],
  "question": "How does this work?",
  "subject": "physics",
  "style_preference": "schematic"
}
```

**Annotation Types**

| Type | Required Fields | Optional Fields |
|------|-----------------|-----------------|
| `circle` | x, y | radius, color, stroke_width |
| `rectangle` | x, y | width, height, color, stroke_width |
| `arrow` | x, y | end_x, end_y, color, stroke_width |
| `freehand` | x, y | points, color, stroke_width |
| `text` | x, y | text, color |
| `highlight` | x, y | width, height, color |

**Response**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_image_url": "data:image/jpeg;base64,...",
  "generated_image_url": "https://cdn.example.com/generated/123.png",
  "explanation": "Look at the diagram I created for you...",
  "confusion_analysis": {
    "confusion_concept": "mechanical advantage in pulleys",
    "difficulty_level": "intermediate",
    "suggested_explanation_type": "schematic",
    "subject": "physics",
    "subtopic": "mechanics"
  },
  "generation_time_ms": 4523
}
```

**Error Response**
```json
{
  "error": "validation_error",
  "detail": "Image data is invalid or corrupted",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### Snap and Explain (File Upload)

Alternative endpoint accepting multipart file upload.

```http
POST /api/v1/snap-and-explain/upload
Content-Type: multipart/form-data
```

**Form Fields**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | File | Yes | Image file (JPEG, PNG, WebP) |
| annotations | String | No | JSON string of annotations |
| question | String | No | Student's question |

**Response**: Same as `/snap-and-explain`

---

### Get Supported Subjects

```http
GET /api/v1/subjects
```

**Response**
```json
{
  "subjects": [
    {
      "id": "math",
      "name": "Mathematics",
      "subtopics": ["algebra", "geometry", "calculus", "statistics"]
    },
    {
      "id": "physics",
      "name": "Physics",
      "subtopics": ["mechanics", "electromagnetism", "thermodynamics", "optics"]
    }
  ]
}
```

---

### Get Diagram Styles

```http
GET /api/v1/styles
```

**Response**
```json
{
  "styles": [
    {
      "id": "schematic",
      "name": "Schematic",
      "description": "Technical diagrams with precise layouts"
    },
    {
      "id": "cartoon",
      "name": "Cartoon",
      "description": "Fun, engaging illustrations for younger students"
    }
  ]
}
```

---

## WebSocket Endpoints

### Live Lens

Real-time video streaming and analysis.

```
WS /api/v1/live-lens
```

#### Client → Server Messages

**Video Frame**
```json
{
  "type": "video_frame",
  "data": "base64_encoded_jpeg_frame"
}
```

**Audio Transcript**
```json
{
  "type": "audio",
  "transcript": "I don't understand how this works"
}
```

**Request Explanation**
```json
{
  "type": "request_explanation",
  "concept": "the relationship between force and acceleration"
}
```

**Ping**
```json
{
  "type": "ping"
}
```

**Disconnect**
```json
{
  "type": "disconnect"
}
```

#### Server → Client Messages

**Connected**
```json
{
  "type": "connected",
  "session_id": "abc123-def456"
}
```

**Analysis Result**
```json
{
  "type": "analysis",
  "text": "I can see you're studying force diagrams"
}
```

**Image Generated**
```json
{
  "type": "image_generated",
  "image_url": "https://cdn.example.com/generated/456.png",
  "concept": "force and acceleration"
}
```

**Explanation**
```json
{
  "type": "explanation",
  "text": "Look at the diagram I created...",
  "audio_url": "https://cdn.example.com/audio/789.mp3"
}
```

**Status Update**
```json
{
  "type": "status",
  "message": "Generating explanation..."
}
```

**Error**
```json
{
  "type": "error",
  "message": "Failed to process frame"
}
```

**Pong**
```json
{
  "type": "pong"
}
```

---

### Get Active Sessions (Monitoring)

```http
GET /api/v1/live-lens/sessions
```

**Response**
```json
{
  "active_sessions": 5
}
```

---

## Error Codes

| HTTP Code | Description |
|-----------|-------------|
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Missing/invalid authentication |
| 413 | Payload Too Large - Image exceeds size limit |
| 422 | Unprocessable Entity - Validation failed |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server-side error |
| 503 | Service Unavailable - External API unavailable |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/snap-and-explain` | 10 requests/minute |
| `/live-lens` | 1 session/user |
| Video frames | 2 frames/second |

---

## Image Requirements

| Property | Requirement |
|----------|-------------|
| Max Size | 10 MB |
| Formats | JPEG, PNG, WebP, GIF |
| Min Dimensions | 100x100 pixels |
| Max Dimensions | 4096x4096 pixels |

---

## SDK Examples

### Python

```python
import httpx
import base64

async def get_explanation(image_path: str, question: str):
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/snap-and-explain",
            json={
                "image": image_b64,
                "annotations": [
                    {"type": "circle", "x": 0.5, "y": 0.5, "radius": 0.1}
                ],
                "question": question
            }
        )
        return response.json()
```

### JavaScript

```javascript
async function getExplanation(imageFile, question) {
  const base64 = await fileToBase64(imageFile);
  
  const response = await fetch('/api/v1/snap-and-explain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image: base64,
      annotations: [
        { type: 'circle', x: 0.5, y: 0.5, radius: 0.1 }
      ],
      question
    })
  });
  
  return response.json();
}
```

### WebSocket (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/live-lens');

ws.onopen = () => {
  console.log('Connected to Live Lens');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'connected':
      console.log('Session:', message.session_id);
      break;
    case 'image_generated':
      displayImage(message.image_url);
      break;
    case 'explanation':
      displayExplanation(message.text);
      break;
  }
};

// Send video frame
function sendFrame(base64Frame) {
  ws.send(JSON.stringify({
    type: 'video_frame',
    data: base64Frame
  }));
}

// Request explanation
function requestExplanation(concept) {
  ws.send(JSON.stringify({
    type: 'request_explanation',
    concept
  }));
}
```
