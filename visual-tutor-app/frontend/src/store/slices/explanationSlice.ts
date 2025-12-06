import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit'
import { SnapAndExplainResponse, ConfusionAnalysis, DiagramStyle } from '../../types/api.types'
import { api } from '../../services/api'

interface ExplanationState {
  isLoading: boolean
  error: string | null
  currentExplanation: {
    requestId: string
    originalImageUrl: string
    generatedImageUrl: string
    explanation: string
    confusionAnalysis: ConfusionAnalysis
    generationTimeMs: number
  } | null
  explanationHistory: Array<{
    requestId: string
    originalImageUrl: string
    generatedImageUrl: string
    explanation: string
    confusionAnalysis: ConfusionAnalysis
    generationTimeMs: number
    timestamp: number
  }>
  preferredStyle: DiagramStyle | null
}

const initialState: ExplanationState = {
  isLoading: false,
  error: null,
  currentExplanation: null,
  explanationHistory: [],
  preferredStyle: null,
}

// Async thunk for fetching explanations
export const fetchExplanation = createAsyncThunk(
  'explanation/fetch',
  async (
    {
      image,
      annotations,
      question,
    }: {
      image: string
      annotations: Array<{
        type: string
        x: number
        y: number
        color: string
        stroke_width: number
        radius?: number
        end_x?: number
        end_y?: number
        text?: string
        points?: Array<{ x: number; y: number }>
      }>
      question?: string
    },
    { rejectWithValue }
  ) => {
    try {
      const response = await api.snapAndExplain({
        image,
        annotations: annotations as any,
        question,
      })
      return response
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to get explanation')
    }
  }
)

const explanationSlice = createSlice({
  name: 'explanation',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },
    setCurrentExplanation: (state, action: PayloadAction<SnapAndExplainResponse>) => {
      state.currentExplanation = {
        requestId: action.payload.request_id,
        originalImageUrl: action.payload.original_image_url,
        generatedImageUrl: action.payload.generated_image_url,
        explanation: action.payload.explanation,
        confusionAnalysis: action.payload.confusion_analysis,
        generationTimeMs: action.payload.generation_time_ms,
      }
      // Add to history
      state.explanationHistory.unshift({
        ...state.currentExplanation,
        timestamp: Date.now(),
      })
      // Keep only last 10 items
      if (state.explanationHistory.length > 10) {
        state.explanationHistory = state.explanationHistory.slice(0, 10)
      }
    },
    clearCurrentExplanation: (state) => {
      state.currentExplanation = null
      state.error = null
    },
    setPreferredStyle: (state, action: PayloadAction<DiagramStyle | null>) => {
      state.preferredStyle = action.payload
    },
    addLiveExplanation: (
      state,
      action: PayloadAction<{
        imageUrl: string
        explanation: string
        concept: string
      }>
    ) => {
      // For live mode explanations
      const liveExplanation = {
        requestId: `live-${Date.now()}`,
        originalImageUrl: '',
        generatedImageUrl: action.payload.imageUrl,
        explanation: action.payload.explanation,
        confusionAnalysis: {
          confusion_concept: action.payload.concept,
          difficulty_level: 'intermediate' as const,
          suggested_explanation_type: 'schematic' as const,
          subject: 'general',
          subtopic: action.payload.concept,
        },
        generationTimeMs: 0,
      }
      state.currentExplanation = liveExplanation
      state.explanationHistory.unshift({
        ...liveExplanation,
        timestamp: Date.now(),
      })
    },
    resetExplanations: (state) => {
      state.isLoading = false
      state.error = null
      state.currentExplanation = null
      state.explanationHistory = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchExplanation.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(fetchExplanation.fulfilled, (state, action) => {
        state.isLoading = false
        state.currentExplanation = {
          requestId: action.payload.request_id,
          originalImageUrl: action.payload.original_image_url,
          generatedImageUrl: action.payload.generated_image_url,
          explanation: action.payload.explanation,
          confusionAnalysis: action.payload.confusion_analysis,
          generationTimeMs: action.payload.generation_time_ms,
        }
        state.explanationHistory.unshift({
          ...state.currentExplanation,
          timestamp: Date.now(),
        })
        if (state.explanationHistory.length > 10) {
          state.explanationHistory = state.explanationHistory.slice(0, 10)
        }
      })
      .addCase(fetchExplanation.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as string
      })
  },
})

export const {
  setLoading,
  setError,
  setCurrentExplanation,
  clearCurrentExplanation,
  setPreferredStyle,
  addLiveExplanation,
  resetExplanations,
} = explanationSlice.actions

export default explanationSlice.reducer
