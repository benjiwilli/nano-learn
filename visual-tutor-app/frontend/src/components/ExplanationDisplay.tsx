/**
 * Enhanced Explanation Display component
 * 
 * Features:
 * - Side-by-side image comparison
 * - Fullscreen viewer
 * - Explanation history
 * - Feedback submission
 * - Export functionality
 * - Accessibility improvements
 */

import React, { useState, useCallback, useRef, useEffect } from 'react'
import {
  X,
  Download,
  Copy,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ThumbsUp,
  ThumbsDown,
  Clock,
  BookOpen,
  Lightbulb,
  Star,
  Share2,
  Minimize2,
  RefreshCw,
  MessageSquare
} from 'lucide-react'
import { useAppSelector, useAppDispatch } from '../store'
import { clearCurrentExplanation } from '../store/slices/explanationSlice'

interface FeedbackState {
  rating: number | null
  clarity: number | null
  helpfulness: number | null
  comment: string
  submitted: boolean
}

const ExplanationDisplay: React.FC = () => {
  const dispatch = useAppDispatch()
  const { currentExplanation, explanationHistory } = useAppSelector(
    (state) => state.explanation
  )

  const [showFullscreen, setShowFullscreen] = useState(false)
  const [fullscreenImage, setFullscreenImage] = useState<'original' | 'generated'>('generated')
  const [zoomLevel, setZoomLevel] = useState(1)
  const [showHistory, setShowHistory] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedback, setFeedback] = useState<FeedbackState>({
    rating: null,
    clarity: null,
    helpfulness: null,
    comment: '',
    submitted: false
  })
  const [copiedText, setCopiedText] = useState(false)

  const explanationRef = useRef<HTMLDivElement>(null)

  // Reset zoom when closing fullscreen
  useEffect(() => {
    if (!showFullscreen) {
      setZoomLevel(1)
    }
  }, [showFullscreen])

  const handleClear = useCallback(() => {
    dispatch(clearCurrentExplanation())
    setFeedback({
      rating: null,
      clarity: null,
      helpfulness: null,
      comment: '',
      submitted: false
    })
  }, [dispatch])

  const handleCopyExplanation = useCallback(async () => {
    if (currentExplanation?.explanation) {
      await navigator.clipboard.writeText(currentExplanation.explanation)
      setCopiedText(true)
      setTimeout(() => setCopiedText(false), 2000)
    }
  }, [currentExplanation])

  const handleDownloadImage = useCallback(async () => {
    if (!currentExplanation?.generatedImageUrl) return

    try {
      const response = await fetch(currentExplanation.generatedImageUrl)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `explanation-${currentExplanation.requestId}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download image:', error)
    }
  }, [currentExplanation])

  const handleZoom = useCallback((direction: 'in' | 'out') => {
    setZoomLevel((prev) => {
      const newLevel = direction === 'in' ? prev * 1.25 : prev / 1.25
      return Math.max(0.5, Math.min(3, newLevel))
    })
  }, [])

  const handleSubmitFeedback = useCallback(async () => {
    if (!currentExplanation?.requestId || !feedback.rating) return

    try {
      // In production, this would send to the API
      console.log('Submitting feedback:', {
        request_id: currentExplanation.requestId,
        ...feedback
      })
      setFeedback((prev) => ({ ...prev, submitted: true }))
      setTimeout(() => setShowFeedback(false), 1500)
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }, [currentExplanation, feedback])

  const handleShare = useCallback(async () => {
    if (!currentExplanation) return

    const shareData = {
      title: 'Visual Tutor Explanation',
      text: currentExplanation.explanation.substring(0, 200) + '...',
      url: window.location.href
    }

    try {
      if (navigator.share) {
        await navigator.share(shareData)
      } else {
        await navigator.clipboard.writeText(currentExplanation.explanation)
        alert('Explanation copied to clipboard!')
      }
    } catch (error) {
      console.error('Failed to share:', error)
    }
  }, [currentExplanation])

  if (!currentExplanation) {
    return null
  }

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <>
      {/* Main Explanation Card */}
      <div className="card space-y-4" ref={explanationRef}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20">
              <Lightbulb className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Your Visual Explanation</h2>
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                <span>Generated in {formatTime(currentExplanation.generationTimeMs)}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
              title="View history"
              aria-label="View explanation history"
            >
              <BookOpen className="w-5 h-5" />
            </button>
            <button
              onClick={handleShare}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
              title="Share"
              aria-label="Share explanation"
            >
              <Share2 className="w-5 h-5" />
            </button>
            <button
              onClick={handleClear}
              className="p-2 text-gray-500 hover:text-red-600 rounded-lg hover:bg-red-50"
              title="Close"
              aria-label="Close explanation"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Concept Badge */}
        {currentExplanation.confusionAnalysis?.confusion_concept && (
          <div className="flex flex-wrap gap-2">
            <span className="px-3 py-1 bg-primary-50 text-primary-700 border border-primary-100 rounded-lg text-xs font-bold uppercase tracking-wide">
              {currentExplanation.confusionAnalysis.confusion_concept}
            </span>
            <span className="px-3 py-1 bg-secondary-50 text-secondary-700 border border-secondary-100 rounded-lg text-xs font-bold uppercase tracking-wide">
              {currentExplanation.confusionAnalysis.subject}
            </span>
            <span className="px-3 py-1 bg-slate-50 text-slate-600 border border-slate-100 rounded-lg text-xs font-bold uppercase tracking-wide">
              {currentExplanation.confusionAnalysis.difficulty_level}
            </span>
          </div>
        )}

        {/* Image Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Original Image */}
          {currentExplanation.originalImageUrl && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-700">Your Image</h3>
                <button
                  onClick={() => {
                    setFullscreenImage('original')
                    setShowFullscreen(true)
                  }}
                  className="p-1.5 text-gray-400 hover:text-gray-600 rounded"
                  aria-label="View original image fullscreen"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>
              <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-50 shadow-inner">
                <img
                  src={currentExplanation.originalImageUrl}
                  alt="Original image"
                  className="w-full h-48 object-contain p-2"
                  loading="lazy"
                />
              </div>
            </div>
          )}

          {/* Generated Image */}
          {currentExplanation.generatedImageUrl && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-700">Generated Explanation</h3>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleDownloadImage}
                    className="p-1.5 text-gray-400 hover:text-gray-600 rounded"
                    aria-label="Download generated image"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      setFullscreenImage('generated')
                      setShowFullscreen(true)
                    }}
                    className="p-1.5 text-gray-400 hover:text-gray-600 rounded"
                    aria-label="View generated image fullscreen"
                  >
                    <Maximize2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="relative rounded-xl overflow-hidden border-2 border-primary-200 bg-primary-50/30 shadow-sm">
                <img
                  src={currentExplanation.generatedImageUrl}
                  alt="AI-generated explanation diagram"
                  className="w-full h-48 object-contain p-2"
                  loading="lazy"
                />
                <div className="absolute top-2 left-2 px-2.5 py-1 bg-primary-600 text-white text-[10px] font-bold uppercase tracking-wider rounded-md shadow-sm">
                  AI Generated
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Explanation Text */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-700">Explanation</h3>
            <button
              onClick={handleCopyExplanation}
              className="flex items-center gap-1 px-2 py-1 text-sm text-gray-500 hover:text-gray-700 rounded hover:bg-gray-100"
              aria-label="Copy explanation text"
            >
              <Copy className="w-3.5 h-3.5" />
              {copiedText ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <div className="p-5 bg-slate-50 rounded-xl border border-slate-100 text-slate-700 leading-relaxed whitespace-pre-wrap">
            <p>
              {currentExplanation.explanation}
            </p>
          </div>
        </div>

        {/* Feedback Section */}
        {!feedback.submitted ? (
          <div className="border-t border-gray-200 pt-4">
            <button
              onClick={() => setShowFeedback(!showFeedback)}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800"
            >
              <MessageSquare className="w-4 h-4" />
              Was this explanation helpful?
            </button>
            
            {showFeedback && (
              <div className="mt-4 space-y-4 animate-fadeIn">
                {/* Rating */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Overall Rating
                  </label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => setFeedback((prev) => ({ ...prev, rating: star }))}
                        className={`p-1 rounded ${
                          feedback.rating && feedback.rating >= star
                            ? 'text-yellow-400'
                            : 'text-gray-300 hover:text-yellow-400'
                        }`}
                        aria-label={`Rate ${star} stars`}
                      >
                        <Star className="w-6 h-6 fill-current" />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Quick feedback buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={() => setFeedback((prev) => ({ ...prev, clarity: 5, helpfulness: 5 }))}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                      feedback.clarity === 5
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-gray-200 hover:border-green-300 hover:bg-green-50'
                    }`}
                  >
                    <ThumbsUp className="w-4 h-4" />
                    Very helpful
                  </button>
                  <button
                    onClick={() => setFeedback((prev) => ({ ...prev, clarity: 2, helpfulness: 2 }))}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                      feedback.clarity === 2
                        ? 'border-red-500 bg-red-50 text-red-700'
                        : 'border-gray-200 hover:border-red-300 hover:bg-red-50'
                    }`}
                  >
                    <ThumbsDown className="w-4 h-4" />
                    Not helpful
                  </button>
                </div>

                {/* Comment */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Additional comments (optional)
                  </label>
                  <textarea
                    value={feedback.comment}
                    onChange={(e) => setFeedback((prev) => ({ ...prev, comment: e.target.value }))}
                    className="input min-h-[80px] resize-none"
                    placeholder="What could be improved?"
                    maxLength={500}
                  />
                </div>

                {/* Submit */}
                <button
                  onClick={handleSubmitFeedback}
                  disabled={!feedback.rating}
                  className="btn btn-primary w-full"
                >
                  Submit Feedback
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="border-t border-gray-200 pt-4 text-center text-green-600">
            <div className="flex items-center justify-center gap-2">
              <ThumbsUp className="w-5 h-5" />
              Thank you for your feedback!
            </div>
          </div>
        )}
      </div>

      {/* History Panel */}
      {showHistory && explanationHistory.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Recent Explanations</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {explanationHistory.slice(0, 5).map((item) => (
              <div
                key={item.requestId}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  item.requestId === currentExplanation?.requestId
                    ? 'border-purple-300 bg-purple-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-800 text-sm">
                    {item.confusionAnalysis?.confusion_concept || 'Explanation'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {item.explanation.substring(0, 100)}...
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fullscreen Modal */}
      {showFullscreen && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={() => setShowFullscreen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Fullscreen image viewer"
        >
          <div
            className="relative max-w-full max-h-full p-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Controls */}
            <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
              <button
                onClick={() => handleZoom('out')}
                className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white"
                aria-label="Zoom out"
              >
                <ZoomOut className="w-5 h-5" />
              </button>
              <span className="px-2 text-white text-sm">
                {Math.round(zoomLevel * 100)}%
              </span>
              <button
                onClick={() => handleZoom('in')}
                className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white"
                aria-label="Zoom in"
              >
                <ZoomIn className="w-5 h-5" />
              </button>
              <button
                onClick={() => setZoomLevel(1)}
                className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white"
                aria-label="Reset zoom"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
              <button
                onClick={() => setShowFullscreen(false)}
                className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white"
                aria-label="Close fullscreen"
              >
                <Minimize2 className="w-5 h-5" />
              </button>
            </div>

            {/* Image switcher */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-4 z-10">
              {currentExplanation?.originalImageUrl && (
                <button
                  onClick={() => setFullscreenImage('original')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    fullscreenImage === 'original'
                      ? 'bg-white text-gray-900'
                      : 'bg-white/10 text-white hover:bg-white/20'
                  }`}
                >
                  Original
                </button>
              )}
              {currentExplanation?.generatedImageUrl && (
                <button
                  onClick={() => setFullscreenImage('generated')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    fullscreenImage === 'generated'
                      ? 'bg-white text-gray-900'
                      : 'bg-white/10 text-white hover:bg-white/20'
                  }`}
                >
                  Generated
                </button>
              )}
            </div>

            {/* Image */}
            <div className="overflow-auto max-h-[80vh] max-w-[90vw]">
              <img
                src={
                  fullscreenImage === 'original'
                    ? currentExplanation?.originalImageUrl
                    : currentExplanation?.generatedImageUrl
                }
                alt={fullscreenImage === 'original' ? 'Original image' : 'Generated explanation'}
                style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center' }}
                className="transition-transform duration-200"
              />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default ExplanationDisplay
