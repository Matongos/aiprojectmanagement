"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Calendar, Star, Clock } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { toast } from "react-hot-toast";

interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  created_at: string;
  start_date: string;
  end_date: string;
  customer: string;
  tags: string[];
  allocated_hours: string;
  project_manager: {
    id: number;
    name: string;
    profile_image_url?: string;
  };
}

export default function ProjectView() {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const params = useParams();
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/projects/${params.id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch project");
        }

        const data = await response.json();
        setProject(data);
      } catch (error) {
        toast.error("Failed to load project details");
      } finally {
        setLoading(false);
      }
    };

    if (params.id) {
      fetchProject();
    }
  }, [params.id, token]);

  if (loading) {
    return <div className="p-4">Loading project details...</div>;
  }

  if (!project) {
    return <div className="p-4">Project not found</div>;
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });
  };

  return (
    <div className="container mx-auto py-6 px-4">
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Star className="h-6 w-6 text-yellow-400" />
            <h1 className="text-2xl font-bold">{project.name}</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="outline" size="sm">
              Add Shortcuts
            </Button>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm">To Do</Button>
              <Button variant="secondary" size="sm">In Progress</Button>
              <Button variant="secondary" size="sm">Done</Button>
              <Button variant="secondary" size="sm">Canceled</Button>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card className="p-6">
            <div className="grid grid-cols-2 gap-6 mb-6">
              <div>
                <label className="text-sm text-gray-500">Name of the Tasks</label>
                <div className="font-medium">{project.name}</div>
              </div>
              <div>
                <label className="text-sm text-gray-500">Project Manager</label>
                <div className="flex items-center gap-2">
                  <Avatar className="h-6 w-6">
                    <AvatarImage 
                      src={project.project_manager?.profile_image_url || '/default-avatar.png'}
                      alt={project.project_manager?.name}
                    />
                    <AvatarFallback>{project.project_manager?.name[0]}</AvatarFallback>
                  </Avatar>
                  <span className="font-medium">{project.project_manager?.name}</span>
                </div>
              </div>
              <div>
                <label className="text-sm text-gray-500">Customer</label>
                <div className="font-medium">{project.customer}</div>
              </div>
              <div>
                <label className="text-sm text-gray-500">Planned Date</label>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-500" />
                  <span className="font-medium">
                    {formatDate(project.start_date)} — {formatDate(project.end_date)}
                  </span>
                </div>
              </div>
              <div>
                <label className="text-sm text-gray-500">Tags</label>
                <div className="flex gap-2">
                  {project.tags?.map((tag, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-600"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm text-gray-500">Allocated Hours</label>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-500" />
                  <span className="font-medium">{project.allocated_hours}</span>
                </div>
              </div>
            </div>

            <Tabs defaultValue="description" className="w-full">
              <TabsList className="mb-4">
                <TabsTrigger value="description">Description</TabsTrigger>
                <TabsTrigger value="settings">Settings</TabsTrigger>
                <TabsTrigger value="checklist">Checklist</TabsTrigger>
              </TabsList>
              
              <TabsContent value="description">
                <div className="prose max-w-none">
                  {project.description || "No description provided."}
                </div>
              </TabsContent>
              
              <TabsContent value="settings">
                <div className="text-gray-600">
                  Project settings will be displayed here.
                </div>
              </TabsContent>
              
              <TabsContent value="checklist">
                <div className="text-gray-600">
                  Project checklist will be displayed here.
                </div>
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        <div className="col-span-1">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Project Activity</h3>
            <div className="text-gray-600">
              Recent activity will be displayed here.
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
} 