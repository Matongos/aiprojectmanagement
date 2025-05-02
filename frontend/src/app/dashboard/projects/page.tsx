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
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Grid, List, Plus, Star, Calendar, MoreVertical, Search, FileText, LineChart, Share2, Settings, ListTodo, Milestone, BarChart3, Eye } from "lucide-react";
import { toast } from "react-hot-toast";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";
import { fetchApi } from "@/lib/api-helper";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";

interface Project {
  id: number;
  name: string;
  description: string;
  status: 'on_track' | 'at_risk' | 'off_track' | 'on_hold' | 'done';
  created_at: string;
  start_date: string | null;
  end_date: string | null;
  task_count: number;
  tags: string[];
  members: { id: number; user: { profile_image_url?: string; name: string } }[];
}

const statusConfig = {
  on_track: { label: 'On Track', color: 'bg-green-500' },
  at_risk: { label: 'At Risk', color: 'bg-yellow-500' },
  off_track: { label: 'Off Track', color: 'bg-red-500' },
  on_hold: { label: 'On Hold', color: 'bg-gray-500' },
  done: { label: 'Done', color: 'bg-blue-500' },
  default: { label: 'Unknown', color: 'bg-gray-300' }
};

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
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null);
  const { user, token } = useAuthStore();
  const router = useRouter();
  
  // Check if user can create projects (admin or has project creation permission)
  const canCreateProjects = user?.is_superuser === true;
  // Check if user can delete/edit projects (admin or project owner)
  const isAdmin = user?.is_superuser === true;

  const fetchProjects = async (search?: string) => {
    try {
      setLoading(true);
      setError(null);

      const authToken = token || localStorage.getItem('token');
      
      if (!authToken) {
        throw new Error("No authentication token found");
      }

      const apiUrl = search 
        ? `${API_BASE_URL}/projects/search/?query=${encodeURIComponent(search)}`
        : `${API_BASE_URL}/projects/`;

      const response = await fetch(apiUrl, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          "Content-Type": "application/json"
        },
        cache: 'no-store'
      });

      if (response.status === 401) {
        toast.error("Your session has expired. Please log in again.");
        router.push('/auth/login');
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.status}`);
      }

      const data = await response.json();
      console.log("Projects data with status:", data.map(p => ({ id: p.id, name: p.name, status: p.status })));
      
      const validatedData = data.map(project => ({
        ...project,
        status: statusConfig[project.status] ? project.status : 'default'
      }));
      
      setProjects(validatedData);
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
  
  // Handle search input with debounce
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    
    // Clear any existing timeout
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
    
    // Set a new timeout for the search
    const timeout = setTimeout(() => {
      if (query.trim().length > 0) {
        fetchProjects(query);
      } else {
        fetchProjects();
      }
    }, 500); // 500ms debounce
    
    setSearchTimeout(timeout);
  };

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

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric'
    });
  };

  if (loading) {
    return <div className="p-4">Loading projects...</div>;
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <Button onClick={() => fetchProjects()}>Retry</Button>
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
    <div className="container mx-auto py-6 px-4">
      {/* Header Section */}
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Projects</h1>
          <Button variant="outline" size="sm">
            <Star className="w-4 h-4 mr-2" />
            New
          </Button>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="pl-10 w-[300px]"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">1-{filteredProjects.length} / {projects.length}</span>
          </div>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredProjects.map((project) => (
          <Card
            key={project.id}
            className="p-4 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => router.push(`/dashboard/projects/${project.id}`)}
          >
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-start gap-2">
                <Star className="w-5 h-5 text-yellow-400 mt-1" />
                <div>
                  <h3 className="font-semibold text-lg">{project.name}</h3>
                  <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                    <Calendar className="w-4 h-4" />
                    <span>{formatDate(project.start_date)} — {formatDate(project.end_date)}</span>
                  </div>
                </div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                  <button className="text-gray-400 hover:text-gray-600">
                    <MoreVertical className="w-5 h-5" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" onClick={(e) => e.stopPropagation()}>
                  <DropdownMenuGroup>
                    <DropdownMenuItem onClick={() => router.push(`/dashboard/projects/${project.id}/view`)}>
                      <Eye className="mr-2 h-4 w-4" />
                      <span>View</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <ListTodo className="mr-2 h-4 w-4" />
                      <span>Tasks</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Milestone className="mr-2 h-4 w-4" />
                      <span>Milestones</span>
                    </DropdownMenuItem>
                  </DropdownMenuGroup>
                  <DropdownMenuSeparator />
                  <DropdownMenuGroup>
                    <DropdownMenuItem>
                      <FileText className="mr-2 h-4 w-4" />
                      <span>Project Updates</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <LineChart className="mr-2 h-4 w-4" />
                      <span>Tasks Analysis</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <BarChart3 className="mr-2 h-4 w-4" />
                      <span>Burndown Chart</span>
                    </DropdownMenuItem>
                  </DropdownMenuGroup>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <Share2 className="mr-2 h-4 w-4" />
                    <span>Share</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="flex items-center justify-between mt-4">
              <div className="flex gap-2">
                {project.tags?.map((tag, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-4">
                <div className="flex -space-x-2">
                  {project.members?.slice(0, 3).map((member) => (
                    <Avatar key={member.id} className="h-6 w-6 border-2 border-white">
                      <AvatarImage 
                        src={member.user.profile_image_url || '/default-avatar.png'} 
                        alt={member.user.name}
                        className="object-cover"
                      />
                      <AvatarFallback>{member.user.name[0]}</AvatarFallback>
                    </Avatar>
                  ))}
                  {project.members && project.members.length > 3 && (
                    <div className="h-6 w-6 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center">
                      <span className="text-xs text-gray-600">+{project.members.length - 3}</span>
                    </div>
                  )}
                </div>
                <div className={`w-3 h-3 rounded-full ${statusConfig[project.status]?.color || statusConfig.default.color}`} />
                <span className="text-sm font-medium">{project.task_count || 0} Tasks</span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
} 