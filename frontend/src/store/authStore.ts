import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

// API URL - should be in environment variables
const API_URL = 'http://localhost:8001';

// Axios instance with CORS config
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: false
});

// Types
interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_superuser: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (email: string, username: string, full_name: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

// Create auth store with persistence
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login function
      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          console.log(`Attempting login for: ${username}`);
          
          // Create form data for token endpoint
          const formData = new FormData();
          formData.append('username', username);
          formData.append('password', password);

          // Use URLSearchParams for proper form submission
          const params = new URLSearchParams();
          params.append('username', username);
          params.append('password', password);

          const response = await axios.post(`${API_URL}/auth/login`, params, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded'
            }
          });
          
          const data = response.data;
          console.log("Login successful:", data);

          // Set auth state
          set({
            user: {
              id: data.user_id,
              username: data.username,
              email: data.email,
              full_name: data.full_name,
              is_superuser: data.is_superuser
            },
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });

          // Set axios default auth header
          axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        } catch (error: any) {
          console.error("Login error:", error);
          set({
            isLoading: false,
            error: error.response?.data?.detail || 'Login failed. Please try again.'
          });
        }
      },

      // Register function
      register: async (email: string, username: string, full_name: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          console.log("Registering new user:", username);
          
          const response = await axios.post(`${API_URL}/auth/register`, {
            email,
            username,
            full_name,
            password
          });
          
          const data = response.data;
          console.log("Registration successful:", data);

          // Set auth state
          set({
            user: {
              id: data.user_id,
              username: data.username,
              email: data.email,
              full_name: data.full_name,
              is_superuser: data.is_superuser
            },
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });

          // Set axios default auth header
          axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        } catch (error: any) {
          console.error("Registration error:", error);
          set({
            isLoading: false,
            error: error.response?.data?.detail || 'Registration failed. Please try again.'
          });
        }
      },

      // Logout function
      logout: () => {
        // Remove auth header
        delete axios.defaults.headers.common['Authorization'];
        
        // Clear state
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null
        });
      },

      // Clear error function
      clearError: () => {
        set({ error: null });
      }
    }),
    {
      name: 'auth-storage', // name of the item in storage
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
); 