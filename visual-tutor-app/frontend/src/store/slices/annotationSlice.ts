import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { CanvasAnnotation, ToolType } from '../../types/canvas.types'

interface AnnotationState {
  annotations: CanvasAnnotation[]
  selectedAnnotationId: string | null
  currentTool: ToolType
  currentColor: string
  strokeWidth: number
  history: CanvasAnnotation[][]
  historyIndex: number
  capturedImage: string | null
  isDrawing: boolean
}

const initialState: AnnotationState = {
  annotations: [],
  selectedAnnotationId: null,
  currentTool: 'circle',
  currentColor: '#FF0000',
  strokeWidth: 3,
  history: [[]],
  historyIndex: 0,
  capturedImage: null,
  isDrawing: false,
}

const annotationSlice = createSlice({
  name: 'annotation',
  initialState,
  reducers: {
    setCurrentTool: (state, action: PayloadAction<ToolType>) => {
      state.currentTool = action.payload
      state.selectedAnnotationId = null
    },
    setCurrentColor: (state, action: PayloadAction<string>) => {
      state.currentColor = action.payload
    },
    setStrokeWidth: (state, action: PayloadAction<number>) => {
      state.strokeWidth = action.payload
    },
    setCapturedImage: (state, action: PayloadAction<string | null>) => {
      state.capturedImage = action.payload
      if (action.payload === null) {
        // Clear annotations when clearing image
        state.annotations = []
        state.history = [[]]
        state.historyIndex = 0
      }
    },
    setIsDrawing: (state, action: PayloadAction<boolean>) => {
      state.isDrawing = action.payload
    },
    addAnnotation: (state, action: PayloadAction<CanvasAnnotation>) => {
      state.annotations.push(action.payload)
      // Update history
      state.history = state.history.slice(0, state.historyIndex + 1)
      state.history.push([...state.annotations])
      state.historyIndex = state.history.length - 1
    },
    updateAnnotation: (state, action: PayloadAction<{ id: string; updates: Partial<CanvasAnnotation> }>) => {
      const index = state.annotations.findIndex((a) => a.id === action.payload.id)
      if (index !== -1) {
        state.annotations[index] = { ...state.annotations[index], ...action.payload.updates }
      }
    },
    removeAnnotation: (state, action: PayloadAction<string>) => {
      state.annotations = state.annotations.filter((a) => a.id !== action.payload)
      // Update history
      state.history = state.history.slice(0, state.historyIndex + 1)
      state.history.push([...state.annotations])
      state.historyIndex = state.history.length - 1
    },
    selectAnnotation: (state, action: PayloadAction<string | null>) => {
      state.selectedAnnotationId = action.payload
    },
    clearAnnotations: (state) => {
      state.annotations = []
      state.selectedAnnotationId = null
      state.history.push([])
      state.historyIndex = state.history.length - 1
    },
    undo: (state) => {
      if (state.historyIndex > 0) {
        state.historyIndex -= 1
        state.annotations = [...state.history[state.historyIndex]]
        state.selectedAnnotationId = null
      }
    },
    redo: (state) => {
      if (state.historyIndex < state.history.length - 1) {
        state.historyIndex += 1
        state.annotations = [...state.history[state.historyIndex]]
        state.selectedAnnotationId = null
      }
    },
    resetAnnotations: (state) => {
      state.annotations = []
      state.selectedAnnotationId = null
      state.currentTool = 'circle'
      state.currentColor = '#FF0000'
      state.strokeWidth = 3
      state.history = [[]]
      state.historyIndex = 0
      state.capturedImage = null
      state.isDrawing = false
    },
  },
})

export const {
  setCurrentTool,
  setCurrentColor,
  setStrokeWidth,
  setCapturedImage,
  setIsDrawing,
  addAnnotation,
  updateAnnotation,
  removeAnnotation,
  selectAnnotation,
  clearAnnotations,
  undo,
  redo,
  resetAnnotations,
} = annotationSlice.actions

export default annotationSlice.reducer
