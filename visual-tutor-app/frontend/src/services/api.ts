/**
 * API service for Visual Tutor backend communication
 */

import axios, { AxiosInstance, AxiosError } from 'axios'
import {
  SnapAndExplainRequest,
  SnapAndExplainResponse,
  HealthCheckResponse,
  SubjectInfo,
  StyleInfo,
  ErrorResponse,
} from '../types/api.types'

// API configuration - handle sandbox environment
function getApiBaseUrl(): string {
  // Check for explicit environment variable
  const envUrl = (import.meta as any).env?.VITE_API_BASE_URL
  if (envUrl) return envUrl
  
  // In sandbox environment, construct backend URL from current hostname
  const hostname = window.location.hostname
  if (hostname.includes('sandbox.novita.ai') || hostname.includes('.e2b.dev')) {
    // Replace the port in the hostname (e.g., 5173 -> 8000)
    const backendHost = hostname.replace(/^\d+-/, '8000-')
    return `https://${backendHost}/api/v1`
  }
  
  // Default to relative path (works with proxy)
  return '/api/v1'
}

const API_BASE_URL = getApiBaseUrl()
const API_TIMEOUT = 60000 // 60 seconds for image generation

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add timestamp for debugging
    config.headers['X-Request-Time'] = new Date().toISOString()
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError<ErrorResponse>) => {
    if (error.response) {
      // Server responded with error
      const errorData = error.response.data
      console.error('API Error:', errorData)
      throw new Error(errorData.detail || errorData.error || 'An error occurred')
    } else if (error.request) {
      // Request was made but no response
      console.error('Network Error:', error.message)
      throw new Error('Network error. Please check your connection.')
    } else {
      // Error setting up request
      console.error('Request Setup Error:', error.message)
      throw new Error('Failed to send request')
    }
  }
)

/**
 * API methods
 */
export const api = {
  /**
   * Generic POST method
   */
  async post<T = any>(url: string, data?: any): Promise<{ data: T }> {
    const response = await apiClient.post<T>(url, data)
    return { data: response.data }
  },

  /**
   * Generic GET method
   */
  async get<T = any>(url: string): Promise<{ data: T }> {
    const response = await apiClient.get<T>(url)
    return { data: response.data }
  },

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await apiClient.get<HealthCheckResponse>('/health')
    return response.data
  },

  /**
   * Submit annotated image for explanation
   */
  async snapAndExplain(request: SnapAndExplainRequest): Promise<SnapAndExplainResponse> {
    const response = await apiClient.post<SnapAndExplainResponse>('/snap-and-explain', request)
    return response.data
  },

  /**
   * Upload image file for explanation
   */
  async snapAndExplainUpload(
    imageFile: File,
    annotations?: string,
    question?: string
  ): Promise<SnapAndExplainResponse> {
    const formData = new FormData()
    formData.append('image', imageFile)
    if (annotations) {
      formData.append('annotations', annotations)
    }
    if (question) {
      formData.append('question', question)
    }

    const response = await apiClient.post<SnapAndExplainResponse>('/snap-and-explain/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * Get supported subjects
   */
  async getSubjects(): Promise<{ subjects: SubjectInfo[] }> {
    const response = await apiClient.get<{ subjects: SubjectInfo[] }>('/subjects')
    return response.data
  },

  /**
   * Get available diagram styles
   */
  async getStyles(): Promise<{ styles: StyleInfo[] }> {
    const response = await apiClient.get<{ styles: StyleInfo[] }>('/styles')
    return response.data
  },
}

/**
 * Helper function to convert image file to base64
 */
export async function imageFileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Remove data URI prefix if present
      const base64 = result.includes(',') ? result.split(',')[1] : result
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/**
 * Helper function to convert canvas to base64
 */
export function canvasToBase64(canvas: HTMLCanvasElement, format: 'jpeg' | 'png' = 'jpeg'): string {
  const dataUrl = canvas.toDataURL(`image/${format}`, 0.9)
  return dataUrl.split(',')[1]
}

/**
 * Helper function to compress image before upload
 */
export async function compressImage(
  file: File,
  maxWidth: number = 1920,
  maxHeight: number = 1080,
  quality: number = 0.85
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      // Calculate new dimensions
      let { width, height } = img
      if (width > maxWidth) {
        height = (height * maxWidth) / width
        width = maxWidth
      }
      if (height > maxHeight) {
        width = (width * maxHeight) / height
        height = maxHeight
      }

      // Create canvas and draw
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('Failed to get canvas context'))
        return
      }
      ctx.drawImage(img, 0, 0, width, height)

      // Get base64
      const base64 = canvas.toDataURL('image/jpeg', quality).split(',')[1]
      resolve(base64)
    }
    img.onerror = () => reject(new Error('Failed to load image'))
    img.src = URL.createObjectURL(file)
  })
}

export default api
