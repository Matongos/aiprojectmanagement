"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "react-hot-toast";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";

export default function CreateProjectPage() {
  return (
    <AuthWrapper>
      <CreateProjectContent />
    </AuthWrapper>
  );
}

function CreateProjectContent() {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const { user } = useAuthStore();
  const router = useRouter();

  // Check if user can create projects (admin or has project creation permission)
  // For now we'll use is_superuser as the criteria
  const canCreateProjects = user?.is_superuser === true;

  // Redirect if user doesn't have permission
  useEffect(() => {
    if (user && !canCreateProjects) {
      toast.error("You don't have permission to create projects");
      router.push("/dashboard/projects");
    }
  }, [user, canCreateProjects, router]);

  // Generate a project key from the name
  const generateKey = (name: string) => {
    // Extract first letters of each word, max 5 chars
    const words = name.split(' ');
    let keyBase = words.map(word => word[0]?.toUpperCase() || '').join('');
    
    // Add some random chars if needed
    if (keyBase.length < 3) {
      keyBase += 'PRJ';
    }
    
    // Generate 3 random characters (letters and numbers)
    const randomChars = Math.random().toString(36).substring(2, 5).toUpperCase();
    
    return (keyBase.substring(0, 5) + randomChars).substring(0, 10);
  };

  // Update the key when name changes
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value;
    setName(newName);
    
    // Only auto-generate key if user hasn't manually edited it
    if (!key) {
      setKey(generateKey(newName));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const storedToken = localStorage.getItem('token');
      if (!storedToken) {
        throw new Error("No authentication token found");
      }

      if (!key) {
        throw new Error("Project key is required");
      }

      // Check permission again just to be safe
      if (!canCreateProjects) {
        throw new Error("You don't have permission to create projects");
      }

      const response = await fetch(`${API_BASE_URL}/projects/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${storedToken}`,
        },
        body: JSON.stringify({
          name,
          description,
          key,
          status: "active",
          privacy_level: "private"
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        console.error("Error creating project:", errorData);
        throw new Error(errorData?.detail || "Failed to create project");
      }

      toast.success("Project created successfully");
      router.push("/dashboard/projects");
    } catch (error) {
      console.error("Error creating project:", error);
      toast.error(error instanceof Error ? error.message : "Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  if (!user || !canCreateProjects) {
    return (
      <div className="container mx-auto py-6 text-center">
        <h1 className="text-2xl font-bold mb-4">Access Denied</h1>
        <p className="mb-4">You don't have permission to create projects.</p>
        <Button onClick={() => router.push("/dashboard/projects")}>
          Back to Projects
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Create New Project</h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium">
              Project Name
            </label>
            <Input
              id="name"
              value={name}
              onChange={handleNameChange}
              placeholder="Enter project name"
              required
            />
          </div>
          
          <div className="space-y-2">
            <label htmlFor="key" className="text-sm font-medium">
              Project Key (used in URLs and references)
            </label>
            <Input
              id="key"
              value={key}
              onChange={(e) => setKey(e.target.value.toUpperCase())}
              placeholder="e.g. PROJ123"
              maxLength={10}
              required
            />
            <p className="text-xs text-gray-500">
              A short, unique identifier for your project (max 10 chars)
            </p>
          </div>
          
          <div className="space-y-2">
            <label htmlFor="description" className="text-sm font-medium">
              Description
            </label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter project description"
              required
            />
          </div>
          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/dashboard/projects")}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create Project"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
} 