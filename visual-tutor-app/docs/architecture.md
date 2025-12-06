# Visual Tutor - System Architecture

## Overview

Visual Tutor is a multimodal AI education application that combines real-time analysis with visual explanation generation to help students understand complex concepts.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Camera    │  │ Annotation  │  │      Live Lens          │ │
│  │   Capture   │  │   Canvas    │  │   (WebSocket Client)    │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         └────────────────┼──────────────────────┘               │
│                          │                                      │
│                    ┌─────▼─────┐                                │
│                    │   Redux   │                                │
│                    │   Store   │                                │
│                    └─────┬─────┘                                │
└──────────────────────────┼──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │ REST API   │ WebSocket  │
              └────────────┼────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Backend (FastAPI)                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │   Analyze   │─▶│  Generate   │─▶│    Explain      │  │   │
│  │  │  Confusion  │  │   Prompt    │  │    Diagram      │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └────────────┬──────────────┬───────────────┬─────────────┘   │
│               │              │               │                  │
│       ┌───────▼───────┐ ┌────▼────┐  ┌───────▼───────┐         │
│       │ Gemini Service│ │  Prompt │  │  Nano Banana  │         │
│       │   (Analysis)  │ │ Engine  │  │  Pro Service  │         │
│       └───────┬───────┘ └─────────┘  └───────┬───────┘         │
│               │                              │                  │
└───────────────┼──────────────────────────────┼──────────────────┘
                │                              │
        ┌───────▼───────┐              ┌───────▼───────┐
        │  Gemini 3.0   │              │  Nano Banana  │
        │     Pro       │              │     Pro       │
        │    (API)      │              │    (API)      │
        └───────────────┘              └───────────────┘
```

## Component Details

### Frontend Layer

#### Camera Capture Component
- **Purpose**: Capture images from device camera or file upload
- **Technology**: WebRTC getUserMedia API
- **Features**:
  - Camera permission handling
  - Front/back camera switching
  - Image preview and retake
  - File upload alternative

#### Annotation Canvas Component
- **Purpose**: Allow students to mark areas of confusion
- **Technology**: HTML5 Canvas API
- **Tools**:
  - Circle (highlight areas)
  - Arrow (show relationships)
  - Freehand (general marking)
  - Text (explicit questions)
  - Rectangle (region selection)
  - Highlight (semi-transparent overlay)

#### Live Lens Component
- **Purpose**: Real-time video streaming with AI analysis
- **Technology**: WebSocket with binary frame transmission
- **Features**:
  - 2 FPS frame streaming
  - Real-time analysis feedback
  - Voice input (future)
  - On-demand explanation generation

#### Redux Store
- **Slices**:
  - `sessionSlice`: WebSocket connection state
  - `annotationSlice`: Drawing state and history
  - `explanationSlice`: Generated explanations and history

### Backend Layer

#### Orchestrator Service
The core agentic component that coordinates the multi-step workflow:

1. **Snap-and-Explain Workflow**:
   ```
   Image + Annotations → Gemini Analysis → Prompt Generation → 
   Nano Banana Pro → Generated Image → Gemini Explanation
   ```

2. **Live Lens Workflow**:
   ```
   Video Frame + Audio → Gemini Analysis → Confusion Detection →
   (If confused) → Prompt Generation → Image Generation → Explanation
   ```

#### Gemini Service
- **Purpose**: Multimodal AI analysis and reasoning
- **Capabilities**:
  - Image analysis (identify concepts, confusion points)
  - Prompt engineering for image generation
  - Explanation generation (verbal walkthroughs)
  - Video frame analysis (live mode)

#### Nano Banana Pro Service
- **Purpose**: High-fidelity educational image generation
- **Features**:
  - Text-accurate rendering
  - Spatially-precise layouts
  - Multiple visual styles
  - Reference image support

### Data Flow

#### Snap-and-Explain Flow
```
1. User captures/uploads image
2. User adds annotations (circles, arrows, text)
3. Frontend sends image + annotations to backend
4. Orchestrator:
   a. Sends to Gemini for analysis
   b. Receives confusion analysis (concept, difficulty, subject)
   c. Generates Nano Banana Pro prompt
   d. Calls Nano Banana Pro for image generation
   e. Sends generated image back to Gemini for verbal explanation
5. Returns: original image, generated image, explanation
6. Frontend displays side-by-side comparison
```

#### Live Lens Flow
```
1. User starts live session (WebSocket connection)
2. Camera streams frames at 2 FPS
3. Frames sent to backend via WebSocket
4. Gemini analyzes frames continuously
5. When confusion detected (audio cues, explicit request):
   a. Orchestrator generates explanation image
   b. Returns image + verbal explanation via WebSocket
6. Frontend displays inline explanation
7. User can continue conversation
```

## Technology Stack

### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Runtime | Python 3.11+ |
| Async HTTP | httpx |
| WebSocket | starlette/websockets |
| Validation | Pydantic v2 |
| Logging | structlog |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | React 18 |
| Language | TypeScript |
| Build Tool | Vite |
| State | Redux Toolkit |
| Styling | Tailwind CSS |
| HTTP Client | Axios |
| WebSocket | Native WebSocket API |

### External APIs
| Service | Purpose |
|---------|---------|
| Gemini 3.0 Pro | Multimodal analysis, reasoning |
| Nano Banana Pro | Educational image generation |

## Scalability Considerations

### Horizontal Scaling
- Stateless backend design (state in Redis/external)
- WebSocket connection pooling
- Load balancer for API distribution

### Performance Optimizations
- Image compression before upload
- Frame rate limiting (2 FPS max)
- Response caching for common explanations
- CDN for generated images

### Rate Limiting
- Per-user request limits
- API call budgets
- Graceful degradation under load

## Security

### Input Validation
- Image size/format validation
- Annotation data sanitization
- WebSocket message validation

### Authentication (Future)
- JWT-based authentication
- Session management
- API key rotation

### Data Privacy
- No permanent image storage (optional)
- Encrypted transmission (HTTPS/WSS)
- Configurable data retention
