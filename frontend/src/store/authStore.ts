import { create } from 'zustand';
import { toast } from 'react-hot-toast';
import { API_BASE_URL } from '../lib/constants';

// User type
export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active?: boolean;
  is_superuser?: boolean;
  profile_image_url?: string;
  job_title?: string;
  bio?: string;
  access_token?: string;
}

// Profile update data type
export interface ProfileUpdateData {
  full_name?: string;
  job_title?: string;
  bio?: string;
  profile_image_url?: string;
}

// Auth store interface
interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  updateProfile: (profileData: ProfileUpdateData) => Promise<void>;
  registerUser: (email: string, username: string, full_name: string, password: string, is_superuser: boolean) => Promise<void>;
  loadingUserData: boolean;
  checkAuth: () => Promise<boolean>;
}

// Create auth store
export const useAuthStore = create<AuthStore>((set, get) => {
  // Initialize token from localStorage if available
  const storedToken = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  
  return {
    user: null,
    token: storedToken,
    isAuthenticated: !!storedToken,
    isLoading: false,
    error: null,
    loadingUserData: true,

    // Login function
    login: async (username: string, password: string) => {
      try {
        console.log(`Attempting login for: ${username} to ${API_BASE_URL}/token`);
        set({ isLoading: true, error: null });
        
        // Create form data
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE_URL}/token`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formData.toString(),
          cache: 'no-store'
        });

        console.log("Login response status:", response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error("Login error response:", errorText);
          set({ error: 'Invalid credentials', isLoading: false });
          return false;
        }

        const data = await response.json();
        console.log("Login response data received:", !!data);
        
        if (!data.access_token) {
          console.error("No access token in response");
          set({ error: 'Authentication failed', isLoading: false });
          return false;
        }
        
        // Store token in localStorage
        localStorage.setItem('token', data.access_token);
        
        // Update state
        set({ 
          token: data.access_token, 
          isAuthenticated: true,
          user: data.user,
          isLoading: false,
          error: null
        });
        
        console.log("Login successful, user data:", data.user);
        
        // Fetch additional user details if needed
        const authenticated = await get().checkAuth();
        return authenticated;
      } catch (error) {
        console.error('Login error:', error);
        set({ 
          error: error instanceof Error ? error.message : 'An error occurred during login', 
          isLoading: false,
          isAuthenticated: false
        });
        return false;
      }
    },

    // Logout function
    logout: () => {
      localStorage.removeItem('token');
      set({ token: null, isAuthenticated: false, user: null });
      toast.success('Logged out successfully');
    },

    // Update profile function
    updateProfile: async (profileData: ProfileUpdateData) => {
      try {
        const { token } = get();
        if (!token) throw new Error('Not authenticated');

        const response = await fetch(`${API_BASE_URL}/users/me`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(profileData)
        });
        
        if (!response.ok) {
          throw new Error('Failed to update profile');
        }
        
        const updatedUser = await response.json();
        
        // Update local user data
        set({
          user: updatedUser
        });

        toast.success('Profile updated successfully!');
      } catch (error) {
        console.error('Failed to update profile:', error);
        toast.error('Failed to update profile');
        throw error;
      }
    },

    // Register user function
    registerUser: async (email: string, username: string, full_name: string, password: string, is_superuser: boolean) => {
      try {
        const response = await fetch(`${API_BASE_URL}/users/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email,
            username,
            full_name,
            password,
            is_superuser
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to register user');
        }
        
        toast.success('User registered successfully!');
      } catch (error) {
        console.error('Registration error:', error);
        toast.error('Failed to register user');
        throw error;
      }
    },

    checkAuth: async () => {
      set({ loadingUserData: true });
      const token = localStorage.getItem('token');
      
      if (token) {
        try {
          console.log("Checking authentication with token");
          const response = await fetch(`${API_BASE_URL}/users/me`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
            cache: 'no-store'
          });

          console.log("Auth check response status:", response.status);

          if (response.ok) {
            const user = await response.json();
            console.log("Authentication successful, user data:", user);
            set({ token, isAuthenticated: true, user, loadingUserData: false, error: null });
            return true;
          } else {
            console.error("Authentication check failed, status:", response.status);
            // Clear invalid token
            localStorage.removeItem('token');
            set({ 
              token: null, 
              isAuthenticated: false, 
              user: null, 
              loadingUserData: false,
              error: 'Session expired. Please log in again.'
            });
            return false;
          }
        } catch (error) {
          console.error('Error checking auth:', error);
          localStorage.removeItem('token');
          set({ 
            token: null, 
            isAuthenticated: false, 
            user: null, 
            loadingUserData: false,
            error: 'Authentication error. Please log in again.'
          });
          return false;
        }
      } else {
        console.log("No token found in storage");
        set({ token: null, isAuthenticated: false, user: null, loadingUserData: false });
        return false;
      }
    }
  };
}); 