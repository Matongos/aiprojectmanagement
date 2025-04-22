"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Grid, List, Plus } from "lucide-react";
import { toast } from "react-hot-toast";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";

interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  creator_id: number;
}

export default function ProjectsPage() {
  return (
    <AuthWrapper>
      <ProjectsContent />
    </AuthWrapper>
  );
}

function ProjectsContent() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const { user, token } = useAuthStore();
  const router = useRouter();
  
  // Check if user can create projects (admin or has project creation permission)
  const canCreateProjects = user?.is_superuser === true;
  // Check if user can delete/edit projects (admin or project owner)
  const isAdmin = user?.is_superuser === true;

  const fetchProjects = async () => {
    try {
      setLoading(true);
      setError(null);

      // Use token from auth store first, if not available try localStorage
      const authToken = token || localStorage.getItem('token');
      
      if (!authToken) {
        throw new Error("No authentication token found");
      }

      const response = await fetch(`${API_BASE_URL}/projects/`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          "Content-Type": "application/json"
        },
        // Add cache: 'no-store' to prevent caching
        cache: 'no-store'
      });

      if (response.status === 401) {
        // Handle unauthorized error - redirect to login
        toast.error("Your session has expired. Please log in again.");
        router.push('/auth/login');
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.status}`);
      }

      const data = await response.json();
      console.log("Projects data:", data);
      setProjects(data);
    } catch (error) {
      console.error("Error fetching projects:", error);
      setError(error instanceof Error ? error.message : "Failed to load projects");
      toast.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && token) {
      fetchProjects();
    }
  }, [user, token]);

  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDeleteProject = async (projectId: number) => {
    if (!window.confirm("Are you sure you want to delete this project?")) {
      return;
    }

    try {
      // Use token from auth store first, if not available try localStorage
      const authToken = token || localStorage.getItem('token');
      
      if (!authToken) {
        throw new Error("No authentication token found");
      }
      
      const response = await fetch(
        `${API_BASE_URL}/projects/${projectId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${authToken}`,
            "Content-Type": "application/json"
          },
        }
      );

      if (response.status === 401) {
        // Handle unauthorized error - redirect to login
        toast.error("Your session has expired. Please log in again.");
        router.push('/auth/login');
        return;
      }

      if (!response.ok) {
        throw new Error("Failed to delete project");
      }

      toast.success("Project deleted successfully");
      fetchProjects();
    } catch (error) {
      console.error("Error deleting project:", error);
      toast.error("Failed to delete project");
    }
  };

  // Check if user can edit/delete a specific project
  const canModifyProject = (project: Project) => {
    if (!user) return false;
    return isAdmin || project.creator_id === Number(user.id);
  };

  if (loading) {
    return <div className="p-4">Loading projects...</div>;
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <Button onClick={fetchProjects}>Retry</Button>
      </div>
    );
  }

  if (!projects.length) {
    return (
      <div className="p-8">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold mb-2">No Projects Found</h2>
          <p className="text-gray-600">You don't have any projects yet. Create your first project to get started.</p>
        </div>
        {canCreateProjects && (
          <div className="flex justify-center">
            <Button onClick={() => router.push("/dashboard/projects/create")}>
              <Plus className="h-4 w-4 mr-2" />
              Create New Project
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <div className="flex items-center gap-4">
          <Input
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-64"
          />
          <div className="flex gap-2">
            <Button
              variant={viewMode === "grid" ? "default" : "outline"}
              onClick={() => setViewMode("grid")}
            >
              <Grid className="h-4 w-4 mr-2" />
              Grid
            </Button>
            <Button
              variant={viewMode === "list" ? "default" : "outline"}
              onClick={() => setViewMode("list")}
            >
              <List className="h-4 w-4 mr-2" />
              List
            </Button>
          </div>
          {canCreateProjects && (
            <Button onClick={() => router.push("/dashboard/projects/create")}>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          )}
        </div>
      </div>

      {viewMode === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => (
            <Card key={project.id} className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-semibold">{project.name}</h3>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() =>
                        router.push(`/dashboard/projects/${project.id}`)
                      }
                    >
                      View Details
                    </DropdownMenuItem>
                    {canModifyProject(project) && (
                      <>
                        <DropdownMenuItem
                          onClick={() =>
                            router.push(`/dashboard/projects/${project.id}/edit`)
                          }
                        >
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleDeleteProject(project.id)}
                          className="text-red-600"
                        >
                          Delete
                        </DropdownMenuItem>
                      </>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <p className="text-gray-600 mb-4">{project.description}</p>
              <div className="flex justify-between items-center">
                <span
                  className={`px-2 py-1 rounded-full text-xs ${
                    project.status === "active"
                      ? "bg-green-100 text-green-800"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {project.status}
                </span>
                <span className="text-sm text-gray-500">
                  Updated: {new Date(project.updated_at).toLocaleDateString()}
                </span>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Updated</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredProjects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell className="font-medium">{project.name}</TableCell>
                  <TableCell>{project.description}</TableCell>
                  <TableCell>
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        project.status === "active"
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {project.status}
                    </span>
                  </TableCell>
                  <TableCell>
                    {new Date(project.updated_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() =>
                            router.push(`/dashboard/projects/${project.id}`)
                          }
                        >
                          View Details
                        </DropdownMenuItem>
                        {canModifyProject(project) && (
                          <>
                            <DropdownMenuItem
                              onClick={() =>
                                router.push(`/dashboard/projects/${project.id}/edit`)
                              }
                            >
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleDeleteProject(project.id)}
                              className="text-red-600"
                            >
                              Delete
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
} 