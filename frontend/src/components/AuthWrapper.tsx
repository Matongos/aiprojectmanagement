"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";

interface AuthWrapperProps {
  children: React.ReactNode;
}

export default function AuthWrapper({ children }: AuthWrapperProps) {
  const [isLoading, setIsLoading] = useState(true);
  const { token, isAuthenticated, checkAuth, user } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    async function verifyAuth() {
      setIsLoading(true);
      console.log("AuthWrapper: Verifying authentication, token present:", !!token);
      console.log("AuthWrapper: isAuthenticated:", isAuthenticated);
      
      try {
        if (!isAuthenticated) {
          // Try to check authentication
          console.log("AuthWrapper: Calling checkAuth()");
          const authenticated = await checkAuth();
          
          if (!authenticated) {
            console.log("AuthWrapper: Not authenticated, redirecting to login");
            toast.error("Please log in to access this page");
            router.push("/auth/login");
            return;
          }
        }
        
        console.log("AuthWrapper: Auth verified, user:", user);
      } catch (error) {
        console.error("AuthWrapper: Auth verification error:", error);
        toast.error("Authentication error. Please log in again.");
        router.push("/auth/login");
        return;
      } finally {
        setIsLoading(false);
      }
    }
    
    verifyAuth();
  }, [checkAuth, router, token, isAuthenticated, user]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
} 