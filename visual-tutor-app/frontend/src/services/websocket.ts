/**
 * WebSocket service for Live Lens real-time communication
 */

import { WSMessage, WSResponse } from '../types/api.types'

type MessageHandler = (message: WSResponse) => void
type ConnectionHandler = () => void
type ErrorHandler = (error: Event) => void

interface WebSocketConfig {
  url: string
  onMessage: MessageHandler
  onConnect?: ConnectionHandler
  onDisconnect?: ConnectionHandler
  onError?: ErrorHandler
  reconnectAttempts?: number
  reconnectDelay?: number
}

export class LiveLensWebSocket {
  private ws: WebSocket | null = null
  private config: WebSocketConfig
  private reconnectCount = 0
  private isManualClose = false
  private pingInterval: ReturnType<typeof setInterval> | null = null
  private sessionId: string | null = null

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectAttempts: 3,
      reconnectDelay: 2000,
      ...config,
    }
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.isManualClose = false
        this.ws = new WebSocket(this.config.url)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.reconnectCount = 0
          this.startPingInterval()
          this.config.onConnect?.()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WSResponse = JSON.parse(event.data)
            
            // Handle session ID
            if (message.type === 'connected' && message.session_id) {
              this.sessionId = message.session_id
            }
            
            this.config.onMessage(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason)
          this.stopPingInterval()
          this.config.onDisconnect?.()

          if (!this.isManualClose && this.reconnectCount < (this.config.reconnectAttempts || 3)) {
            this.reconnectCount++
            console.log(`Reconnecting... Attempt ${this.reconnectCount}`)
            setTimeout(() => this.connect(), this.config.reconnectDelay)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.config.onError?.(error)
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.isManualClose = true
    this.stopPingInterval()
    
    if (this.ws) {
      // Send disconnect message
      this.send({ type: 'disconnect' })
      this.ws.close()
      this.ws = null
    }
    
    this.sessionId = null
  }

  /**
   * Send a message through the WebSocket
   */
  send(message: WSMessage): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      return true
    }
    console.warn('WebSocket not connected, cannot send message')
    return false
  }

  /**
   * Send a video frame
   */
  sendVideoFrame(base64Frame: string): boolean {
    return this.send({
      type: 'video_frame',
      data: base64Frame,
    })
  }

  /**
   * Send audio transcript
   */
  sendAudioTranscript(transcript: string): boolean {
    return this.send({
      type: 'audio',
      transcript,
    })
  }

  /**
   * Request explanation for a specific concept
   */
  requestExplanation(concept: string): boolean {
    return this.send({
      type: 'request_explanation',
      concept,
    })
  }

  /**
   * Get the current session ID
   */
  getSessionId(): string | null {
    return this.sessionId
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' })
    }, 30000) // Ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }
}

/**
 * Create WebSocket URL from current location
 */
export function createWebSocketUrl(path: string = '/api/v1/live-lens'): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = (import.meta as any).env?.VITE_WS_HOST || window.location.host
  return `${protocol}//${host}${path}`
}

/**
 * Singleton instance for easy access
 */
let wsInstance: LiveLensWebSocket | null = null

export function getWebSocketInstance(config?: Partial<WebSocketConfig>): LiveLensWebSocket {
  if (!wsInstance && config) {
    wsInstance = new LiveLensWebSocket({
      url: createWebSocketUrl(),
      onMessage: () => {},
      ...config,
    })
  }
  return wsInstance!
}

export function destroyWebSocketInstance(): void {
  if (wsInstance) {
    wsInstance.disconnect()
    wsInstance = null
  }
}

export default LiveLensWebSocket
