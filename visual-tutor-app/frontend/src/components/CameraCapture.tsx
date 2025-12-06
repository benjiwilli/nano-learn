/**
 * Camera capture component for snap-and-explain mode
 */

import React, { useState, useRef, useCallback } from 'react'
import { 
  Camera, 
  Upload, 
  X, 
  Sparkles,
  ImageIcon,
  RefreshCw 
} from 'lucide-react'
import { useCamera } from '../hooks/useCamera'
import { useImageGeneration } from '../hooks/useImageGeneration'
import { useAppDispatch, useAppSelector } from '../store'
import { setCapturedImage, resetAnnotations } from '../store/slices/annotationSlice'
import AnnotationCanvas from './AnnotationCanvas'

const CameraCapture: React.FC = () => {
  const dispatch = useAppDispatch()
  const { capturedImage, annotations } = useAppSelector((state) => state.annotation)
  
  const [showCamera, setShowCamera] = useState(false)
  const [question, setQuestion] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const {
    videoRef,
    canvasRef,
    isStreaming,
    error: cameraError,
    startCamera,
    stopCamera,
    captureImage,
    switchCamera,
  } = useCamera()
  
  const { isLoading, error: genError, generateExplanation } = useImageGeneration({
    onSuccess: () => {
      setQuestion('')
    },
  })

  const handleStartCamera = useCallback(async () => {
    setShowCamera(true)
    await startCamera()
  }, [startCamera])

  const handleStopCamera = useCallback(() => {
    stopCamera()
    setShowCamera(false)
  }, [stopCamera])

  const handleCapture = useCallback(() => {
    const image = captureImage()
    if (image) {
      dispatch(setCapturedImage(image))
      handleStopCamera()
    }
  }, [captureImage, dispatch, handleStopCamera])

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const result = e.target?.result as string
        dispatch(setCapturedImage(result))
      }
      reader.readAsDataURL(file)
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [dispatch])

  const handleClearImage = useCallback(() => {
    dispatch(resetAnnotations())
  }, [dispatch])

  const handleSubmit = useCallback(async () => {
    if (!capturedImage) return
    
    await generateExplanation(
      capturedImage,
      annotations,
      question || undefined
    )
  }, [capturedImage, annotations, question, generateExplanation])

  // Camera view
  if (showCamera) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Camera</h2>
          <button
            onClick={handleStopCamera}
            className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="relative rounded-xl overflow-hidden bg-black">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-auto"
          />
          <canvas ref={canvasRef} className="hidden" />
          
          {cameraError && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/80">
              <p className="text-red-400 text-center px-4">{cameraError}</p>
            </div>
          )}
        </div>
        
        <div className="flex justify-center gap-4 mt-4">
          <button
            onClick={switchCamera}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Switch
          </button>
          <button
            onClick={handleCapture}
            disabled={!isStreaming}
            className="btn btn-primary flex items-center gap-2 px-8"
          >
            <Camera className="w-5 h-5" />
            Capture
          </button>
        </div>
      </div>
    )
  }

  // Image captured - show annotation canvas
  if (capturedImage) {
    return (
      <div className="space-y-4">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Annotate Your Image</h2>
            <button
              onClick={handleClearImage}
              className="p-2 text-gray-500 hover:text-red-600 rounded-lg hover:bg-red-50"
              title="Remove image"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <AnnotationCanvas imageUrl={capturedImage} />
          
          <p className="text-sm text-gray-500 mt-3">
            Draw circles, arrows, or text to highlight what confuses you
          </p>
        </div>
        
        {/* Question input */}
        <div className="card">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ask a question (optional)
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., How does this pulley system reduce the force needed?"
            className="input min-h-[80px] resize-none"
            rows={3}
          />
        </div>
        
        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={isLoading}
          className="w-full btn btn-primary flex items-center justify-center gap-2 py-3 text-lg"
        >
          {isLoading ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Generating Explanation...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Get Visual Explanation
            </>
          )}
        </button>
        
        {genError && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {genError}
          </div>
        )}
      </div>
    )
  }

  // Initial state - show capture options
  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Capture an Image</h2>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Camera option */}
        <button
          onClick={handleStartCamera}
          className="flex flex-col items-center gap-3 p-8 border-2 border-dashed border-primary-200 rounded-2xl hover:border-primary-400 hover:bg-primary-50 transition-all duration-300 group"
        >
          <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-sm">
            <Camera className="w-8 h-8 text-primary-600" />
          </div>
          <div className="text-center">
            <p className="font-bold text-slate-900 text-lg">Use Camera</p>
            <p className="text-sm text-slate-500">Take a photo of your study material</p>
          </div>
        </button>
        
        {/* Upload option */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center gap-3 p-8 border-2 border-dashed border-secondary-200 rounded-2xl hover:border-secondary-400 hover:bg-secondary-50 transition-all duration-300 group"
        >
          <div className="w-16 h-16 bg-secondary-100 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-sm">
            <Upload className="w-8 h-8 text-secondary-600" />
          </div>
          <div className="text-center">
            <p className="font-bold text-slate-900 text-lg">Upload Image</p>
            <p className="text-sm text-slate-500">Choose from your device</p>
          </div>
        </button>
        
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="hidden"
        />
      </div>
      
      {/* Sample images hint */}
      <div className="mt-8 p-6 bg-slate-50 border border-slate-100 rounded-xl">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-white rounded-lg shadow-sm">
            <ImageIcon className="w-6 h-6 text-primary-400" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900 mb-2">What works best?</p>
            <ul className="text-sm text-slate-600 space-y-2 grid grid-cols-1 sm:grid-cols-2 gap-x-4">
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary-400"></div>Textbook pages with diagrams</li>
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary-400"></div>Whiteboard notes</li>
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary-400"></div>Homework problems</li>
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary-400"></div>Scientific charts and graphs</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CameraCapture
