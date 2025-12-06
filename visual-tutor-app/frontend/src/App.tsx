/**
 * Visual Tutor App - Main Application Component
 * 
 * An AI-powered educational application that provides visual
 * explanations for student questions using Gemini and Nano Banana Pro.
 */

import React, { useState, useCallback } from 'react'
import { 
  Camera, 
  Video, 
  BookOpen, 
  Sparkles, 
  ListOrdered, 
  Lightbulb,
  HelpCircle,
  Moon,
  Sun
} from 'lucide-react'
import CameraCapture from './components/CameraCapture'
import LiveLens from './components/LiveLens'
import ExplanationDisplay from './components/ExplanationDisplay'
import ChatInterface from './components/ChatInterface'
import StepByStepExplanation from './components/StepByStepExplanation'
import { useAppSelector } from './store'

type Mode = 'snap' | 'live' | 'step-by-step'

function App() {
  const [mode, setMode] = useState<Mode>('snap')
  const [showHelp, setShowHelp] = useState(false)
  const [darkMode, setDarkMode] = useState(false)
  
  const { currentExplanation, isLoading } = useAppSelector((state) => state.explanation)

  const handleModeChange = useCallback((newMode: Mode) => {
    setMode(newMode)
  }, [])

  return (
    <div className={`min-h-screen transition-colors ${
      darkMode 
        ? 'bg-gray-900 text-white' 
        : ''
    }`}>
      {/* Header */}
      <header className={`sticky top-0 z-50 backdrop-blur-lg border-b ${
        darkMode 
          ? 'bg-gray-900/80 border-gray-800' 
          : 'bg-white/70 border-white/50'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <div className="flex items-center space-x-3 group cursor-pointer">
              <div className="bg-gradient-to-br from-primary-500 to-primary-700 p-2.5 rounded-xl shadow-lg shadow-primary-500/30 group-hover:scale-105 transition-transform duration-300">
                <BookOpen className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className={`text-xl font-bold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                  Visual Tutor
                </h1>
                <p className={`text-xs font-medium ${darkMode ? 'text-gray-400' : 'text-slate-500'}`}>
                  AI-Powered Learning Assistant
                </p>
              </div>
            </div>
            
            {/* Mode Toggle */}
            <div className={`hidden md:flex ${darkMode ? 'bg-gray-800' : 'bg-white/60 border border-white/60'} backdrop-blur-sm rounded-xl p-1.5 shadow-sm`}>
              <ModeButton
                active={mode === 'snap'}
                onClick={() => handleModeChange('snap')}
                icon={<Camera className="w-4 h-4" />}
                label="Snap & Explain"
                darkMode={darkMode}
              />
              <ModeButton
                active={mode === 'live'}
                onClick={() => handleModeChange('live')}
                icon={<Video className="w-4 h-4" />}
                label="Live Lens"
                darkMode={darkMode}
              />
              <ModeButton
                active={mode === 'step-by-step'}
                onClick={() => handleModeChange('step-by-step')}
                icon={<ListOrdered className="w-4 h-4" />}
                label="Step by Step"
                darkMode={darkMode}
              />
            </div>

            {/* Settings */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setDarkMode(!darkMode)}
                className={`p-2 rounded-lg ${
                  darkMode 
                    ? 'text-gray-400 hover:text-white hover:bg-gray-700' 
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
                title={darkMode ? 'Light mode' : 'Dark mode'}
                aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
              <button
                onClick={() => setShowHelp(true)}
                className={`p-2 rounded-lg ${
                  darkMode 
                    ? 'text-gray-400 hover:text-white hover:bg-gray-700' 
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
                title="Help"
                aria-label="Help"
              >
                <HelpCircle className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Introduction Banner */}
        {!currentExplanation && !isLoading && mode !== 'step-by-step' && (
          <IntroductionBanner mode={mode} />
        )}

        {/* Content based on mode */}
        {mode === 'step-by-step' ? (
          <StepByStepExplanation />
        ) : (
          /* Content Grid */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Panel - Camera/Input */}
            <div className="space-y-6">
              {mode === 'snap' ? <CameraCapture /> : <LiveLens />}
            </div>

            {/* Right Panel - Explanation/Chat */}
            <div className="space-y-6">
              {currentExplanation ? (
                <ExplanationDisplay />
              ) : (
                <EmptyStateCard mode={mode} darkMode={darkMode} />
              )}
              
              {/* Chat Interface */}
              <ChatInterface />
            </div>
          </div>
        )}

        {/* Features Section */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-4 gap-6">
          <FeatureCard
            icon={<Camera className="w-6 h-6" />}
            title="Smart Annotation"
            description="Circle, arrow, or highlight any part of your study material."
            darkMode={darkMode}
          />
          <FeatureCard
            icon={<Sparkles className="w-6 h-6" />}
            title="Visual Explanations"
            description="AI generates custom diagrams tailored to your confusion."
            darkMode={darkMode}
          />
          <FeatureCard
            icon={<Video className="w-6 h-6" />}
            title="Real-Time Help"
            description="Get instant assistance with live camera mode."
            darkMode={darkMode}
          />
          <FeatureCard
            icon={<ListOrdered className="w-6 h-6" />}
            title="Step-by-Step"
            description="Break down complex concepts into digestible steps."
            darkMode={darkMode}
          />
        </div>

        {/* Quick Tips */}
        <QuickTips darkMode={darkMode} mode={mode} />
      </main>

      {/* Footer */}
      <footer className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-t mt-16`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Powered by Gemini 3.0 Pro & Nano Banana Pro
            </p>
            <div className="flex items-center gap-4">
              <a href="/docs" className={`text-sm ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
                API Docs
              </a>
              <a href="#" className={`text-sm ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
                Privacy
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* Help Modal */}
      {showHelp && (
        <HelpModal onClose={() => setShowHelp(false)} />
      )}
    </div>
  )
}

// Sub-components

function ModeButton({ 
  active, 
  onClick, 
  icon, 
  label,
  darkMode 
}: { 
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
  darkMode: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center space-x-2 px-5 py-2.5 rounded-lg transition-all duration-200 ${
        active
          ? `${darkMode ? 'bg-gray-700 text-white' : 'bg-white text-primary-600 shadow-sm ring-1 ring-black/5'}`
          : `${darkMode ? 'text-gray-400 hover:text-white hover:bg-gray-700/50' : 'text-slate-500 hover:text-slate-900 hover:bg-white/50'}`
      }`}
    >
      {icon}
      <span className={`font-medium text-sm hidden sm:inline ${active ? 'font-semibold' : ''}`}>{label}</span>
    </button>
  )
}

function IntroductionBanner({ mode }: { mode: Mode }) {
  const content = {
    snap: {
      title: 'Snap a Photo, Get an Explanation',
      description: 'Take a photo of any confusing diagram, textbook page, or problem. Circle what confuses you, and our AI will generate a custom visual explanation just for you.'
    },
    live: {
      title: 'Real-Time Visual Learning',
      description: 'Point your camera at study material and get real-time AI assistance. Just ask questions naturally, and Visual Tutor will create diagrams on the fly.'
    },
    'step-by-step': {
      title: 'Learn Step by Step',
      description: 'Enter any concept and get a structured breakdown into easy-to-follow steps with visual explanations.'
    }
  }

  return (
    <div className="mb-10 relative overflow-hidden rounded-3xl shadow-xl group">
      <div className="absolute inset-0 bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-500 opacity-100 transition-opacity duration-500"></div>
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-soft-light"></div>
      <div className="relative p-8 text-white flex items-start gap-6">
        <div className="bg-white/20 backdrop-blur-md p-4 rounded-2xl shadow-inner border border-white/20 group-hover:scale-110 transition-transform duration-300">
          <Sparkles className="w-8 h-8 text-yellow-200" />
        </div>
        <div className="flex-1">
          <h2 className="text-3xl font-bold mb-3 tracking-tight">{content[mode].title}</h2>
          <p className="text-blue-50 text-lg leading-relaxed max-w-3xl font-light">{content[mode].description}</p>
        </div>
      </div>
    </div>
  )
}

function EmptyStateCard({ mode, darkMode }: { mode: Mode; darkMode: boolean }) {
  return (
    <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl shadow-lg p-8 text-center`}>
      <div className={`w-16 h-16 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'} rounded-full flex items-center justify-center mx-auto mb-4`}>
        <BookOpen className={`w-8 h-8 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`} />
      </div>
      <h3 className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-700'} mb-2`}>
        Your Explanation Will Appear Here
      </h3>
      <p className={darkMode ? 'text-gray-400' : 'text-gray-500'}>
        {mode === 'snap'
          ? 'Capture an image and add annotations to get started'
          : 'Start the live session and ask a question'}
      </p>
    </div>
  )
}

function FeatureCard({ 
  icon, 
  title, 
  description,
  darkMode
}: { 
  icon: React.ReactNode
  title: string
  description: string
  darkMode: boolean
}) {
  return (
    <div className={`${
      darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white/60 backdrop-blur-sm border-white/60'
    } rounded-2xl p-6 shadow-soft border hover:shadow-lg hover:-translate-y-1 transition-all duration-300 group`}>
      <div className={`${darkMode ? 'bg-gray-700 text-primary-400' : 'bg-primary-50 text-primary-600'} w-14 h-14 rounded-xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300`}>
        {icon}
      </div>
      <h3 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-slate-900'} mb-3`}>{title}</h3>
      <p className={`${darkMode ? 'text-gray-400' : 'text-slate-600'} text-sm leading-relaxed`}>{description}</p>
    </div>
  )
}

function QuickTips({ darkMode, mode }: { darkMode: boolean; mode: Mode }) {
  const tips = {
    snap: [
      'Use circles to highlight confusing areas',
      'Add text annotations for specific questions',
      'Arrows can show relationships you want explained'
    ],
    live: [
      'Speak naturally to ask questions',
      'Hold the camera steady for better analysis',
      'Request visual explanations anytime'
    ],
    'step-by-step': [
      'Be specific about the concept you want explained',
      'Choose the right difficulty level for your understanding',
      'Use the auto-play feature to learn at your pace'
    ]
  }

  return (
    <div className={`mt-16 ${darkMode ? 'bg-gray-800/50 border-gray-700' : 'bg-white/40 border-white/50'} border backdrop-blur-sm rounded-2xl p-8`}>
      <div className="flex items-center gap-3 mb-6">
        <div className={`p-2 rounded-lg ${darkMode ? 'bg-yellow-900/30' : 'bg-yellow-50'}`}>
          <Lightbulb className={`w-6 h-6 ${darkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
        </div>
        <h3 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>Quick Tips</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tips[mode].map((tip, index) => (
          <div key={index} className={`flex items-start gap-3 ${darkMode ? 'text-gray-300' : 'text-slate-600'} text-sm p-4 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white/50'} shadow-sm`}>
            <span className="text-primary-500 font-bold text-lg leading-none">•</span>
            {tip}
          </div>
        ))}
      </div>
    </div>
  )
}

function HelpModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div 
        className="bg-white rounded-2xl p-6 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">How to Use Visual Tutor</h2>
          <button 
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100"
          >
            ✕
          </button>
        </div>

        <div className="space-y-6">
          <div>
            <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
              <Camera className="w-5 h-5 text-blue-500" /> Snap & Explain
            </h3>
            <p className="text-sm text-gray-600">
              1. Take a photo or upload an image of your study material<br/>
              2. Use annotation tools to circle confusing areas<br/>
              3. Optionally add a question<br/>
              4. Click "Get Visual Explanation"
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
              <Video className="w-5 h-5 text-blue-500" /> Live Lens
            </h3>
            <p className="text-sm text-gray-600">
              1. Start a live session<br/>
              2. Point your camera at study material<br/>
              3. Ask questions in the chat<br/>
              4. Request visual explanations on demand
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
              <ListOrdered className="w-5 h-5 text-blue-500" /> Step by Step
            </h3>
            <p className="text-sm text-gray-600">
              1. Enter a concept you want to understand<br/>
              2. Select subject and difficulty level<br/>
              3. Navigate through steps at your own pace<br/>
              4. Use auto-play for guided learning
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="mt-6 w-full btn btn-primary"
        >
          Got it!
        </button>
      </div>
    </div>
  )
}

export default App
