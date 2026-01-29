/**
 * Frontend Logging Utility
 * Provides structured logging with backend integration for traceability
 */

import { supabase } from '@/integrations/supabase/client'

export interface LogEntry {
  level: 'debug' | 'info' | 'warn' | 'error'
  message: string
  category?: string
  userId?: string
  sessionId?: string
  metadata?: Record<string, unknown>
  timestamp?: string
  userAgent?: string
  url?: string
}

class FrontendLogger {
  private sessionId: string
  private userId: string | null = null
  private buffer: LogEntry[] = []
  private flushInterval: number

  constructor() {
    this.sessionId = this.generateSessionId()
    this.flushInterval = setInterval(() => this.flush(), 30000) // Flush every 30 seconds

    // Get user ID when available (gracefully handle test environments)
    try {
      supabase.auth.getUser?.().then(({ data: { user } }) => {
        this.userId = user?.id || null
      }).catch(() => {
        // Ignore auth errors in test/dev environments
      })
    } catch {
      // Supabase client not fully initialized (test environment)
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      this.flush()
      clearInterval(this.flushInterval)
    })
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  private async flush(): Promise<void> {
    if (this.buffer.length === 0) return

    const logsToSend = [...this.buffer]
    this.buffer = []

    try {
      // Send logs to backend action logging system
      await supabase.from('action_logs').insert(
        logsToSend.map(log => ({
          action_type: `frontend_${log.level}`,
          action_name: log.message,
          status: 'completed',
          action_details: {
            category: log.category,
            metadata: log.metadata,
            url: log.url || window.location.href,
            userAgent: log.userAgent || navigator.userAgent,
            sessionId: this.sessionId
          },
          source: 'frontend',
          user_id: this.userId,
          action_timestamp: log.timestamp || new Date().toISOString()
        }))
      )
    } catch (error) {
      // Fallback to console if backend logging fails
      console.error('Failed to send logs to backend:', error)
      logsToSend.forEach(log => {
        console[log.level === 'error' ? 'error' : log.level === 'warn' ? 'warn' : 'log'](
          `[${log.level.toUpperCase()}] ${log.message}`,
          log.metadata || {}
        )
      })
    }
  }

  private log(level: LogEntry['level'], message: string, category?: string, metadata?: Record<string, unknown>): void {
    const logEntry: LogEntry = {
      level,
      message,
      category,
      userId: this.userId || undefined,
      sessionId: this.sessionId,
      metadata,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    // Always log to console for development
    const consoleMethod = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log'
    console[consoleMethod](`[${level.toUpperCase()}] ${message}`, metadata || {})

    // Buffer for backend sending
    this.buffer.push(logEntry)

    // Flush immediately for errors
    if (level === 'error') {
      this.flush()
    }
  }

  debug(message: string, category?: string, metadata?: Record<string, unknown>): void {
    this.log('debug', message, category, metadata)
  }

  info(message: string, category?: string, metadata?: Record<string, unknown>): void {
    this.log('info', message, category, metadata)
  }

  warn(message: string, category?: string, metadata?: Record<string, unknown>): void {
    this.log('warn', message, category, metadata)
  }

  error(message: string, category?: string, error?: Error, metadata?: Record<string, unknown>): void {
    const errorMetadata = {
      ...metadata,
      error: error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : undefined
    }
    this.log('error', message, category, errorMetadata)
  }

  // Track user actions
  trackAction(action: string, details?: Record<string, unknown>): void {
    this.info(`User action: ${action}`, 'user_action', details)
  }

  // Track API calls
  trackApiCall(endpoint: string, method: string, duration?: number, success?: boolean, error?: string): void {
    this.info(`API call: ${method} ${endpoint}`, 'api_call', {
      endpoint,
      method,
      duration,
      success,
      error
    })
  }

  // Track page views
  trackPageView(page: string): void {
    this.info(`Page view: ${page}`, 'navigation', { page })
  }
}

// Global logger instance
export const logger = new FrontendLogger()

// Convenience functions
export const logDebug = logger.debug.bind(logger)
export const logInfo = logger.info.bind(logger)
export const logWarn = logger.warn.bind(logger)
export const logError = logger.error.bind(logger)
export const trackAction = logger.trackAction.bind(logger)
export const trackApiCall = logger.trackApiCall.bind(logger)
export const trackPageView = logger.trackPageView.bind(logger)