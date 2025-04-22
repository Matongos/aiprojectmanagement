"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "react-hot-toast";

interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  creator_id: number;
}

export default function ProjectDetailsPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    const fetchProject = async () => {
      try {
        if (!token) {
          throw new Error("No authentication token found");
        }

        const response = await fetch(
          `http://192.168.56.1:8003/projects/${params.id}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error("Failed to fetch project");
        }

        const data = await response.json();
        setProject(data);
      } catch (error) {
        console.error("Error fetching project:", error);
        toast.error("Failed to load project");
        router.push("/dashboard/projects");
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [params.id, token, router]);

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  if (!project) {
    return <div className="p-4">Project not found</div>;
  }

  return (
    <div className="container mx-auto py-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <div className="flex gap-4">
            <Button
              variant="outline"
              onClick={() => router.push(`/dashboard/projects/${params.id}/edit`)}
            >
              Edit Project
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push("/dashboard/projects")}
            >
              Back to Projects
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Project Details</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-500">Description</p>
                <p className="mt-1">{project.description}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Status</p>
                <span
                  className={`px-2 py-1 rounded-full text-xs mt-1 ${
                    project.status === "active"
                      ? "bg-green-100 text-green-800"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {project.status}
                </span>
              </div>
              <div>
                <p className="text-sm text-gray-500">Created At</p>
                <p className="mt-1">
                  {new Date(project.created_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Last Updated</p>
                <p className="mt-1">
                  {new Date(project.updated_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Project Tasks</h2>
            <div className="space-y-4">
              {/* Task list will be implemented here */}
              <p className="text-gray-500">No tasks yet</p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
} 