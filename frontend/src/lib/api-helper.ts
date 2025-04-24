import { API_BASE_URL } from './constants';

/**
 * Helper function to make authenticated API calls
 * @param endpoint The API endpoint (without base URL)
 * @param options Additional fetch options
 * @returns The response data or throws an error
 */
export async function fetchApi<T>(
  endpoint: string, 
  options: RequestInit = {},
  redirectOnAuthError: boolean = true
): Promise<T> {
  // Get token from localStorage
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  
  // Check if token exists
  if (!token) {
    // If we're in a browser context and should redirect
    if (typeof window !== 'undefined' && redirectOnAuthError) {
      console.warn('No authentication token found, redirecting to login');
      // Save the current URL to redirect back after login
      localStorage.setItem('redirectAfterLogin', window.location.pathname);
      window.location.href = '/auth/login';
    }
    throw new Error('No authentication token found');
  }
  
  // Set up headers with authentication
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  };

  try {
    // Make the request
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    // Check if the response is ok
    if (!response.ok) {
      // If authentication error and should redirect
      if (response.status === 401 && redirectOnAuthError && typeof window !== 'undefined') {
        console.warn('Authentication token expired or invalid, redirecting to login');
        localStorage.removeItem('token'); // Clear invalid token
        localStorage.setItem('redirectAfterLogin', window.location.pathname);
        window.location.href = '/auth/login';
      }
      
      // Try to get error details from response
      let errorMessage = `API Error: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch (_) {
        // If we can't parse error as JSON, just use the status text
      }
      
      throw new Error(errorMessage);
    }

    // Return the response data
    return await response.json() as T;
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    throw error;
  }
}

/**
 * Helper for POST requests
 */
export async function postApi<T>(
  endpoint: string,
  data: any,
  options: RequestInit = {}
): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * Helper for PUT requests
 */
export async function putApi<T>(
  endpoint: string,
  data: any,
  options: RequestInit = {}
): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * Helper for DELETE requests
 */
export async function deleteApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'DELETE',
    ...options,
  });
}

/**
 * Helper for PATCH requests
 */
export async function patchApi<T>(
  endpoint: string,
  data: any,
  options: RequestInit = {}
): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
    ...options,
  });
} 