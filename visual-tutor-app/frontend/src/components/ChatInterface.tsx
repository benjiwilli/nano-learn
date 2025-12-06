/**
 * Chat interface component for follow-up questions and conversation
 */

import React, { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, MessageCircle } from 'lucide-react'
import { useAppSelector } from '../store'
import api from '../services/api'

interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  suggestions?: string[]
}

const ChatInterface: React.FC = () => {
  const { currentExplanation, isLoading } = useAppSelector((state) => state.explanation)
  
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Add welcome message when explanation is generated
  useEffect(() => {
    if (currentExplanation && messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          type: 'assistant',
          content: `I've created a visual explanation for "${currentExplanation.confusionAnalysis.confusion_concept}". Feel free to ask follow-up questions!`,
          timestamp: new Date(),
        },
      ])
    }
  }, [currentExplanation])

  const handleSend = async () => {
    if (!input.trim() || isTyping) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const questionText = input.trim()
    setInput('')
    setIsTyping(true)

    try {
      // Call the backend follow-up endpoint
      const response = await api.post<{
        request_id: string
        response: string
        suggestions: string[]
      }>('/explain/follow-up', {
        question: questionText,
        context: currentExplanation?.explanation || '',
        concept: currentExplanation?.confusionAnalysis?.confusion_concept || '',
        request_id: currentExplanation?.requestId
      })

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: response.data.response,
        timestamp: new Date(),
        suggestions: response.data.suggestions
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error('Follow-up error:', error)
      
      // Fallback response if API fails
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: "That's a great question! Based on the diagram, I can help explain further. Would you like me to generate a new visual focusing on this specific aspect?",
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Don't show chat if no explanation yet
  if (!currentExplanation && messages.length === 0) {
    return null
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <MessageCircle className="w-5 h-5 text-blue-600" />
        <h3 className="font-semibold text-gray-900">Ask Follow-up Questions</h3>
      </div>

      {/* Messages container */}
      <div className="h-64 overflow-y-auto space-y-4 mb-4 pr-2 scrollbar-thin">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.type === 'user' ? 'flex-row-reverse' : ''
            }`}
          >
            {/* Avatar */}
            <div
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-md ${
                message.type === 'user'
                  ? 'bg-gradient-to-br from-primary-500 to-primary-700'
                  : 'bg-gradient-to-br from-secondary-500 to-secondary-700'
              }`}
            >
              {message.type === 'user' ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Bot className="w-4 h-4 text-white" />
              )}
            </div>

            {/* Message bubble */}
            <div
              className={`max-w-[80%] px-4 py-3 shadow-sm ${
                message.type === 'user'
                  ? 'bg-primary-600 text-white rounded-2xl rounded-tr-sm'
                  : 'bg-white border border-slate-100 text-slate-700 rounded-2xl rounded-tl-sm'
              }`}
            >
              <p className="text-sm leading-relaxed">{message.content}</p>
              <p
                className={`text-[10px] mt-1 opacity-70 ${
                  message.type === 'user' ? 'text-blue-100' : 'text-slate-400'
                }`}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-secondary-500 to-secondary-700 flex items-center justify-center shadow-md">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-secondary-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-secondary-400 rounded-full animate-bounce animation-delay-200" />
                <div className="w-1.5 h-1.5 bg-secondary-400 rounded-full animate-bounce animation-delay-400" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a follow-up question..."
          disabled={isTyping || isLoading}
          className="input flex-1"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isTyping || isLoading}
          className="btn btn-primary px-4 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isTyping ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Quick suggestions */}
      {messages.length <= 2 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            "Can you explain this differently?",
            "What's the next step?",
            "Why is this important?",
            "Show me an example",
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                setInput(suggestion)
                inputRef.current?.focus()
              }}
              className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default ChatInterface
