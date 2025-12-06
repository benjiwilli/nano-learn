/**
 * Canvas component for drawing annotations on images
 */

import React, { useRef, useEffect, useState, useCallback } from 'react'
import { 
  Circle, 
  Square, 
  ArrowRight, 
  Pencil, 
  Type, 
  Highlighter,
  Undo2,
  Redo2,
  Trash2
} from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../store'
import {
  setCurrentTool,
  setCurrentColor,
  addAnnotation,
  undo,
  redo,
  clearAnnotations,
  setIsDrawing,
} from '../store/slices/annotationSlice'
import { ToolType, Point, CanvasAnnotation, ANNOTATION_COLORS } from '../types/canvas.types'

interface AnnotationCanvasProps {
  imageUrl: string
}

const TOOLS: Array<{ id: ToolType; icon: React.ReactNode; label: string }> = [
  { id: 'circle', icon: <Circle className="w-5 h-5" />, label: 'Circle' },
  { id: 'rectangle', icon: <Square className="w-5 h-5" />, label: 'Rectangle' },
  { id: 'arrow', icon: <ArrowRight className="w-5 h-5" />, label: 'Arrow' },
  { id: 'freehand', icon: <Pencil className="w-5 h-5" />, label: 'Freehand' },
  { id: 'text', icon: <Type className="w-5 h-5" />, label: 'Text' },
  { id: 'highlight', icon: <Highlighter className="w-5 h-5" />, label: 'Highlight' },
]

const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({ imageUrl }) => {
  const dispatch = useAppDispatch()
  const { 
    annotations, 
    currentTool, 
    currentColor, 
    strokeWidth,
    historyIndex,
    history,
    isDrawing 
  } = useAppSelector((state) => state.annotation)

  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imageRef = useRef<HTMLImageElement | null>(null)
  
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 })
  const [startPoint, setStartPoint] = useState<Point | null>(null)
  const [currentPoints, setCurrentPoints] = useState<Point[]>([])
  const [textInput, setTextInput] = useState('')
  const [showTextInput, setShowTextInput] = useState(false)
  const [textPosition, setTextPosition] = useState<Point | null>(null)

  // Load and draw image
  useEffect(() => {
    const img = new Image()
    img.onload = () => {
      imageRef.current = img
      
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth
        const aspectRatio = img.height / img.width
        const height = containerWidth * aspectRatio
        
        setCanvasSize({
          width: containerWidth,
          height: Math.min(height, 600), // Max height
        })
      }
    }
    img.src = imageUrl
  }, [imageUrl])

  // Redraw canvas
  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    const img = imageRef.current
    
    if (!canvas || !ctx || !img) return

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    // Draw image
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    
    // Draw all annotations
    annotations.forEach((ann) => {
      drawAnnotation(ctx, ann, canvas.width, canvas.height)
    })
  }, [annotations])

  useEffect(() => {
    redrawCanvas()
  }, [redrawCanvas, canvasSize])

  const drawAnnotation = (
    ctx: CanvasRenderingContext2D,
    ann: CanvasAnnotation,
    width: number,
    height: number
  ) => {
    ctx.strokeStyle = ann.color
    ctx.fillStyle = ann.color
    ctx.lineWidth = ann.strokeWidth
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    const startX = ann.startPoint.x * width
    const startY = ann.startPoint.y * height

    switch (ann.type) {
      case 'circle':
        if (ann.endPoint) {
          const endX = ann.endPoint.x * width
          const endY = ann.endPoint.y * height
          const radius = Math.sqrt(
            Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2)
          )
          ctx.beginPath()
          ctx.arc(startX, startY, radius, 0, Math.PI * 2)
          ctx.stroke()
        }
        break

      case 'rectangle':
        if (ann.endPoint) {
          const rectWidth = (ann.endPoint.x - ann.startPoint.x) * width
          const rectHeight = (ann.endPoint.y - ann.startPoint.y) * height
          ctx.strokeRect(startX, startY, rectWidth, rectHeight)
        }
        break

      case 'arrow':
        if (ann.endPoint) {
          const endX = ann.endPoint.x * width
          const endY = ann.endPoint.y * height
          
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
          ctx.moveTo(endX, endY)
          ctx.lineTo(
            endX - headLen * Math.cos(angle + Math.PI / 6),
            endY - headLen * Math.sin(angle + Math.PI / 6)
          )
          ctx.stroke()
        }
        break

      case 'freehand':
        if (ann.points && ann.points.length > 1) {
          ctx.beginPath()
          ctx.moveTo(ann.points[0].x * width, ann.points[0].y * height)
          ann.points.forEach((point) => {
            ctx.lineTo(point.x * width, point.y * height)
          })
          ctx.stroke()
        }
        break

      case 'highlight':
        if (ann.endPoint) {
          ctx.globalAlpha = 0.3
          const rectWidth = (ann.endPoint.x - ann.startPoint.x) * width
          const rectHeight = (ann.endPoint.y - ann.startPoint.y) * height
          ctx.fillRect(startX, startY, rectWidth, rectHeight)
          ctx.globalAlpha = 1
        }
        break

      case 'text':
        if (ann.text) {
          ctx.font = 'bold 18px Arial'
          ctx.fillText(ann.text, startX, startY)
        }
        break
    }
  }

  const getCanvasPoint = (e: React.MouseEvent | React.TouchEvent): Point => {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    
    let clientX: number, clientY: number
    if ('touches' in e) {
      clientX = e.touches[0].clientX
      clientY = e.touches[0].clientY
    } else {
      clientX = e.clientX
      clientY = e.clientY
    }
    
    return {
      x: (clientX - rect.left) / rect.width,
      y: (clientY - rect.top) / rect.height,
    }
  }

  const handleMouseDown = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    const point = getCanvasPoint(e)
    
    if (currentTool === 'text') {
      setTextPosition(point)
      setShowTextInput(true)
      return
    }
    
    dispatch(setIsDrawing(true))
    setStartPoint(point)
    
    if (currentTool === 'freehand') {
      setCurrentPoints([point])
    }
  }

  const handleMouseMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing || !startPoint) return
    
    e.preventDefault()
    const point = getCanvasPoint(e)
    
    if (currentTool === 'freehand') {
      setCurrentPoints((prev) => [...prev, point])
    }
    
    // Preview drawing
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    
    redrawCanvas()
    
    // Draw preview
    ctx.strokeStyle = currentColor
    ctx.fillStyle = currentColor
    ctx.lineWidth = strokeWidth
    ctx.lineCap = 'round'
    
    const startX = startPoint.x * canvas.width
    const startY = startPoint.y * canvas.height
    const endX = point.x * canvas.width
    const endY = point.y * canvas.height
    
    switch (currentTool) {
      case 'circle':
        const radius = Math.sqrt(
          Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2)
        )
        ctx.beginPath()
        ctx.arc(startX, startY, radius, 0, Math.PI * 2)
        ctx.stroke()
        break
        
      case 'rectangle':
        ctx.strokeRect(startX, startY, endX - startX, endY - startY)
        break
        
      case 'arrow':
        ctx.beginPath()
        ctx.moveTo(startX, startY)
        ctx.lineTo(endX, endY)
        ctx.stroke()
        break
        
      case 'freehand':
        ctx.beginPath()
        ctx.moveTo(currentPoints[0].x * canvas.width, currentPoints[0].y * canvas.height)
        currentPoints.forEach((p) => {
          ctx.lineTo(p.x * canvas.width, p.y * canvas.height)
        })
        ctx.stroke()
        break
        
      case 'highlight':
        ctx.globalAlpha = 0.3
        ctx.fillRect(startX, startY, endX - startX, endY - startY)
        ctx.globalAlpha = 1
        break
    }
  }

  const handleMouseUp = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing || !startPoint) return
    
    const point = getCanvasPoint(e)
    
    const annotation: CanvasAnnotation = {
      id: `ann-${Date.now()}`,
      type: currentTool,
      startPoint,
      endPoint: point,
      color: currentColor,
      strokeWidth,
      points: currentTool === 'freehand' ? currentPoints : undefined,
    }
    
    dispatch(addAnnotation(annotation))
    dispatch(setIsDrawing(false))
    setStartPoint(null)
    setCurrentPoints([])
  }

  const handleTextSubmit = () => {
    if (textInput && textPosition) {
      const annotation: CanvasAnnotation = {
        id: `ann-${Date.now()}`,
        type: 'text',
        startPoint: textPosition,
        color: currentColor,
        strokeWidth,
        text: textInput,
      }
      dispatch(addAnnotation(annotation))
    }
    setShowTextInput(false)
    setTextInput('')
    setTextPosition(null)
  }

  const canUndo = historyIndex > 0
  const canRedo = historyIndex < history.length - 1

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 p-2 bg-gray-50 rounded-lg">
        {/* Tools */}
        <div className="flex gap-1 border-r border-gray-200 pr-2">
          {TOOLS.map((tool) => (
            <button
              key={tool.id}
              onClick={() => dispatch(setCurrentTool(tool.id))}
              className={`annotation-tool ${currentTool === tool.id ? 'active' : ''}`}
              title={tool.label}
            >
              {tool.icon}
            </button>
          ))}
        </div>
        
        {/* Colors */}
        <div className="flex gap-1 border-r border-gray-200 pr-2">
          {ANNOTATION_COLORS.slice(0, 6).map((color) => (
            <button
              key={color}
              onClick={() => dispatch(setCurrentColor(color))}
              className={`w-8 h-8 rounded-lg border-2 ${
                currentColor === color ? 'border-gray-800' : 'border-transparent'
              }`}
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
        </div>
        
        {/* Actions */}
        <div className="flex gap-1 ml-auto">
          <button
            onClick={() => dispatch(undo())}
            disabled={!canUndo}
            className="annotation-tool disabled:opacity-50"
            title="Undo"
          >
            <Undo2 className="w-5 h-5" />
          </button>
          <button
            onClick={() => dispatch(redo())}
            disabled={!canRedo}
            className="annotation-tool disabled:opacity-50"
            title="Redo"
          >
            <Redo2 className="w-5 h-5" />
          </button>
          <button
            onClick={() => dispatch(clearAnnotations())}
            className="annotation-tool text-red-600 hover:bg-red-50"
            title="Clear all"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      {/* Canvas */}
      <div 
        ref={containerRef}
        className="relative rounded-lg overflow-hidden border border-gray-200"
      >
        <canvas
          ref={canvasRef}
          width={canvasSize.width}
          height={canvasSize.height}
          className="cursor-crosshair touch-none"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleMouseDown}
          onTouchMove={handleMouseMove}
          onTouchEnd={handleMouseUp}
        />
        
        {/* Text input overlay */}
        {showTextInput && textPosition && (
          <div
            className="absolute"
            style={{
              left: `${textPosition.x * 100}%`,
              top: `${textPosition.y * 100}%`,
            }}
          >
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleTextSubmit()
                if (e.key === 'Escape') {
                  setShowTextInput(false)
                  setTextInput('')
                }
              }}
              onBlur={handleTextSubmit}
              autoFocus
              className="px-2 py-1 text-sm border border-gray-300 rounded shadow-lg"
              placeholder="Enter text..."
              style={{ color: currentColor }}
            />
          </div>
        )}
      </div>
      
      {/* Annotation count */}
      {annotations.length > 0 && (
        <p className="text-sm text-gray-500 text-center">
          {annotations.length} annotation{annotations.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}

export default AnnotationCanvas
