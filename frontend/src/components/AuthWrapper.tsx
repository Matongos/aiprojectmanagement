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
  const [isMounted, setIsMounted] = useState(false);
  const { checkAuth } = useAuthStore();
  const router = useRouter();

  // First, handle client-side mounting to prevent hydration errors
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Then handle authentication logic only after component is mounted
  useEffect(() => {
    // Skip auth check during SSR or before mounting
    if (!isMounted) return;

    async function verifyAuth() {
      setIsLoading(true);
      try {
        const authenticated = await checkAuth();
        if (!authenticated) {
          console.log("AuthWrapper: Not authenticated, redirecting to login");
          toast.error("Please log in to access this page");
          router.push("/auth/login");
          return;
        }
      } catch (error) {
        console.error("AuthWrapper: Auth verification error:", error);
        toast.error("Authentication error. Please log in again.");
        router.push("/auth/login");
      } finally {
        setIsLoading(false);
      }
    }
    
    verifyAuth();
  }, [checkAuth, router, isMounted]);

  // Return a simpler loading state during SSR to avoid hydration mismatches
  if (!isMounted) {
    return <>{children}</>;
  }

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