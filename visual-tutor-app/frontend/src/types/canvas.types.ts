/**
 * Canvas and drawing type definitions
 */

export type ToolType = 'select' | 'circle' | 'arrow' | 'freehand' | 'text' | 'rectangle' | 'highlight' | 'eraser'

export interface Point {
  x: number
  y: number
}

export interface DrawingState {
  isDrawing: boolean
  startPoint: Point | null
  currentPoint: Point | null
  tool: ToolType
  color: string
  strokeWidth: number
}

export interface CanvasAnnotation {
  id: string
  type: ToolType
  startPoint: Point
  endPoint?: Point
  points?: Point[]
  text?: string
  color: string
  strokeWidth: number
  // Computed properties
  width?: number
  height?: number
  radius?: number
}

export interface CanvasSize {
  width: number
  height: number
}

export interface ImageData {
  src: string
  naturalWidth: number
  naturalHeight: number
  displayWidth: number
  displayHeight: number
}

export interface CanvasState {
  annotations: CanvasAnnotation[]
  selectedAnnotationId: string | null
  history: CanvasAnnotation[][]
  historyIndex: number
  image: ImageData | null
}

// Color palette
export const ANNOTATION_COLORS = [
  '#FF0000', // Red
  '#00FF00', // Green
  '#0000FF', // Blue
  '#FFFF00', // Yellow
  '#FF00FF', // Magenta
  '#00FFFF', // Cyan
  '#FF8000', // Orange
  '#8000FF', // Purple
  '#FFFFFF', // White
  '#000000', // Black
] as const

export type AnnotationColor = typeof ANNOTATION_COLORS[number]

// Stroke widths
export const STROKE_WIDTHS = [1, 2, 3, 5, 8, 12] as const

export type StrokeWidth = typeof STROKE_WIDTHS[number]

// Tool configuration
export interface ToolConfig {
  id: ToolType
  name: string
  icon: string
  cursor: string
  supportsColor: boolean
  supportsStrokeWidth: boolean
}

export const TOOL_CONFIGS: ToolConfig[] = [
  { id: 'select', name: 'Select', icon: 'mouse-pointer', cursor: 'default', supportsColor: false, supportsStrokeWidth: false },
  { id: 'circle', name: 'Circle', icon: 'circle', cursor: 'crosshair', supportsColor: true, supportsStrokeWidth: true },
  { id: 'rectangle', name: 'Rectangle', icon: 'square', cursor: 'crosshair', supportsColor: true, supportsStrokeWidth: true },
  { id: 'arrow', name: 'Arrow', icon: 'arrow-right', cursor: 'crosshair', supportsColor: true, supportsStrokeWidth: true },
  { id: 'freehand', name: 'Freehand', icon: 'pencil', cursor: 'crosshair', supportsColor: true, supportsStrokeWidth: true },
  { id: 'text', name: 'Text', icon: 'type', cursor: 'text', supportsColor: true, supportsStrokeWidth: false },
  { id: 'highlight', name: 'Highlight', icon: 'highlighter', cursor: 'crosshair', supportsColor: true, supportsStrokeWidth: true },
  { id: 'eraser', name: 'Eraser', icon: 'eraser', cursor: 'crosshair', supportsColor: false, supportsStrokeWidth: true },
]
