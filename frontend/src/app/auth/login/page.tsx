"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { toast } from "react-hot-toast";
import Link from "next/link";
import Image from "next/image";

const loginSchema = z.object({
  username: z.string().min(1, "Email is required"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean().optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const router = useRouter();
  const { login } = useAuthStore();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
      rememberMe: false,
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    try {
      setLoading(true);
      setErrorMessage("");
      console.log("Attempting login with:", data.username);
      
      const success = await login(data.username, data.password);
      
      if (success) {
        console.log("Login successful, redirecting to dashboard");
        toast.success("Login successful!");
        // Small delay to allow state to update
        setTimeout(() => {
          router.push("/dashboard");
        }, 500);
      } else {
        console.error("Login failed");
        setErrorMessage("Invalid username or password");
        toast.error("Login failed. Please check your credentials.");
      }
    } catch (err) {
      console.error("Login error:", err);
      setErrorMessage(err instanceof Error ? err.message : "An unexpected error occurred");
      toast.error("Login error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
      <div className="max-w-md w-full bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="mb-6 flex justify-center">
          <div className="relative h-8 w-36">
            <Image 
              src="/logo.png" 
              alt="ZINGSA Logo" 
              width={140} 
              height={32} 
              className="w-full h-full object-contain"
              priority
            />
          </div>
        </div>
        
        <h1 className="text-3xl font-bold text-center text-black mb-6">ZINGSA</h1>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {errorMessage && (
              <div className="text-sm text-red-600 text-center p-2 bg-gray-100 rounded border border-gray-300">
                {errorMessage}
              </div>
            )}
            
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-gray-800">Email</FormLabel>
                  <FormControl>
                    <Input 
                      {...field} 
                      placeholder="username"
                      autoComplete="username" 
                      className="border-gray-300 focus:border-black focus:ring-black"
                    />
                  </FormControl>
                  <FormMessage className="text-gray-700" />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-gray-800">Password</FormLabel>
                  <FormControl>
                    <Input 
                      {...field} 
                      type="password" 
                      placeholder="••••••"
                      autoComplete="current-password" 
                      className="border-gray-300 focus:border-black focus:ring-black"
                    />
                  </FormControl>
                  <FormMessage className="text-gray-700" />
                </FormItem>
              )}
            />
            
            <div className="flex items-center justify-between">
              <FormField
                control={form.control}
                name="rememberMe"
                render={({ field }) => (
                  <div className="flex items-center space-x-2">
                    <div className="h-4 w-4 rounded border border-gray-300 flex items-center justify-center">
                      {field.value && (
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3 text-black">
                          <path fillRule="evenodd" d="M19.916 4.626a.75.75 0 01.208 1.04l-9 13.5a.75.75 0 01-1.154.114l-6-6a.75.75 0 011.06-1.06l5.353 5.353 8.493-12.739a.75.75 0 011.04-.208z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <input
                      type="checkbox"
                      id="rememberMe"
                      checked={field.value}
                      onChange={(e) => field.onChange(e.target.checked)}
                      className="sr-only"
                    />
                    <label
                      htmlFor="rememberMe"
                      className="text-sm font-medium text-gray-700 cursor-pointer"
                      onClick={() => field.onChange(!field.value)}
                    >
                      Remember me
                    </label>
                  </div>
                )}
              />
              <Link 
                href="/auth/forgot-password"
                className="text-sm font-medium text-gray-700 hover:text-black"
              >
                Forgot your password?
              </Link>
            </div>
            
            <Button 
              type="submit" 
              className="w-full bg-black hover:bg-gray-800 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2" 
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </Form>
      </div>
    </div>
  );
} 