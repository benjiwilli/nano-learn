/**
 * Custom hook for camera access and control
 */

import { useState, useRef, useCallback, useEffect } from 'react'

interface UseCameraOptions {
  facingMode?: 'user' | 'environment'
  width?: number
  height?: number
  onError?: (error: Error) => void
}

interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement>
  canvasRef: React.RefObject<HTMLCanvasElement>
  isStreaming: boolean
  hasPermission: boolean | null
  error: string | null
  startCamera: () => Promise<void>
  stopCamera: () => void
  captureImage: () => string | null
  switchCamera: () => Promise<void>
  currentFacingMode: 'user' | 'environment'
}

export function useCamera(options: UseCameraOptions = {}): UseCameraReturn {
  const {
    facingMode = 'environment',
    width = 1920,
    height = 1080,
    onError,
  } = options

  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const [isStreaming, setIsStreaming] = useState(false)
  const [hasPermission, setHasPermission] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentFacingMode, setCurrentFacingMode] = useState<'user' | 'environment'>(facingMode)

  const startCamera = useCallback(async () => {
    try {
      setError(null)

      // Stop any existing stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }

      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: currentFacingMode,
          width: { ideal: width },
          height: { ideal: height },
        },
        audio: false,
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        setIsStreaming(true)
        setHasPermission(true)
      }
    } catch (err) {
      const error = err as Error
      console.error('Camera error:', error)
      
      let errorMessage = 'Failed to access camera'
      if (error.name === 'NotAllowedError') {
        errorMessage = 'Camera permission denied. Please allow camera access.'
        setHasPermission(false)
      } else if (error.name === 'NotFoundError') {
        errorMessage = 'No camera found on this device.'
      } else if (error.name === 'NotReadableError') {
        errorMessage = 'Camera is already in use by another application.'
      }
      
      setError(errorMessage)
      onError?.(new Error(errorMessage))
    }
  }, [currentFacingMode, width, height, onError])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsStreaming(false)
  }, [])

  const captureImage = useCallback((): string | null => {
    if (!videoRef.current || !canvasRef.current) {
      console.warn('Video or canvas ref not available')
      return null
    }

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    if (!ctx) {
      console.error('Failed to get canvas context')
      return null
    }

    // Set canvas size to video size
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Draw video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Return base64 image
    return canvas.toDataURL('image/jpeg', 0.9)
  }, [])

  const switchCamera = useCallback(async () => {
    const newMode = currentFacingMode === 'user' ? 'environment' : 'user'
    setCurrentFacingMode(newMode)
    
    if (isStreaming) {
      stopCamera()
      // Small delay before restarting
      setTimeout(() => {
        startCamera()
      }, 100)
    }
  }, [currentFacingMode, isStreaming, stopCamera, startCamera])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  return {
    videoRef,
    canvasRef,
    isStreaming,
    hasPermission,
    error,
    startCamera,
    stopCamera,
    captureImage,
    switchCamera,
    currentFacingMode,
  }
}

/**
 * Hook for capturing frames at regular intervals (for Live Lens)
 */
export function useFrameCapture(
  videoRef: React.RefObject<HTMLVideoElement>,
  fps: number = 2
) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [isCapturing, setIsCapturing] = useState(false)

  // Create canvas on mount
  useEffect(() => {
    canvasRef.current = document.createElement('canvas')
    return () => {
      canvasRef.current = null
    }
  }, [])

  const startCapture = useCallback(
    (onFrame: (base64Frame: string) => void) => {
      if (!videoRef.current || !canvasRef.current) return

      const video = videoRef.current
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')

      if (!ctx) return

      setIsCapturing(true)

      intervalRef.current = setInterval(() => {
        if (video.readyState === video.HAVE_ENOUGH_DATA) {
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight
          ctx.drawImage(video, 0, 0)
          const base64 = canvas.toDataURL('image/jpeg', 0.7).split(',')[1]
          onFrame(base64)
        }
      }, 1000 / fps)
    },
    [videoRef, fps]
  )

  const stopCapture = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsCapturing(false)
  }, [])

  // Cleanup
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  return {
    isCapturing,
    startCapture,
    stopCapture,
  }
}

export default useCamera
