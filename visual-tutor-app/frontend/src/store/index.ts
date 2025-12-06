import { configureStore } from '@reduxjs/toolkit'
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux'
import sessionReducer from './slices/sessionSlice'
import annotationReducer from './slices/annotationSlice'
import explanationReducer from './slices/explanationSlice'

export const store = configureStore({
  reducer: {
    session: sessionReducer,
    annotation: annotationReducer,
    explanation: explanationReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types (for WebSocket and File objects)
        ignoredActions: ['session/setWebSocket'],
        ignoredPaths: ['session.webSocket'],
      },
    }),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

// Typed hooks
export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector
