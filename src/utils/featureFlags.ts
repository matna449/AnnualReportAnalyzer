/**
 * Feature flags for the Annual Report Analyzer
 * 
 * This file contains feature flags used throughout the application to control
 * feature visibility and functionality. Use these flags to show/hide features
 * based on environment or user role.
 */

// Determines if developer tools like logging and debugging components are shown
export const SHOW_DEVELOPER_TOOLS = process.env.NODE_ENV === 'development' || 
  process.env.NEXT_PUBLIC_SHOW_DEVELOPER_TOOLS === 'true';

// Determines if detailed processing logs are shown to users
export const SHOW_PROCESSING_LOGS = SHOW_DEVELOPER_TOOLS || 
  process.env.NEXT_PUBLIC_SHOW_PROCESSING_LOGS === 'true';

// Check if current user has admin access (implement actual user role checking here)
export const isAdmin = (): boolean => {
  // For now, we'll use localStorage to determine if user is admin
  // In a real app, this would check auth context or make an API call
  if (typeof window !== 'undefined') {
    return localStorage.getItem('isAdmin') === 'true';
  }
  return false;
};

// Function to determine if logs should be visible based on user role and config
export const shouldShowLogs = (): boolean => {
  return SHOW_PROCESSING_LOGS || isAdmin();
}; 