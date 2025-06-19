"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Plus, Star, Calendar, MoreVertical, Search, FileText, LineChart, Share2, Settings, ListTodo, Milestone, BarChart3, Eye } from "lucide-react";
import { toast } from "react-hot-toast";
import { useRouter } from "next/navigation";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";

type ProjectStatus = 'on_track' | 'at_risk' | 'off_track' | 'on_hold' | 'done';
type ProjectStage = 'to_do' | 'in_progress' | 'done' | 'cancelled' | null;

interface Project {
  id: number;
  name: string;
  description: string;
  status: ProjectStatus;
  stage: ProjectStage;
  created_at: string;
  start_date: string | null;
  end_date: string | null;
  task_count: number;
  member_count: number;
  tags: string[];
  members: { id: number; user: { profile_image_url?: string; name: string } }[];
  creator_id?: number;
  has_user_tasks?: boolean;
  progress: number;
  weighted_progress?: number;
}

const statusConfig: Record<ProjectStatus | 'default', { label: string; color: string; description: string }> = {
  on_track: { label: 'On Track', color: 'bg-green-500', description: 'Project is progressing as planned' },
  at_risk: { label: 'At Risk', color: 'bg-yellow-500', description: 'Project might face some issues' },
  off_track: { label: 'Off Track', color: 'bg-red-500', description: 'Project is behind schedule' },
  on_hold: { label: 'On Hold', color: 'bg-gray-500', description: 'Project is temporarily paused' },
  done: { label: 'Done', color: 'bg-blue-500', description: 'Project is completed' },
  default: { label: 'Unknown', color: 'bg-gray-300', description: 'Status not set' }
};

const stageConfig: Record<NonNullable<ProjectStage>, { label: string; color: string }> = {
  'to_do': { label: 'To Do', color: 'bg-gray-500' },
  'in_progress': { label: 'In Progress', color: 'bg-blue-500' },
  'done': { label: 'Done', color: 'bg-green-500' },
  'cancelled': { label: 'Cancelled', color: 'bg-red-500' }
};

const ProgressIndicator = ({ progress, weighted_progress }: { progress: number; weighted_progress?: number }) => {
  const getProgressColor = (value: number) => {
    if (value >= 80) return 'text-green-600 bg-green-50';
    if (value >= 50) return 'text-blue-600 bg-blue-50';
    if (value >= 30) return 'text-yellow-600 bg-yellow-50';
    return 'text-gray-600 bg-gray-50';
  };

  const displayProgress = weighted_progress !== undefined ? weighted_progress : progress;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <div className={`px-2 py-0.5 rounded-full text-xs font-medium ${getProgressColor(displayProgress)}`}>
            {Math.round(displayProgress)}%
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>Project Progress: {Math.round(displayProgress)}%</p>
          {weighted_progress !== undefined && (
            <p className="text-xs text-gray-500">(Weighted by planned hours)</p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
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
  const [searchQuery, setSearchQuery] = useState("");
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null);
  const { user, token } = useAuthStore();
  const router = useRouter();
  
  // Check if user can create projects (admin or has project creation permission)
  const canCreateProjects = user?.is_superuser === true;
  // Check if user can delete/edit projects (admin or project owner)
  const isAdmin = user?.is_superuser === true;

  // Check if a user has access to a project
  const hasProjectAccess = (project: Project): boolean => {
    // Superusers can access all projects
    if (user?.is_superuser) return true;
    
    // Project creators can access their projects
    if (project.creator_id === Number(user?.id)) return true;
    
    // Users with tasks in the project can access it
    if (project.has_user_tasks) return true;
    
    return false;
  };

  const fetchProjects = async (search?: string) => {
    try {
      setLoading(true);
      setError(null);

      const authToken = token || localStorage.getItem('token');
      
      if (!authToken) {
        throw new Error("No authentication token found");
      }

      // First, we need to get ALL projects to show in the listing
      const allProjectsApiUrl = isAdmin
        ? `${API_BASE_URL}/projects/`  // Admin gets all projects directly 
        : `${API_BASE_URL}/projects/`; // Regular users get all projects too, but we'll mark access level
      
      const allProjectsResponse = await fetch(allProjectsApiUrl, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          "Content-Type": "application/json"
        },
        cache: 'no-store'
      });

      if (allProjectsResponse.status === 401) {
        toast.error("Your session has expired. Please log in again.");
        router.push('/auth/login');
        return;
      }

      if (!allProjectsResponse.ok) {
        throw new Error(`Failed to fetch projects: ${allProjectsResponse.status}`);
      }

      const allProjects = await allProjectsResponse.json();
      
      // Fetch weighted progress for each project
      const projectsWithProgress = await Promise.all(
        allProjects.map(async (project: Project) => {
          try {
            const progressResponse = await fetch(
              `${API_BASE_URL}/analytics/projects/${project.id}/weighted-progress`,
              {
                headers: {
                  Authorization: `Bearer ${authToken}`,
                  "Content-Type": "application/json"
                }
              }
            );
            
            if (progressResponse.ok) {
              const progressData = await progressResponse.json();
              return {
                ...project,
                weighted_progress: progressData.weighted_progress
              };
            }
            return project;
          } catch (error) {
            console.error(`Error fetching progress for project ${project.id}:`, error);
            return project;
          }
        })
      );
      
      // Now check if user has tasks in each project
      let userTasks = [];
      try {
        const userTasksResponse = await fetch(`${API_BASE_URL}/tasks/`, {
          headers: {
            Authorization: `Bearer ${authToken}`,
            "Content-Type": "application/json"
          }
        });
        
        if (userTasksResponse.ok) {
          userTasks = await userTasksResponse.json();
        }
      } catch (taskError) {
        console.error("Error fetching user tasks:", taskError);
      }
      
      // Mark projects where user has access
      const projectsWithAccessInfo = projectsWithProgress.map((project: Project) => {
        const hasUserTasks = userTasks.length > 0
          ? userTasks.some((task: any) => task.project_id === project.id)
          : false;
        
        const isCreator = project.creator_id === Number(user?.id);
        
        return {
          ...project,
          has_user_tasks: hasUserTasks,
          has_access: isAdmin || isCreator || hasUserTasks,
          status: project.status in statusConfig ? project.status : 'default'
        };
      });
      
      setProjects(projectsWithAccessInfo);
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

  const handleStatusChange = async (projectId: number, newStatus: ProjectStatus) => {
    try {
      const authToken = token || localStorage.getItem('token');
      
      if (!authToken) {
        throw new Error("No authentication token found");
      }

      // First update optimistically in the UI
      setProjects(projects.map(project => 
        project.id === projectId 
          ? { ...project, status: newStatus }
          : project
      ));
      
      const response = await fetch(
        `${API_BASE_URL}/projects/${projectId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${authToken}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ status: newStatus })
        }
      );

      if (response.status === 401) {
        toast.error("Your session has expired. Please log in again.");
        router.push('/auth/login');
        return;
      }

      if (!response.ok) {
        // Revert the optimistic update if the API call fails
        setProjects(projects.map(project => 
          project.id === projectId 
            ? { ...project }
            : project
        ));
        throw new Error("Failed to update project status");
      }

      const updatedProject = await response.json();
      
      // Update with the response from the server
      setProjects(projects.map(project => 
        project.id === projectId 
          ? { ...project, ...updatedProject }
          : project
      ));

      toast.success(`Project status updated to ${statusConfig[newStatus].label}`);
    } catch (error) {
      console.error("Error updating project status:", error);
      toast.error("Failed to update project status");
    }
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
          {canCreateProjects && (
            <Button onClick={() => router.push("/dashboard/projects/create")} variant="default">
              <Plus className="h-4 w-4 mr-2" />
              Create New Project
            </Button>
          )}
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
        {filteredProjects.map((project) => {
          const projectAccess = hasProjectAccess(project);
          
          return (
            <Card
              key={project.id}
              className={`p-4 transition-all ${
                projectAccess 
                  ? 'cursor-pointer hover:shadow-lg' 
                  : 'cursor-not-allowed opacity-60'
              }`}
              onClick={() => {
                if (projectAccess) {
                  router.push(`/dashboard/projects/${project.id}`);
                } else {
                  toast.error("You don't have access to this project. You need to be assigned to a task in this project or be the creator.");
                }
              }}
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-start gap-2">
                  <Star className={`w-5 h-5 mt-1 ${projectAccess ? 'text-yellow-400' : 'text-gray-400'}`} />
                  <div>
                    <h3 className="font-semibold text-lg">{project.name}</h3>
                    <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                      <Calendar className="w-4 h-4" />
                      <span>{formatDate(project.start_date)} — {formatDate(project.end_date)}</span>
                    </div>
                    {!projectAccess && (
                      <p className="text-xs text-gray-500 mt-1 italic">
                        Limited access - get assigned to a task to unlock
                      </p>
                    )}
                  </div>
                </div>
                
                {projectAccess && (
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
                        <DropdownMenuItem onClick={() => router.push(`/dashboard/projects/${project.id}/tasks`)}>
                          <ListTodo className="mr-2 h-4 w-4" />
                          <span>Tasks</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => router.push(`/dashboard/projects/${project.id}/milestones`)}>
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
                )}
              </div>
              
              <div className="flex items-center justify-between mt-4">
                <div className="flex gap-2">
                  {project.tags?.map((tag, index) => (
                    <span
                      key={index}
                      className={`px-2 py-1 text-xs rounded-full ${
                        projectAccess 
                          ? 'bg-gray-100 text-gray-600' 
                          : 'bg-gray-50 text-gray-400'
                      }`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex -space-x-2">
                    {project.members?.slice(0, 3).map((member) => (
                      <Avatar key={member.id} className={`h-6 w-6 border-2 border-white ${!projectAccess && 'opacity-60'}`}>
                        <AvatarImage 
                          src={member.user.profile_image_url || '/default-avatar.png'} 
                          alt={member.user.name}
                          className="object-cover"
                        />
                        <AvatarFallback>{member.user.name[0]}</AvatarFallback>
                      </Avatar>
                    ))}
                    {project.member_count > 3 && (
                      <div className={`h-6 w-6 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center ${!projectAccess && 'opacity-60'}`}>
                        <span className="text-xs text-gray-600">+{project.member_count - 3}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <div className={`w-4 h-4 rounded-full ${statusConfig[project.status]?.color || statusConfig.default.color} transition-all duration-200 hover:ring-2 hover:ring-offset-2 hover:ring-${(statusConfig[project.status]?.color || statusConfig.default.color).replace('bg-', '')}`} />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Status: {statusConfig[project.status]?.label || statusConfig.default.label}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                    {project.stage && (
                      <div className="flex items-center gap-2">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <div className={`w-4 h-4 rounded-full ${stageConfig[project.stage].color} transition-all duration-200 hover:ring-2 hover:ring-offset-2 hover:ring-${stageConfig[project.stage].color.replace('bg-', '')}`} />
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Stage: {stageConfig[project.stage].label}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    )}
                    <ProgressIndicator progress={project.progress || 0} weighted_progress={project.weighted_progress} />
                    <span className={`text-sm ${projectAccess ? 'text-gray-600' : 'text-gray-400'}`}>
                      {project.task_count || 0} Tasks
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
} 