/**
 * Step-by-Step Explanation Component
 * 
 * Features:
 * - Progressive disclosure of steps
 * - Step navigation
 * - Visual indicators for progress
 * - Expandable step details
 * - Accessibility support
 */

import React, { useState, useCallback, useEffect, useRef } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  RotateCcw,
  BookOpen,
  Lightbulb,
  CheckCircle2,
  Loader2
} from 'lucide-react'
import { api } from '../services/api'

interface Step {
  step_number: number
  title: string
  explanation: string
  visual_description: string
}

interface StepByStepExplanationProps {
  concept?: string
  subject?: string
  difficulty?: string
  onComplete?: () => void
}

const StepByStepExplanation: React.FC<StepByStepExplanationProps> = ({
  concept: initialConcept,
  subject: initialSubject = 'general',
  difficulty: initialDifficulty = 'intermediate',
  onComplete
}) => {
  const [concept, setConcept] = useState(initialConcept || '')
  const [subject, setSubject] = useState(initialSubject)
  const [difficulty, setDifficulty] = useState(initialDifficulty)
  
  const [steps, setSteps] = useState<Step[]>([])
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [overviewImageUrl, setOverviewImageUrl] = useState<string>('')
  
  const [isAutoPlaying, setIsAutoPlaying] = useState(false)
  const [autoPlayInterval, setAutoPlayInterval] = useState<ReturnType<typeof setInterval> | null>(null)
  
  const stepRef = useRef<HTMLDivElement>(null)

  // Auto-play functionality
  useEffect(() => {
    if (isAutoPlaying && steps.length > 0) {
      const interval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= steps.length - 1) {
            setIsAutoPlaying(false)
            return prev
          }
          return prev + 1
        })
      }, 5000) // 5 seconds per step
      
      setAutoPlayInterval(interval)
      
      return () => clearInterval(interval)
    } else if (autoPlayInterval) {
      clearInterval(autoPlayInterval)
      setAutoPlayInterval(null)
    }
  }, [isAutoPlaying, steps.length])

  // Mark step as completed when viewed
  useEffect(() => {
    if (steps.length > 0) {
      setCompletedSteps((prev) => new Set([...prev, currentStep]))
    }
  }, [currentStep, steps.length])

  // Scroll to current step
  useEffect(() => {
    if (stepRef.current) {
      stepRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [currentStep])

  const handleGenerate = useCallback(async () => {
    if (!concept.trim()) {
      setError('Please enter a concept to explain')
      return
    }

    setIsLoading(true)
    setError(null)
    setSteps([])
    setCurrentStep(0)
    setCompletedSteps(new Set())

    try {
      const response = await api.post('/explain/step-by-step', {
        concept: concept.trim(),
        subject,
        difficulty
      })

      if (response.data.steps && response.data.steps.length > 0) {
        setSteps(response.data.steps)
        setOverviewImageUrl(response.data.overview_image_url || '')
      } else {
        setError('No steps were generated. Try a different concept.')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate explanation')
    } finally {
      setIsLoading(false)
    }
  }, [concept, subject, difficulty])

  const handleNext = useCallback(() => {
    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1)
    } else if (onComplete) {
      onComplete()
    }
  }, [currentStep, steps.length, onComplete])

  const handlePrevious = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1)
    }
  }, [currentStep])

  const handleReset = useCallback(() => {
    setCurrentStep(0)
    setCompletedSteps(new Set())
    setIsAutoPlaying(false)
  }, [])

  const handleStepClick = useCallback((index: number) => {
    setCurrentStep(index)
    setIsAutoPlaying(false)
  }, [])

  const progress = steps.length > 0 ? ((currentStep + 1) / steps.length) * 100 : 0

  // Input form when no steps
  if (steps.length === 0 && !isLoading) {
    return (
      <div className="card">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-teal-500 rounded-full flex items-center justify-center">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Step-by-Step Explanation</h2>
            <p className="text-sm text-gray-500">Break down any concept into digestible steps</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Concept input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              What concept would you like explained?
            </label>
            <input
              type="text"
              value={concept}
              onChange={(e) => setConcept(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              placeholder="e.g., How photosynthesis works"
              className="input"
            />
          </div>

          {/* Subject and Difficulty */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subject
              </label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="input"
              >
                <option value="general">General</option>
                <option value="math">Mathematics</option>
                <option value="physics">Physics</option>
                <option value="chemistry">Chemistry</option>
                <option value="biology">Biology</option>
                <option value="history">History</option>
                <option value="geography">Geography</option>
                <option value="computer_science">Computer Science</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="input"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={!concept.trim() || isLoading}
            className="btn btn-primary w-full flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating Steps...
              </>
            ) : (
              <>
                <Lightbulb className="w-5 h-5" />
                Generate Step-by-Step Explanation
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="card">
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Creating Your Lesson</h3>
          <p className="text-gray-500 text-center">
            Breaking down "{concept}" into easy-to-follow steps...
          </p>
        </div>
      </div>
    )
  }

  // Steps view
  const currentStepData = steps[currentStep]

  return (
    <div className="space-y-4">
      {/* Progress Header */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{concept}</h2>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span className="px-2 py-0.5 bg-gray-100 rounded">{subject}</span>
              <span className="px-2 py-0.5 bg-gray-100 rounded">{difficulty}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsAutoPlaying(!isAutoPlaying)}
              className={`p-2 rounded-lg ${
                isAutoPlaying
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={isAutoPlaying ? 'Pause auto-play' : 'Auto-play steps'}
            >
              {isAutoPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            </button>
            <button
              onClick={handleReset}
              className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
              title="Reset"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex justify-between text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
            <span>Progress</span>
            <span>Step {currentStep + 1} of {steps.length}</span>
          </div>
          <div className="h-3 bg-slate-100 rounded-full overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-secondary-400 to-secondary-600 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-2 flex-wrap">
          {steps.map((step, index) => (
            <button
              key={step.step_number}
              onClick={() => handleStepClick(index)}
              className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 ${
                index === currentStep
                  ? 'bg-secondary-500 text-white scale-110 shadow-lg shadow-secondary-500/40 font-bold'
                  : completedSteps.has(index)
                  ? 'bg-green-100 text-green-600 hover:bg-green-200'
                  : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
              }`}
              title={step.title}
            >
              {completedSteps.has(index) && index !== currentStep ? (
                <CheckCircle2 className="w-5 h-5" />
              ) : (
                <span className="text-sm">{index + 1}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Current Step Content */}
      <div className="card" ref={stepRef}>
        <div className="flex items-start gap-5">
          <div className="flex-shrink-0 w-14 h-14 bg-gradient-to-br from-secondary-400 to-secondary-600 rounded-2xl flex items-center justify-center text-white font-bold text-2xl shadow-lg shadow-secondary-500/20">
            {currentStep + 1}
          </div>
          <div className="flex-1">
            <h3 className="text-2xl font-bold text-slate-900 mb-3">
              {currentStepData.title}
            </h3>
            <p className="text-slate-700 leading-relaxed mb-6 text-lg">
              {currentStepData.explanation}
            </p>
            
            {/* Visual description */}
            {currentStepData.visual_description && (
              <div className="p-5 bg-primary-50/50 rounded-xl border border-primary-100/50 backdrop-blur-sm">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-white rounded-lg shadow-sm">
                    <Lightbulb className="w-5 h-5 text-primary-500" />
                  </div>
                  <div>
                    <span className="text-sm font-bold text-primary-700 uppercase tracking-wide">Visualize this</span>
                    <p className="text-primary-800 mt-1 leading-relaxed">
                      {currentStepData.visual_description}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={handlePrevious}
          disabled={currentStep === 0}
          className="btn btn-secondary flex items-center gap-2 disabled:opacity-50"
        >
          <ChevronLeft className="w-5 h-5" />
          Previous
        </button>

        <div className="text-sm text-gray-500">
          {completedSteps.size} of {steps.length} steps completed
        </div>

        <button
          onClick={handleNext}
          className="btn btn-primary flex items-center gap-2"
        >
          {currentStep === steps.length - 1 ? (
            <>
              Complete
              <CheckCircle2 className="w-5 h-5" />
            </>
          ) : (
            <>
              Next
              <ChevronRight className="w-5 h-5" />
            </>
          )}
        </button>
      </div>

      {/* Overview image */}
      {overviewImageUrl && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-3">Overview Diagram</h3>
          <div className="rounded-lg overflow-hidden border border-gray-200">
            <img
              src={overviewImageUrl}
              alt={`Overview diagram for ${concept}`}
              className="w-full h-auto"
              loading="lazy"
            />
          </div>
        </div>
      )}

      {/* New concept button */}
      <button
        onClick={() => {
          setSteps([])
          setConcept('')
          setOverviewImageUrl('')
        }}
        className="w-full text-center text-sm text-gray-500 hover:text-gray-700 py-2"
      >
        Explain a different concept
      </button>
    </div>
  )
}

export default StepByStepExplanation
