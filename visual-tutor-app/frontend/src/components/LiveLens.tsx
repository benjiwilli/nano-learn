/**
 * Live Lens component for real-time video streaming and AI assistance
 */

import React, { useState, useCallback, useEffect, useRef } from 'react'
import { 
  Video, 
  VideoOff, 
  Send,
  Wifi,
  WifiOff,
  Sparkles,
  Loader2
} from 'lucide-react'
import { useCamera, useFrameCapture } from '../hooks/useCamera'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppSelector, useAppDispatch } from '../store'
import { setStreaming, setLiveMode } from '../store/slices/sessionSlice'

const LiveLens: React.FC = () => {
  const dispatch = useAppDispatch()
  const { isLoading } = useAppSelector((state) => state.explanation)
  
  const [manualQuestion, setManualQuestion] = useState('')
  const [messages, setMessages] = useState<Array<{ type: 'user' | 'ai'; text: string }>>([])
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const {
    videoRef,
    canvasRef,
    isStreaming: isCameraStreaming,
    error: cameraError,
    startCamera,
    stopCamera,
  } = useCamera({ facingMode: 'environment' })

  const {
    isConnected,
    error: wsError,
    connect,
    disconnect,
    sendVideoFrame,
    sendAudioTranscript,
    requestExplanation,
  } = useWebSocket({
    onMessage: (msg) => {
      if (msg.type === 'explanation' && msg.text) {
        const text = msg.text
        setMessages((prev) => [...prev, { type: 'ai' as const, text }])
      } else if (msg.type === 'analysis' && msg.text) {
        // Show brief analysis in messages
        const text = msg.text
        if (text.length < 200) {
          setMessages((prev) => [...prev, { type: 'ai' as const, text }])
        }
      }
    },
  })

  const { isCapturing, startCapture, stopCapture } = useFrameCapture(videoRef, 2)

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleStartSession = useCallback(async () => {
    try {
      await connect()
      await startCamera()
      dispatch(setLiveMode(true))
    } catch (error) {
      console.error('Failed to start session:', error)
    }
  }, [connect, startCamera, dispatch])

  const handleStopSession = useCallback(() => {
    stopCapture()
    stopCamera()
    disconnect()
    dispatch(setLiveMode(false))
    dispatch(setStreaming(false))
    setMessages([])
  }, [stopCapture, stopCamera, disconnect, dispatch])

  const handleStartStreaming = useCallback(() => {
    if (!isConnected) return
    
    dispatch(setStreaming(true))
    startCapture((frame) => {
      sendVideoFrame(frame)
    })
  }, [isConnected, dispatch, startCapture, sendVideoFrame])

  const handleStopStreaming = useCallback(() => {
    stopCapture()
    dispatch(setStreaming(false))
  }, [stopCapture, dispatch])

  const handleSendQuestion = useCallback(() => {
    if (!manualQuestion.trim()) return
    
    setMessages((prev) => [...prev, { type: 'user', text: manualQuestion }])
    
    if (isConnected) {
      sendAudioTranscript(manualQuestion)
    }
    
    setManualQuestion('')
  }, [manualQuestion, isConnected, sendAudioTranscript])

  const handleRequestExplanation = useCallback(() => {
    if (!isConnected) return
    requestExplanation('current concept')
    setMessages((prev) => [...prev, { type: 'user', text: 'Generate visual explanation' }])
  }, [isConnected, requestExplanation])

  // Not started state
  if (!isCameraStreaming && !isConnected) {
    return (
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Live Lens</h2>
        
        <div className="text-center py-8">
          <div className="w-24 h-24 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-xl shadow-primary-500/30">
            <Video className="w-12 h-12 text-white" />
          </div>
          
          <h3 className="text-2xl font-bold text-slate-900 mb-3">
            Real-Time AI Assistance
          </h3>
          <p className="text-slate-600 mb-8 max-w-md mx-auto text-lg leading-relaxed">
            Point your camera at study material and ask questions in real-time.
            The AI will analyze what you're looking at and create visual explanations.
          </p>
          
          <button
            onClick={handleStartSession}
            className="btn btn-primary px-8 py-3 text-lg flex items-center gap-2 mx-auto"
          >
            <Video className="w-5 h-5" />
            Start Live Session
          </button>
        </div>
        
        {cameraError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {cameraError}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Video feed */}
      <div className="card p-0 overflow-hidden">
        <div className="relative">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-auto"
          />
          <canvas ref={canvasRef} className="hidden" />
          
          {/* Status overlay */}
          <div className="absolute top-3 left-3 flex items-center gap-2">
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-sm font-medium ${
              isConnected ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
            }`}>
              {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            
            {isCapturing && (
              <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500 text-white rounded-full text-sm font-medium">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                Streaming
              </div>
            )}
          </div>
          
          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
              <div className="bg-white rounded-lg p-4 flex items-center gap-3">
                <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                <span className="font-medium text-gray-900">Generating explanation...</span>
              </div>
            </div>
          )}
        </div>
        
        {/* Controls */}
        <div className="p-6 bg-white border-t border-slate-100">
          <div className="flex items-center justify-center gap-4">
            {/* Streaming toggle */}
            {isCapturing ? (
              <button
                onClick={handleStopStreaming}
                className="btn btn-danger flex items-center gap-2 shadow-md"
              >
                <VideoOff className="w-4 h-4" />
                Pause Analysis
              </button>
            ) : (
              <button
                onClick={handleStartStreaming}
                disabled={!isConnected}
                className="btn btn-success flex items-center gap-2 shadow-md"
              >
                <Video className="w-4 h-4" />
                Start Analysis
              </button>
            )}
            
            {/* Generate explanation button */}
            <button
              onClick={handleRequestExplanation}
              disabled={!isConnected || isLoading}
              className="btn btn-primary flex items-center gap-2 shadow-md"
            >
              <Sparkles className="w-4 h-4" />
              Generate Visual
            </button>
            
            {/* End session */}
            <button
              onClick={handleStopSession}
              className="btn btn-secondary shadow-sm"
            >
              End Session
            </button>
          </div>
        </div>
      </div>
      
      {/* Messages */}
      <div className="card h-[400px] flex flex-col">
        <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          Live Conversation
        </h3>
        
        <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-2 scrollbar-thin">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-2">
              <Video className="w-8 h-8 opacity-50" />
              <p>Start streaming and ask questions!</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-5 py-3 shadow-sm ${
                    msg.type === 'user'
                      ? 'bg-primary-600 text-white rounded-2xl rounded-br-none'
                      : 'bg-slate-100 text-slate-800 rounded-2xl rounded-bl-none border border-slate-200'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={manualQuestion}
            onChange={(e) => setManualQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSendQuestion()
            }}
            placeholder="Ask a question about what you're studying..."
            className="input flex-1"
          />
          <button
            onClick={handleSendQuestion}
            disabled={!manualQuestion.trim() || !isConnected}
            className="btn btn-primary px-4"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      {/* Errors */}
      {(cameraError || wsError) && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {cameraError || wsError}
        </div>
      )}
    </div>
  )
}

export default LiveLens
