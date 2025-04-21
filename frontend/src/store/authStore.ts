import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';
import { toast } from 'react-hot-toast';

// API URL - should be in environment variables
const API_URL = 'http://192.168.56.1:8003';

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
  is_active: boolean;
  is_superuser: boolean;
  profile_image_url?: string;
  job_title?: string;
  bio?: string;
  access_token?: string;
}

interface ProfileUpdateData {
  email?: string;
  full_name?: string;
  password?: string;
  current_password?: string;
  profile_image_url?: string;
  job_title?: string;
  bio?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  new_password?: string;
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
  updateProfile: (profileData: ProfileUpdateData) => Promise<void>;
  registerUser: (email: string, username: string, full_name: string, password: string, is_superuser: boolean) => Promise<void>;
}

interface ApiError {
  response?: {
    data?: {
      detail?: string | { [key: string]: unknown };
    };
    status?: number;
  };
  message?: string;
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
          
          const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'Access-Control-Allow-Origin': '*'
            },
            mode: 'cors',
            body: JSON.stringify({ username, password })
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
          }

          const data = await response.json();
          console.log("Login response data:", data);

          if (!data || !data.user) {
            console.error("Invalid response format:", data);
            throw new Error('Invalid response format from server');
          }

          // Ensure all user fields are properly mapped
          const userData: User = {
            id: data.user.id,
            username: data.user.username,
            email: data.user.email,
            full_name: data.user.full_name,
            is_active: data.user.is_active ?? true,
            is_superuser: data.user.is_superuser ?? false,
            profile_image_url: data.user.profile_image_url || '',
            job_title: data.user.job_title || '',
            bio: data.user.bio || '',
            access_token: data.access_token
          };

          console.log("Processed user data:", userData);

          if (!data.access_token) {
            console.error("No access token in response");
            throw new Error('No access token received from server');
          }

          set({
            user: userData,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });

          // Set authorization header for subsequent requests
          api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
          
          toast.success('Login successful!');
        } catch (error: unknown) {
          console.error("Login error:", error);
          
          let errorMessage = 'Login failed. Please try again.';
          
          if (error instanceof Error) {
            errorMessage = error.message;
          }
          
          set({
            isLoading: false,
            error: errorMessage
          });
          
          toast.error(errorMessage);
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

          set({
            user: {
              id: data.user_id,
              username: data.username,
              email: data.email,
              full_name: data.full_name,
              is_active: data.is_active ?? true,
              is_superuser: data.is_superuser,
              profile_image_url: data.profile_image_url,
              job_title: data.job_title,
              bio: data.bio,
              access_token: data.access_token
            },
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });

          axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        } catch (error: unknown) {
          console.error("Registration error:", error);
          
          let errorMessage = 'Registration failed. Please try again.';
          
          if (isApiError(error)) {
            const responseData = error.response?.data;
            
            if (typeof responseData === 'string') {
              errorMessage = responseData;
            } else if (typeof responseData?.detail === 'string') {
              errorMessage = responseData.detail;
            } else if (responseData?.detail && typeof responseData.detail === 'object') {
              errorMessage = JSON.stringify(responseData.detail);
            }
          }
          
          set({
            isLoading: false,
            error: errorMessage
          });
          
          toast.error(errorMessage);
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
      },

      // Add updateProfile function
      updateProfile: async (profileData: ProfileUpdateData) => {
        set({ isLoading: true, error: null });
        try {
          console.log("Updating profile with data:", profileData);
          
          // Prepare the request data
          const requestData: ProfileUpdateData = {};
          
          // Handle password update separately
          if (profileData.password) {
            if (!profileData.current_password) {
              throw new Error("Current password is required to change password");
            }
            requestData.new_password = profileData.password;
            requestData.current_password = profileData.current_password;
          }
          
          // Add other fields if they exist
          if (profileData.email) requestData.email = profileData.email;
          if (profileData.full_name) requestData.full_name = profileData.full_name;
          if (profileData.profile_image_url) requestData.profile_image_url = profileData.profile_image_url;
          if (profileData.job_title) requestData.job_title = profileData.job_title;
          if (profileData.bio) requestData.bio = profileData.bio;
          
          console.log("Sending request data:", requestData);
          
          const response = await axios.patch<User>(`${API_URL}/users/me/profile`, requestData, {
            headers: {
              'Authorization': `Bearer ${useAuthStore.getState().token}`
            }
          });
          
          const updatedUser = response.data;
          console.log("Profile update successful:", updatedUser);

          // Update the local state with the new user data
          set((state) => {
            if (!state.user) return state;
            
            return {
              ...state,
              user: {
                ...state.user,
                email: updatedUser.email,
                full_name: updatedUser.full_name,
                profile_image_url: updatedUser.profile_image_url,
                job_title: updatedUser.job_title,
                bio: updatedUser.bio,
                access_token: updatedUser.access_token
              },
              isLoading: false,
              error: null
            };
          });

          toast.success('Profile updated successfully');
        } catch (error: unknown) {
          console.error("Profile update error:", error);
          
          let errorMessage = 'Profile update failed. Please try again.';
          
          if (isApiError(error)) {
            const responseData = error.response?.data;
            
            if (typeof responseData === 'string') {
              errorMessage = responseData;
            } else if (typeof responseData?.detail === 'string') {
              errorMessage = responseData.detail;
            } else if (responseData?.detail && typeof responseData.detail === 'object') {
              errorMessage = JSON.stringify(responseData.detail);
            }
          }
          
          set({
            isLoading: false,
            error: errorMessage
          });
          
          toast.error(errorMessage);
        }
      },

      registerUser: async (email: string, username: string, full_name: string, password: string, is_superuser: boolean = false) => {
        try {
          const response = await api.post('/users/', {
            email,
            username,
            full_name,
            password,
            is_superuser,
          });
          set({ user: response.data });
          toast.success('Registration successful!');
        } catch (error) {
          console.error('Registration error:', error);
          toast.error('Registration failed. Please try again.');
          throw error;
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);

// Type guard for API errors
function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'response' in error
  );
} 