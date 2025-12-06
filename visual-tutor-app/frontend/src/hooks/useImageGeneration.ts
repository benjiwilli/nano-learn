/**
 * Custom hook for image generation and explanation fetching
 */

import { useState, useCallback } from 'react'
import { useAppDispatch, useAppSelector } from '../store'
import { fetchExplanation, setLoading, setError } from '../store/slices/explanationSlice'
import { CanvasAnnotation } from '../types/canvas.types'

interface UseImageGenerationOptions {
  onSuccess?: () => void
  onError?: (error: string) => void
}

interface UseImageGenerationReturn {
  isLoading: boolean
  error: string | null
  generateExplanation: (
    image: string,
    annotations: CanvasAnnotation[],
    question?: string
  ) => Promise<void>
  reset: () => void
}

export function useImageGeneration(
  options: UseImageGenerationOptions = {}
): UseImageGenerationReturn {
  const { onSuccess, onError } = options
  
  const dispatch = useAppDispatch()
  const { isLoading, error } = useAppSelector((state) => state.explanation)

  const generateExplanation = useCallback(
    async (image: string, annotations: CanvasAnnotation[], question?: string) => {
      try {
        // Convert annotations to API format
        const apiAnnotations = annotations.map((ann) => ({
          type: ann.type as any,
          x: ann.startPoint.x,
          y: ann.startPoint.y,
          color: ann.color,
          stroke_width: ann.strokeWidth,
          radius: ann.radius,
          end_x: ann.endPoint?.x,
          end_y: ann.endPoint?.y,
          text: ann.text,
          points: ann.points,
        }))

        // Remove data URI prefix if present
        const base64Image = image.includes(',') ? image.split(',')[1] : image

        await dispatch(
          fetchExplanation({
            image: base64Image,
            annotations: apiAnnotations,
            question,
          })
        ).unwrap()

        onSuccess?.()
      } catch (err: any) {
        onError?.(err.message || 'Failed to generate explanation')
      }
    },
    [dispatch, onSuccess, onError]
  )

  const reset = useCallback(() => {
    dispatch(setError(null))
    dispatch(setLoading(false))
  }, [dispatch])

  return {
    isLoading,
    error,
    generateExplanation,
    reset,
  }
}

/**
 * Hook for polling generation status (for async generation)
 */
export function useGenerationPolling(_requestId: string | null) {
  const [status, setStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending')
  const [progress, setProgress] = useState(0)

  // Simulated progress (actual implementation would poll the server)
  const simulateProgress = useCallback(() => {
    setStatus('processing')
    let currentProgress = 0
    const interval = setInterval(() => {
      currentProgress += Math.random() * 15
      if (currentProgress >= 100) {
        currentProgress = 100
        setStatus('completed')
        clearInterval(interval)
      }
      setProgress(Math.min(currentProgress, 100))
    }, 500)

    return () => clearInterval(interval)
  }, [])

  return {
    status,
    progress,
    simulateProgress,
  }
}

/**
 * Utility function to merge annotations with image
 */
export function mergeAnnotationsWithImage(
  canvas: HTMLCanvasElement,
  imageUrl: string,
  annotations: CanvasAnnotation[]
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    
    img.onload = () => {
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('Failed to get canvas context'))
        return
      }

      // Set canvas size
      canvas.width = img.width
      canvas.height = img.height

      // Draw image
      ctx.drawImage(img, 0, 0)

      // Draw annotations
      annotations.forEach((ann) => {
        ctx.strokeStyle = ann.color
        ctx.fillStyle = ann.color
        ctx.lineWidth = ann.strokeWidth

        const startX = ann.startPoint.x * img.width
        const startY = ann.startPoint.y * img.height

        switch (ann.type) {
          case 'circle':
            if (ann.radius) {
              const radius = ann.radius * Math.min(img.width, img.height)
              ctx.beginPath()
              ctx.arc(startX, startY, radius, 0, Math.PI * 2)
              ctx.stroke()
            }
            break

          case 'rectangle':
            if (ann.endPoint) {
              const width = (ann.endPoint.x - ann.startPoint.x) * img.width
              const height = (ann.endPoint.y - ann.startPoint.y) * img.height
              ctx.strokeRect(startX, startY, width, height)
            }
            break

          case 'arrow':
            if (ann.endPoint) {
              const endX = ann.endPoint.x * img.width
              const endY = ann.endPoint.y * img.height
              
              // Draw line
              ctx.beginPath()
              ctx.moveTo(startX, startY)
              ctx.lineTo(endX, endY)
              ctx.stroke()
              
              // Draw arrowhead
              const angle = Math.atan2(endY - startY, endX - startX)
              const headLen = 15
              ctx.beginPath()
              ctx.moveTo(endX, endY)
              ctx.lineTo(
                endX - headLen * Math.cos(angle - Math.PI / 6),
                endY - headLen * Math.sin(angle - Math.PI / 6)
              )
              ctx.lineTo(
                endX - headLen * Math.cos(angle + Math.PI / 6),
                endY - headLen * Math.sin(angle + Math.PI / 6)
              )
              ctx.closePath()
              ctx.fill()
            }
            break

          case 'freehand':
            if (ann.points && ann.points.length > 1) {
              ctx.beginPath()
              ctx.moveTo(ann.points[0].x * img.width, ann.points[0].y * img.height)
              ann.points.forEach((point) => {
                ctx.lineTo(point.x * img.width, point.y * img.height)
              })
              ctx.stroke()
            }
            break

          case 'text':
            if (ann.text) {
              ctx.font = '16px Arial'
              ctx.fillText(ann.text, startX, startY)
            }
            break
        }
      })

      resolve(canvas.toDataURL('image/jpeg', 0.9))
    }

    img.onerror = () => reject(new Error('Failed to load image'))
    img.src = imageUrl
  })
}

export default useImageGeneration
