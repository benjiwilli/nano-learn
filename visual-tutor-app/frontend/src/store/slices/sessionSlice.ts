/**
 * Session Slice for Visual Tutor App
 * 
 * Manages session state including:
 * - Live mode streaming state
 * - Session persistence
 * - User preferences
 * - Session history
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface SessionHistory {
  id: string
  timestamp: number
  mode: 'snap' | 'live' | 'step-by-step'
  concept?: string
  subject?: string
  successful: boolean
}

interface UserPreferences {
  preferredStyle: string
  preferredDifficulty: string
  darkMode: boolean
  autoPlaySpeed: number // milliseconds per step
  enableSoundEffects: boolean
}

interface SessionState {
  // Live mode state
  isLiveMode: boolean
  isStreaming: boolean
  sessionId: string | null
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error'
  lastHeartbeat: number | null
  
  // Session info
  sessionStartTime: number | null
  totalExplanations: number
  totalLiveMinutes: number
  
  // History
  sessionHistory: SessionHistory[]
  
  // Preferences
  preferences: UserPreferences
  
  // Current session context
  currentSubject: string | null
  currentDifficulty: string
  recentConcepts: string[]
}

const loadPreferences = (): UserPreferences => {
  try {
    const saved = localStorage.getItem('visualTutor_preferences')
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to load preferences:', e)
  }
  
  return {
    preferredStyle: 'educational',
    preferredDifficulty: 'intermediate',
    darkMode: false,
    autoPlaySpeed: 5000,
    enableSoundEffects: false
  }
}

const loadSessionHistory = (): SessionHistory[] => {
  try {
    const saved = localStorage.getItem('visualTutor_history')
    if (saved) {
      const history = JSON.parse(saved)
      // Keep only last 50 entries and last 7 days
      const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000)
      return history
        .filter((h: SessionHistory) => h.timestamp > weekAgo)
        .slice(0, 50)
    }
  } catch (e) {
    console.error('Failed to load session history:', e)
  }
  
  return []
}

const initialState: SessionState = {
  isLiveMode: false,
  isStreaming: false,
  sessionId: null,
  connectionStatus: 'disconnected',
  lastHeartbeat: null,
  
  sessionStartTime: null,
  totalExplanations: 0,
  totalLiveMinutes: 0,
  
  sessionHistory: loadSessionHistory(),
  preferences: loadPreferences(),
  
  currentSubject: null,
  currentDifficulty: 'intermediate',
  recentConcepts: []
}

const sessionSlice = createSlice({
  name: 'session',
  initialState,
  reducers: {
    // Live mode controls
    setLiveMode: (state, action: PayloadAction<boolean>) => {
      state.isLiveMode = action.payload
      if (action.payload && !state.sessionStartTime) {
        state.sessionStartTime = Date.now()
      }
    },
    
    setStreaming: (state, action: PayloadAction<boolean>) => {
      state.isStreaming = action.payload
    },
    
    setSessionId: (state, action: PayloadAction<string | null>) => {
      state.sessionId = action.payload
    },
    
    setConnectionStatus: (state, action: PayloadAction<SessionState['connectionStatus']>) => {
      state.connectionStatus = action.payload
    },
    
    updateHeartbeat: (state) => {
      state.lastHeartbeat = Date.now()
    },
    
    // Session tracking
    incrementExplanations: (state) => {
      state.totalExplanations += 1
    },
    
    updateLiveMinutes: (state, action: PayloadAction<number>) => {
      state.totalLiveMinutes = action.payload
    },
    
    // History management
    addToHistory: (state, action: PayloadAction<Omit<SessionHistory, 'id' | 'timestamp'>>) => {
      const entry: SessionHistory = {
        ...action.payload,
        id: `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now()
      }
      
      state.sessionHistory.unshift(entry)
      
      // Keep only last 50 entries
      if (state.sessionHistory.length > 50) {
        state.sessionHistory = state.sessionHistory.slice(0, 50)
      }
      
      // Persist to localStorage
      try {
        localStorage.setItem('visualTutor_history', JSON.stringify(state.sessionHistory))
      } catch (e) {
        console.error('Failed to save session history:', e)
      }
    },
    
    clearHistory: (state) => {
      state.sessionHistory = []
      localStorage.removeItem('visualTutor_history')
    },
    
    // Preferences
    updatePreferences: (state, action: PayloadAction<Partial<UserPreferences>>) => {
      state.preferences = { ...state.preferences, ...action.payload }
      
      // Persist to localStorage
      try {
        localStorage.setItem('visualTutor_preferences', JSON.stringify(state.preferences))
      } catch (e) {
        console.error('Failed to save preferences:', e)
      }
    },
    
    // Context
    setCurrentSubject: (state, action: PayloadAction<string | null>) => {
      state.currentSubject = action.payload
    },
    
    setCurrentDifficulty: (state, action: PayloadAction<string>) => {
      state.currentDifficulty = action.payload
    },
    
    addRecentConcept: (state, action: PayloadAction<string>) => {
      // Remove if already exists
      state.recentConcepts = state.recentConcepts.filter(c => c !== action.payload)
      
      // Add to front
      state.recentConcepts.unshift(action.payload)
      
      // Keep only last 10
      if (state.recentConcepts.length > 10) {
        state.recentConcepts = state.recentConcepts.slice(0, 10)
      }
    },
    
    // Reset session
    resetSession: (state) => {
      state.isLiveMode = false
      state.isStreaming = false
      state.sessionId = null
      state.connectionStatus = 'disconnected'
      state.lastHeartbeat = null
      state.sessionStartTime = null
      state.currentSubject = null
    }
  }
})

// Legacy action aliases for backward compatibility
const setConnected = (connected: boolean) => 
  sessionSlice.actions.setConnectionStatus(connected ? 'connected' : 'disconnected')

const setError = (error: string | null) => {
  // Error handling is managed through connectionStatus
  console.warn('Session error:', error)
  return sessionSlice.actions.setConnectionStatus(error ? 'error' : 'connected')
}

const updateActivity = () => sessionSlice.actions.updateHeartbeat()

export const {
  setLiveMode,
  setStreaming,
  setSessionId,
  setConnectionStatus,
  updateHeartbeat,
  incrementExplanations,
  updateLiveMinutes,
  addToHistory,
  clearHistory,
  updatePreferences,
  setCurrentSubject,
  setCurrentDifficulty,
  addRecentConcept,
  resetSession
} = sessionSlice.actions

// Export legacy aliases
export { setConnected, setError, updateActivity }

export default sessionSlice.reducer

// Selectors
export const selectIsLiveActive = (state: { session: SessionState }) => 
  state.session.isLiveMode && state.session.connectionStatus === 'connected'

export const selectSessionDuration = (state: { session: SessionState }) => {
  if (!state.session.sessionStartTime) return 0
  return Math.floor((Date.now() - state.session.sessionStartTime) / 1000)
}

export const selectRecentSubjects = (state: { session: SessionState }) => {
  const subjects = state.session.sessionHistory
    .filter(h => h.subject)
    .map(h => h.subject)
  return [...new Set(subjects)].slice(0, 5)
}
