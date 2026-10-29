/**
 * Shared API configuration for frontend runtime requests.
 * Consistently targets the backend running on port 8001.
 */
export const API_BASE_URL =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
  'http://127.0.0.1:8001';

export const getApiUrl = (endpoint) => {
  if (!endpoint) return API_BASE_URL;
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

export default API_BASE_URL;
