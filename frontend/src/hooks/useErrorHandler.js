import { useState } from 'react';
import { ERROR_MESSAGES } from '../constants';

/**
 * Standardized error handling hook
 * Provides consistent error handling across components
 * 
 * @returns {{ error, handleError, clearError }}
 * 
 * Example usage:
 * const { error, handleError, clearError } = useErrorHandler();
 * 
 * try {
 *   await someApiCall();
 * } catch (err) {
 *   handleError(err, { toast: showToast });
 * }
 */
export function useErrorHandler() {
  const [error, setError] = useState(null);
  
  /**
   * Handle error with consistent logic
   * 
   * @param {Error} err - Error object
   * @param {Object} options - Options { toast, fallback, ignoreAbort }
   */
  const handleError = (err, options = {}) => {
    const { 
      toast = null,
      fallback = ERROR_MESSAGES.UNKNOWN, 
      ignoreAbort = true,
      logToConsole = true
    } = options;
    
    // Ignore AbortError by default
    if (ignoreAbort && err.name === 'AbortError') {
      return;
    }
    
    // Determine error message
    let message = fallback;
    
    if (err.message) {
      message = err.message;
    } else if (err.status === 401 || err.status === 403) {
      message = ERROR_MESSAGES.UNAUTHORIZED;
    } else if (err.status === 404) {
      message = ERROR_MESSAGES.NOT_FOUND;
    } else if (err.status >= 500) {
      message = ERROR_MESSAGES.SERVER_ERROR;
    } else if (err.name === 'TypeError' && !navigator.onLine) {
      message = ERROR_MESSAGES.NETWORK;
    }
    
    // Set local error state
    setError(message);
    
    // Show toast if provided
    if (toast) {
      toast(message, "error");
    }
    
    // Log to console in development
    if (logToConsole && process.env.NODE_ENV === 'development') {
      console.error('[Error Handler]', {
        message,
        originalError: err,
        stack: err.stack,
        status: err.status
      });
    }
  };
  
  /**
   * Clear error state
   */
  const clearError = () => setError(null);
  
  /**
   * Check if error is of specific type
   */
  const isErrorType = (errorType) => {
    if (!error) return false;
    return error.includes(ERROR_MESSAGES[errorType]);
  };
  
  return { 
    error, 
    handleError, 
    clearError,
    isErrorType
  };
}
