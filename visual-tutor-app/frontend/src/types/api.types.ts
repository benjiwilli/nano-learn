/**
 * API type definitions for Visual Tutor
 */

// Annotation types
export type AnnotationType = 'circle' | 'arrow' | 'freehand' | 'text' | 'rectangle' | 'highlight'

export interface Annotation {
  id: string
  type: AnnotationType
  x: number
  y: number
  color: string
  strokeWidth: number
  // Type-specific properties
  radius?: number
  width?: number
  height?: number
  endX?: number
  endY?: number
  text?: string
  points?: Array<{ x: number; y: number }>
}

// Request types
export interface SnapAndExplainRequest {
  image: string // base64
  annotations?: Array<{
    type: AnnotationType
    x: number
    y: number
    color: string
    stroke_width: number
    radius?: number
    width?: number
    height?: number
    end_x?: number
    end_y?: number
    text?: string
    points?: Array<{ x: number; y: number }>
  }>
  question?: string
  subject?: string
  style_preference?: DiagramStyle
}

// Response types
export interface ConfusionAnalysis {
  confusion_concept: string
  difficulty_level: 'beginner' | 'intermediate' | 'advanced'
  suggested_explanation_type: DiagramStyle
  subject: string
  subtopic: string
}

export interface SnapAndExplainResponse {
  request_id: string
  original_image_url: string
  generated_image_url: string
  explanation: string
  confusion_analysis: ConfusionAnalysis
  generation_time_ms: number
}

// Diagram styles
export type DiagramStyle = 'schematic' | 'cartoon' | 'realistic' | 'minimalist' | 'gamified'

export interface StyleInfo {
  id: DiagramStyle
  name: string
  description: string
}

// Subject types
export interface SubjectInfo {
  id: string
  name: string
  subtopics: string[]
}

// WebSocket message types
export interface WSMessage {
  type: 'video_frame' | 'audio' | 'request_explanation' | 'ping' | 'disconnect'
  data?: string
  transcript?: string
  concept?: string
}

export interface WSResponse {
  type: 'connected' | 'analysis' | 'image_generated' | 'explanation' | 'error' | 'status' | 'pong'
  session_id?: string
  text?: string
  message?: string
  image_url?: string
  concept?: string
  audio_url?: string
  timestamp?: number
}

// Live Lens types
export interface LiveLensAnalysis {
  content_type: string
  visible_concepts: string[]
  potential_confusion: string | null
  suggested_action: 'wait' | 'explain' | 'generate_diagram'
}

// Health check
export interface HealthCheckResponse {
  status: string
  service: string
  version: string
}

// Error response
export interface ErrorResponse {
  error: string
  detail: string
  request_id?: string
}
