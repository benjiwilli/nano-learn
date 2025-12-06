/**
 * Custom hook for WebSocket connection management
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useAppDispatch } from '../store'
import { setSessionId, setConnected, setError, updateActivity } from '../store/slices/sessionSlice'
import { addLiveExplanation, setLoading } from '../store/slices/explanationSlice'
import { LiveLensWebSocket, createWebSocketUrl } from '../services/websocket'
import { WSResponse } from '../types/api.types'

interface UseWebSocketOptions {
  autoConnect?: boolean
  onMessage?: (message: WSResponse) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

interface UseWebSocketReturn {
  isConnected: boolean
  sessionId: string | null
  error: string | null
  connect: () => Promise<void>
  disconnect: () => void
  sendVideoFrame: (base64Frame: string) => boolean
  sendAudioTranscript: (transcript: string) => boolean
  requestExplanation: (concept: string) => boolean
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = false, onMessage, onConnect, onDisconnect } = options
  
  const dispatch = useAppDispatch()
  const wsRef = useRef<LiveLensWebSocket | null>(null)
  
  const [isConnected, setIsConnected] = useState(false)
  const [sessionId, setLocalSessionId] = useState<string | null>(null)
  const [error, setLocalError] = useState<string | null>(null)

  const handleMessage = useCallback((message: WSResponse) => {
    dispatch(updateActivity())
    
    switch (message.type) {
      case 'connected':
        if (message.session_id) {
          setLocalSessionId(message.session_id)
          dispatch(setSessionId(message.session_id))
        }
        break
        
      case 'image_generated':
        if (message.image_url) {
          dispatch(addLiveExplanation({
            imageUrl: message.image_url,
            explanation: '',
            concept: message.concept || '',
          }))
        }
        dispatch(setLoading(false))
        break
        
      case 'explanation':
        if (message.text) {
          dispatch(addLiveExplanation({
            imageUrl: '',
            explanation: message.text,
            concept: message.concept || '',
          }))
        }
        dispatch(setLoading(false))
        break
        
      case 'status':
        // Loading state
        dispatch(setLoading(true))
        break
        
      case 'error':
        setLocalError(message.message || 'An error occurred')
        dispatch(setError(message.message || 'An error occurred'))
        dispatch(setLoading(false))
        break
        
      case 'pong':
        // Ping response, connection is alive
        break
        
      default:
        break
    }
    
    onMessage?.(message)
  }, [dispatch, onMessage])

  const handleConnect = useCallback(() => {
    setIsConnected(true)
    setLocalError(null)
    dispatch(setConnected(true))
    dispatch(setError(null))
    onConnect?.()
  }, [dispatch, onConnect])

  const handleDisconnect = useCallback(() => {
    setIsConnected(false)
    setLocalSessionId(null)
    dispatch(setConnected(false))
    dispatch(setSessionId(null))
    onDisconnect?.()
  }, [dispatch, onDisconnect])

  const handleError = useCallback((event: Event) => {
    console.error('WebSocket error:', event)
    setLocalError('Connection error occurred')
    dispatch(setError('Connection error occurred'))
  }, [dispatch])

  const connect = useCallback(async () => {
    if (wsRef.current?.isConnected()) {
      return
    }

    try {
      wsRef.current = new LiveLensWebSocket({
        url: createWebSocketUrl(),
        onMessage: handleMessage,
        onConnect: handleConnect,
        onDisconnect: handleDisconnect,
        onError: handleError,
        reconnectAttempts: 3,
        reconnectDelay: 2000,
      })

      await wsRef.current.connect()
    } catch (err) {
      const error = err as Error
      setLocalError(error.message)
      dispatch(setError(error.message))
    }
  }, [handleMessage, handleConnect, handleDisconnect, handleError, dispatch])

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect()
    wsRef.current = null
  }, [])

  const sendVideoFrame = useCallback((base64Frame: string): boolean => {
    return wsRef.current?.sendVideoFrame(base64Frame) ?? false
  }, [])

  const sendAudioTranscript = useCallback((transcript: string): boolean => {
    return wsRef.current?.sendAudioTranscript(transcript) ?? false
  }, [])

  const requestExplanation = useCallback((concept: string): boolean => {
    dispatch(setLoading(true))
    return wsRef.current?.requestExplanation(concept) ?? false
  }, [dispatch])

  // Auto-connect if enabled
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
    
    return () => {
      disconnect()
    }
  }, [autoConnect]) // Only run on mount/unmount

  return {
    isConnected,
    sessionId,
    error,
    connect,
    disconnect,
    sendVideoFrame,
    sendAudioTranscript,
    requestExplanation,
  }
}

export default useWebSocket
