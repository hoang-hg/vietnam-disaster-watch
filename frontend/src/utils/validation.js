/**
 * Centralized form validation utilities
 * Provides consistent validation logic and error messages across the app
 */

export const validators = {
  /**
   * Check if value is not empty
   */
  required: (value, fieldName = "Trường này") => {
    if (!value || (typeof value === 'string' && !value.trim())) {
      return `${fieldName} không được để trống`;
    }
    return null;
  },
  
  /**
   * Check minimum length
   */
  minLength: (value, min, fieldName = "Trường này") => {
    if (value && value.length < min) {
      return `${fieldName} phải có ít nhất ${min} ký tự`;
    }
    return null;
  },
  
  /**
   * Check maximum length
   */
  maxLength: (value, max, fieldName = "Trường này") => {
    if (value && value.length > max) {
      return `${fieldName} không được vượt quá ${max} ký tự`;
    }
    return null;
  },
  
  /**
   * Check if value is a valid number
   */
  number: (value, fieldName = "Trường này") => {
    if (value !== '' && value !== null && value !== undefined && isNaN(Number(value))) {
      return `${fieldName} phải là số`;
    }
    return null;
  },
  
  /**
   * Check if number is positive (>= 0)
   */
  positive: (value, fieldName = "Trường này") => {
    if (value !== '' && value !== null && value !== undefined && Number(value) < 0) {
      return `${fieldName} không thể âm`;
    }
    return null;
  },
  
  /**
   * Check if number is within range
   */
  range: (value, min, max, fieldName = "Trường này") => {
    const num = Number(value);
    if (!isNaN(num) && (num < min || num > max)) {
      return `${fieldName} phải từ ${min} đến ${max}`;
    }
    return null;
  },
  
  /**
   * Validate email format
   */
  email: (value, fieldName = "Email") => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (value && !emailRegex.test(value)) {
      return `${fieldName} không hợp lệ`;
    }
    return null;
  },
  
  /**
   * Validate Vietnamese phone number (10-11 digits)
   */
  phone: (value, fieldName = "Số điện thoại") => {
    const phoneRegex = /^[0-9]{10,11}$/;
    if (value && !phoneRegex.test(value.replace(/\s/g, ''))) {
      return `${fieldName} không hợp lệ (10-11 chữ số)`;
    }
    return null;
  },
  
  /**
   * Validate URL format
   */
  url: (value, fieldName = "URL") => {
    try {
      if (value) new URL(value);
      return null;
    } catch {
      return `${fieldName} không hợp lệ`;
    }
  },
  
  /**
   * Custom regex pattern
   */
  pattern: (value, regex, fieldName = "Trường này", message = "không hợp lệ") => {
    if (value && !regex.test(value)) {
      return `${fieldName} ${message}`;
    }
    return null;
  }
};

/**
 * Validate entire form against rules
 * 
 * @param {Object} formData - Form data object
 * @param {Object} rules - Validation rules { fieldName: [validator1, validator2, ...] }
 * @returns {{ isValid: boolean, errors: Object }}
 * 
 * Example:
 * const { isValid, errors } = validateForm(formData, {
 *   title: [
 *     (v) => validators.required(v, "Tiêu đề"),
 *     (v) => validators.minLength(v, 5, "Tiêu đề")
 *   ],
 *   damage: [
 *     (v) => validators.number(v, "Thiệt hại"),
 *     (v) => validators.positive(v, "Thiệt hại")
 *   ]
 * });
 */
export function validateForm(formData, rules) {
  const errors = {};
  
  for (const [field, fieldRules] of Object.entries(rules)) {
    const value = formData[field];
    
    for (const rule of fieldRules) {
      const error = rule(value);
      if (error) {
        errors[field] = error;
        break; // Stop at first error for this field
      }
    }
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
}

/**
 * Validate single field
 * 
 * @param {any} value - Field value
 * @param {Array} rules - Array of validator functions
 * @returns {string|null} - Error message or null
 */
export function validateField(value, rules) {
  for (const rule of rules) {
    const error = rule(value);
    if (error) return error;
  }
  return null;
}
