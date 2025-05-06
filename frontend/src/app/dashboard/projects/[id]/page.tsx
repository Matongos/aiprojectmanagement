"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "react-hot-toast";
import { fetchApi } from "@/lib/api-helper";
import { API_BASE_URL, DEFAULT_AVATAR_URL } from "@/lib/constants";
import { 
  Plus, 
  Star, 
  Calendar, 
  Clock, 
  Check,
  X,
  AlertCircle,
  LayoutGrid,
  List as ListIcon,
  Search,
  Filter,
  ChevronDown,
  Settings,
  Archive,
  Edit,
  Trash2,
  FolderOpen,
  ChevronRight,
  ChevronLeft
} from "lucide-react";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { use } from "react";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/authStore";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface TaskStatus {
  id: string;
  label: string;
  color: string;
  icon: 'check' | 'x' | 'alert';
}

const taskStatuses: TaskStatus[] = [
  { id: 'in_progress', label: 'In Progress', color: 'bg-gray-200', icon: 'check' },
  { id: 'changes_requested', label: 'Changes Requested', color: 'bg-yellow-200', icon: 'alert' },
  { id: 'approved', label: 'Approved', color: 'bg-green-200', icon: 'check' },
  { id: 'cancelled', label: 'Cancelled', color: 'bg-red-200', icon: 'x' },
  { id: 'done', label: 'Done', color: 'bg-green-500', icon: 'check' }
];

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: 'low' | 'medium' | 'high';
  due_date: string | null;
  created_at: string;
  assignee: {
    id: number;
    name: string;
    profile_image_url: string | null;
  } | null;
}

interface ProjectStage {
  id: number;
  name: string;
  description: string | null;
  sequence: number;
  is_active: boolean;
  fold: boolean;
  project_id: number;
  created_at: string;
  updated_at: string | null;
}

interface Project {
  id: number;
  name: string;
  description: string;
  status: 'on_track' | 'at_risk' | 'off_track' | 'on_hold' | 'done' | 'default';
  stages: ProjectStage[];
  created_at: string;
  updated_at: string;
  creator_id: number;
  start_date: string | null;
  end_date: string | null;
}

interface User {
  id: number;
  name: string;
  email: string;
  profile_image_url?: string;
}

interface Milestone {
  id: number;
  name: string;
}

const styles = `
  .writing-mode-vertical {
    writing-mode: vertical-rl;
    text-orientation: mixed;
  }
`;

export default function ProjectDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const [project, setProject] = useState<Project | null>(null);
  const [stages, setStages] = useState<ProjectStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsedStages, setCollapsedStages] = useState<Set<number>>(new Set());
  const [viewMode, setViewMode] = useState<'kanban' | 'list'>('kanban');
  const [searchQuery, setSearchQuery] = useState('');
  const [newStageName, setNewStageName] = useState('');
  const [isAddingStage, setIsAddingStage] = useState(false);
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [hoveredStageId, setHoveredStageId] = useState<number | null>(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [selectedAssignees, setSelectedAssignees] = useState<User[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [currentStageId, setCurrentStageId] = useState<number | null>(null);
  const [foldedStages, setFoldedStages] = useState<Set<number>>(new Set());
  const [stageToDelete, setStageToDelete] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [selectedMilestone, setSelectedMilestone] = useState<number | null>(null);
  const [deadline, setDeadline] = useState<string | null>(null);

  useEffect(() => {
    const fetchProjectAndStages = async () => {
      if (!projectId || !token) return;
      
      try {
        setLoading(true);
        
        // Fetch project details
        const projectResponse = await fetch(`${API_BASE_URL}/projects/${projectId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!projectResponse.ok) {
          throw new Error(`Failed to fetch project: ${projectResponse.statusText}`);
        }

        const projectData = await projectResponse.json();
        setProject(projectData);

        // Fetch stages for the project
        const stagesResponse = await fetch(`${API_BASE_URL}/projects/${projectId}/stages`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!stagesResponse.ok) {
          throw new Error(`Failed to fetch stages: ${stagesResponse.statusText}`);
        }

        const stagesData = await stagesResponse.json();
        if (Array.isArray(stagesData)) {
          setStages(stagesData);
          // Initialize folded stages from backend data
          const foldedStagesSet = new Set(
            stagesData
              .filter(stage => stage.fold)
              .map(stage => stage.id)
          );
          setFoldedStages(foldedStagesSet);
        } else {
          console.error("Received invalid stages data:", stagesData);
          setStages([]);
        }

      } catch (error) {
        console.error("Error fetching project data:", error);
        toast.error(error instanceof Error ? error.message : "Failed to load project data");
        setStages([]);
      } finally {
        setLoading(false);
      }
    };

    fetchProjectAndStages();
  }, [projectId, token]);

  // Fetch users for assignee selection
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        if (!token) {
          console.log("No token available");
          return;
        }

        const data = await fetchApi<User[]>('/users');
        setUsers(data);
      } catch (error) {
        console.error('Error fetching users:', error);
        toast.error('Failed to load users');
      }
    };

    fetchUsers();
  }, [token]);

  // Fetch milestones for the project
  useEffect(() => {
    const fetchMilestones = async () => {
      try {
        // Try both possible milestone endpoints
        try {
          // First try the /milestones/project/{id} endpoint
          const data = await fetchApi<Milestone[]>(`/milestones/project/${projectId}`);
          setMilestones(data || []);
        } catch (error) {
          if (error instanceof Error && error.message.includes('404')) {
            // If first endpoint fails, try alternative endpoint
            const data = await fetchApi<Milestone[]>(`/projects/${projectId}/milestones`);
            setMilestones(data || []);
          } else {
            throw error;
          }
        }
      } catch (error) {
        console.error('Error fetching milestones:', error);
        // Silently set empty milestones array for 404s
        if (error instanceof Error && error.message.includes('404')) {
          setMilestones([]);
        } else {
          toast.error('Failed to load milestones');
        }
      }
    };

    if (projectId) {
      fetchMilestones();
    }
  }, [projectId, token]);

  const handleCreateStage = async () => {
    if (!projectId) return;

    try {
      const newStage = {
        name: 'New Stage',
        description: '',
        sequence: project?.stages.length + 1,
        project_id: parseInt(projectId),
        is_active: true,
        fold: false
      };

      await fetchApi(`/projects/${projectId}/stages`, {
        method: 'POST',
        body: JSON.stringify(newStage)
      });
      
      // Refresh project data
      const updatedProject = await fetchApi<Project>(`/projects/${projectId}`);
      setProject({
        ...updatedProject,
        stages: updatedProject.stages || []
      });
      toast.success('Stage created successfully');
    } catch (error) {
      console.error('Error creating stage:', error);
      toast.error('Failed to create stage');
    }
  };

  const handleCreateTask = async () => {
    if (!newTaskTitle.trim() || !currentStageId) return;

    try {
      const taskData = {
        name: newTaskTitle.trim(),
        description: "",
        priority: "normal",
        state: "draft",
        project_id: Number(projectId),
        stage_id: currentStageId,
        assigned_to: selectedAssignees.length > 0 ? selectedAssignees[0].id : null,
        milestone_id: selectedMilestone,
        deadline: deadline,
        planned_hours: 0.0
      };

      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(taskData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create task');
      }

      // Reset form and refresh data
      setNewTaskTitle('');
      setSelectedAssignees([]);
      setSelectedMilestone(null);
      setDeadline(null);
      setIsTaskModalOpen(false);
      
      // Refresh stages to get updated task list
      const stagesResponse = await fetch(`${API_BASE_URL}/projects/${projectId}/stages`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!stagesResponse.ok) {
        throw new Error('Failed to refresh stages');
      }
      
      const updatedStages = await stagesResponse.json();
      setStages(updatedStages);
      
      toast.success('Task created successfully');
    } catch (error) {
      console.error('Error creating task:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to create task');
    }
  };

  const handleTaskStatusChange = async (taskId: number, newStatus: string) => {
    if (!projectId) return;

    try {
      await fetchApi(`/tasks/${taskId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus })
      });
      // Refresh project data
      const updatedProject = await fetchApi<Project>(`/projects/${projectId}`);
      setProject({
        ...updatedProject,
        stages: updatedProject.stages || []
      });
      toast.success('Task status updated');
    } catch (error) {
      console.error('Error updating task status:', error);
      toast.error('Failed to update task status');
    }
  };

  const getRelativeTime = (date: string) => {
    const days = Math.floor((new Date().getTime() - new Date(date).getTime()) / (1000 * 60 * 60 * 24));
    return `${days} days ago`;
  };

  const StatusIcon = ({ status }: { status: string }) => {
    const taskStatus = taskStatuses.find(s => s.id === status);
    if (!taskStatus) return null;

    return (
      <div className={`rounded-full p-0.5 ${taskStatus.color} cursor-pointer`}>
        {taskStatus.icon === 'check' && <Check className="h-2.5 w-2.5" />}
        {taskStatus.icon === 'x' && <X className="h-2.5 w-2.5" />}
        {taskStatus.icon === 'alert' && <AlertCircle className="h-2.5 w-2.5" />}
      </div>
    );
  };

  const toggleStageCollapse = (stageId: number) => {
    setCollapsedStages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stageId)) {
        newSet.delete(stageId);
      } else {
        newSet.add(stageId);
      }
      return newSet;
    });
  };

  const handleAddStage = async () => {
    if (!newStageName.trim() || !projectId || !token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/stages`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newStageName.trim(),
          description: '',
          sequence: stages.length,
          project_id: Number(projectId),
          is_active: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create stage');
      }

      const newStage = await response.json();
      setStages(prev => [...prev, newStage]);
      setNewStageName('');
      setIsAddingStage(false);
      toast.success('Stage created successfully');
    } catch (error) {
      console.error("Error creating stage:", error);
      toast.error('Failed to create stage');
    }
  };

  const handleStageDelete = async (stageId: number) => {
    try {
      setIsDeleting(true);
      
      // Call the backend endpoint to delete the stage
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/stages/${stageId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to delete stage: ${response.statusText}`);
      }

      // Update local state immediately after successful deletion
      setStages(prevStages => prevStages.filter(stage => stage.id !== stageId));
      
      // Remove from folded stages if it was folded
      setFoldedStages(prev => {
        const newSet = new Set(prev);
        newSet.delete(stageId);
        return newSet;
      });

      // Close the delete confirmation dialog
      setStageToDelete(null);
      
      toast.success('Stage deleted successfully');

    } catch (error) {
      console.error('Error deleting stage:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to delete stage');
      setStageToDelete(null);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleStageEdit = async (stageId: number, newName: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/stages/${stageId}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newName })
      });

      if (!response.ok) throw new Error('Failed to update stage');

      setStages(prev => prev.map(stage => 
        stage.id === stageId ? { ...stage, name: newName } : stage
      ));
      toast.success('Stage updated successfully');
    } catch (error) {
      toast.error('Failed to update stage');
    }
  };

  const handleArchiveAll = async (stageId: number) => {
    try {
      await fetch(`${API_BASE_URL}/projects/${projectId}/stages/${stageId}/archive-all`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      // Refresh stages data
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/stages`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const updatedStages = await response.json();
      setStages(updatedStages);
      toast.success('All tasks archived successfully');
    } catch (error) {
      toast.error('Failed to archive tasks');
    }
  };

  const handleUnarchiveAll = async (stageId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/stages/${stageId}/unarchive-all`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          toast.error('No archived tasks found in this stage');
          return;
        }
        throw new Error(`Failed to unarchive tasks: ${response.statusText}`);
      }
      
      // Refresh stages data
      const stagesResponse = await fetch(`${API_BASE_URL}/projects/${projectId}/stages`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!stagesResponse.ok) {
        throw new Error('Failed to refresh stages data');
      }

      const updatedStages = await stagesResponse.json();
      if (Array.isArray(updatedStages)) {
        setStages(updatedStages);
        toast.success('All tasks unarchived successfully');
      } else {
        console.error("Received invalid stages data:", updatedStages);
        toast.error('Failed to refresh stages data');
      }
    } catch (error) {
      console.error('Error unarchiving tasks:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to unarchive tasks');
    }
  };

  const removeAssignee = (userId: number) => {
    setSelectedAssignees(prev => prev.filter(user => user.id !== userId));
  };

  const renderEmptyState = () => {
    const placeholderStages = [
      { name: "To Do", description: "Tasks to be started" },
      { name: "In Progress", description: "Tasks currently being worked on" },
      { name: "Done", description: "Completed tasks" }
    ];

    return (
      <div className="overflow-x-auto">
        <div className="inline-flex gap-4 min-w-full pb-4">
          {/* Real Inbox Stage */}
          <div className="w-[300px] flex-shrink-0 bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium">Inbox</h3>
                <span className="text-xs text-gray-500 px-2 py-0.5 bg-gray-200 rounded-full">0</span>
              </div>
            </div>
            <div className="mt-3 space-y-2 min-h-[200px]">
              <div className="flex items-center justify-center h-[200px] border-2 border-dashed border-gray-200 rounded-lg">
                <p className="text-sm text-gray-500">Drop tasks here</p>
              </div>
            </div>
          </div>

          {/* Placeholder Stages */}
          {placeholderStages.map((stage, index) => (
            <div key={index} className="w-[300px] flex-shrink-0 bg-gray-50/30 rounded-lg p-3 relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <p className="text-sm text-gray-400">Example Stage:</p>
                  <h4 className="text-lg font-medium text-gray-400">{stage.name}</h4>
                  <p className="text-xs text-gray-400 mt-1">{stage.description}</p>
                </div>
              </div>
              <div className="opacity-30 pointer-events-none">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium">{stage.name}</h3>
                    <span className="text-xs text-gray-500 px-2 py-0.5 bg-gray-200 rounded-full">0</span>
                  </div>
                </div>
                <div className="mt-3 space-y-2 min-h-[200px]">
                  <div className="flex items-center justify-center h-[200px] border-2 border-dashed border-gray-200 rounded-lg">
                    <p className="text-sm text-gray-500">Drop tasks here</p>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Add Stage Button */}
          <button
            onClick={() => setIsAddingStage(true)}
            className="w-[300px] flex-shrink-0 h-[200px] flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
          >
            <div className="flex flex-col items-center gap-2">
              <Plus className="h-6 w-6 text-gray-400" />
              <span className="text-sm text-gray-500">Add Stage</span>
            </div>
          </button>
        </div>
      </div>
    );
  };

  const handleFoldStage = async (stageId: number) => {
    try {
      const isFolded = foldedStages.has(stageId);
      const currentStage = stages.find(s => s.id === stageId);
      
      if (!currentStage) {
        throw new Error('Stage not found');
      }
      
      // Optimistically update the UI
      setFoldedStages(prev => {
        const newSet = new Set(prev);
        if (isFolded) {
          newSet.delete(stageId);
        } else {
          newSet.add(stageId);
        }
        return newSet;
      });

      // Update the backend with all required fields
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/stages/${stageId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: currentStage.name,
          description: currentStage.description,
          sequence: currentStage.sequence,
          fold: !isFolded,
          is_active: currentStage.is_active,
          project_id: currentStage.project_id
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update stage fold state');
      }

      // Update the stages array with the new fold state
      setStages(prev => prev.map(stage => 
        stage.id === stageId 
          ? { ...stage, fold: !isFolded }
          : stage
      ));

      // Show success message
      toast.success(isFolded ? 'Stage unfolded' : 'Stage folded');

    } catch (error) {
      // Revert the optimistic update on error
      setFoldedStages(prev => {
        const newSet = new Set(prev);
        if (foldedStages.has(stageId)) {
          newSet.delete(stageId);
        } else {
          newSet.add(stageId);
        }
        return newSet;
      });
      
      console.error('Error updating stage fold state:', error);
      toast.error('Failed to update stage fold state');
    }
  };

  const confirmDeleteStage = (stageId: number) => {
    setStageToDelete(stageId);
  };

  useEffect(() => {
    // Add the styles to the document
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);

    // Cleanup
    return () => {
      document.head.removeChild(styleSheet);
    };
  }, []);

  if (loading) return <div className="p-4">Loading...</div>;
  if (!project) return <div className="p-4">Project not found</div>;

  const isProjectCreator = user?.id === project.creator_id;

  // Task Creation Modal
  const TaskCreationModal = () => (
    <Dialog open={isTaskModalOpen} onOpenChange={setIsTaskModalOpen}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create New Task</DialogTitle>
          <DialogDescription>
            Add a new task to your project. Fill in the task details below.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Task Title</label>
            <Input
              placeholder="Enter task title..."
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              className="w-full"
              autoFocus
            />
          </div>
          
          {/* Only show milestone selector if milestones exist */}
          {milestones.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Milestone</label>
              <Select
                value={selectedMilestone}
                onValueChange={setSelectedMilestone}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select milestone" />
                </SelectTrigger>
                <SelectContent>
                  {milestones.map((milestone) => (
                    <SelectItem key={milestone.id} value={milestone.id}>
                      {milestone.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">Deadline</label>
            <Input
              type="datetime-local"
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium">Assignees (Optional)</label>
            <Command className="rounded-lg border shadow-md">
              <CommandInput placeholder="Search users..." />
              <CommandEmpty>No users found.</CommandEmpty>
              <CommandGroup className="max-h-[200px] overflow-auto">
                {users?.map((user) => (
                  <CommandItem
                    key={user.id}
                    onSelect={() => {
                      if (!selectedAssignees.find(a => a.id === user.id)) {
                        setSelectedAssignees(prev => [...prev, user]);
                      }
                    }}
                  >
                    <Avatar className="h-6 w-6 mr-2">
                      <AvatarImage 
                        src={user.profile_image_url || DEFAULT_AVATAR_URL} 
                        alt={user.name || ''} 
                      />
                      <AvatarFallback>{user.name ? user.name[0] : '?'}</AvatarFallback>
                    </Avatar>
                    {user.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            </Command>

            <div className="flex flex-wrap gap-2 mt-2">
              {selectedAssignees.map((user) => (
                <Badge 
                  key={user.id}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  <span>{user.name || 'Unknown User'}</span>
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => removeAssignee(user.id)}
                  />
                </Badge>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => {
              setIsTaskModalOpen(false);
              setNewTaskTitle('');
              setSelectedAssignees([]);
              setSelectedMilestone(null);
              setDeadline(null);
            }}>
              Cancel
            </Button>
            <Button onClick={handleCreateTask} disabled={!newTaskTitle.trim()}>
              Create Task
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );

  return (
    <div className="container mx-auto p-4">
      {/* Project Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-400" />
            <h1 className="text-xl font-semibold">{project.name}</h1>
          </div>
          <div className={`px-2 py-0.5 rounded text-xs ${
            project.status === 'off_track' ? 'bg-red-100 text-red-800' :
            project.status === 'on_track' ? 'bg-green-100 text-green-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {project.status.replace('_', ' ').charAt(0).toUpperCase() + project.status.slice(1)}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Search and Filter */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search tasks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 h-8 w-[200px]"
              />
            </div>
            <Button variant="outline" size="sm" className="h-8">
              <Filter className="h-4 w-4" />
            </Button>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-md p-0.5">
            <Button
              variant={viewMode === 'kanban' ? 'default' : 'ghost'}
              size="sm"
              className="h-7"
              onClick={() => setViewMode('kanban')}
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              className="h-7"
              onClick={() => setViewMode('list')}
            >
              <ListIcon className="h-4 w-4" />
            </Button>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button size="sm" onClick={() => {
              setCurrentStageId(null);
              setIsTaskModalOpen(true);
            }}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              New Task
            </Button>
            <Button size="sm" variant="outline" onClick={() => setIsAddingStage(true)}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Add Stage
            </Button>
          </div>
        </div>
      </div>

      {/* Task Creation Modal */}
      <TaskCreationModal />

      {/* Kanban/List View */}
      {viewMode === 'kanban' ? (
        <div className="relative">
          {/* Stage Creation Modal */}
          {isAddingStage && (
            <Dialog open={isAddingStage} onOpenChange={setIsAddingStage}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create New Stage</DialogTitle>
                  <DialogDescription>
                    Add a new stage to organize your tasks.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Stage Name</label>
                    <Input
                      placeholder="Enter stage name..."
                      value={newStageName}
                      onChange={(e) => setNewStageName(e.target.value)}
                      className="w-full"
                      autoFocus
                      onKeyPress={(e) => e.key === 'Enter' && handleAddStage()}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setIsAddingStage(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleAddStage}>
                      Create Stage
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          )}

          {!stages || stages.length === 0 ? (
            renderEmptyState()
          ) : (
            <div className="overflow-x-auto">
              <div className="inline-flex gap-4 min-w-full pb-4">
                {Array.isArray(stages) && stages.map((stage) => (
                  <div 
                    key={stage.id} 
                    className={`transition-all duration-300 ease-in-out ${
                      foldedStages.has(stage.id) 
                        ? 'w-[50px] min-h-[200px]' 
                        : 'w-[300px]'
                    } flex-shrink-0 bg-gray-50 rounded-lg p-3 relative ${
                      isDeleting && stageToDelete === stage.id ? 'opacity-50 pointer-events-none' : ''
                    }`}
                    onMouseEnter={() => setHoveredStageId(stage.id)}
                    onMouseLeave={() => setHoveredStageId(null)}
                  >
                    <div className={`space-y-2 ${foldedStages.has(stage.id) ? 'h-full' : ''}`}>
                      <div className={`flex items-center ${foldedStages.has(stage.id) ? 'h-full flex-col' : 'justify-between'}`}>
                        {foldedStages.has(stage.id) ? (
                          // Folded view
                          <div className="w-full flex flex-col items-center justify-between h-full py-2 relative group">
                            <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
                              <span className="text-purple-600 font-medium text-sm">
                                {stage.tasks?.length || 0}
                              </span>
                            </div>
                            
                            {/* Unfold Arrow Button */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleFoldStage(stage.id);
                              }}
                              className="absolute -right-3 top-1/2 transform -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <div className="bg-white rounded-full p-1 shadow-md hover:shadow-lg transition-shadow">
                                <ChevronRight className="h-4 w-4 text-gray-600" />
                              </div>
                            </button>

                            <div className="writing-mode-vertical transform rotate-180 flex-grow flex items-center mt-3">
                              <span className="text-xs text-gray-600 whitespace-nowrap">
                                {stage.name}
                              </span>
                            </div>
                          </div>
                        ) : (
                          // Unfolded view
                          <>
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-medium">{stage.name}</h3>
                              <span className="text-xs text-gray-500 px-2 py-0.5 bg-gray-200 rounded-full">
                                {stage.tasks?.length || 0}
                              </span>
                            </div>
                            
                            <div className="flex items-center gap-1">
                              {/* Fold Button */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleFoldStage(stage.id);
                                }}
                                className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-100 rounded-full flex items-center justify-center"
                              >
                                <ChevronLeft className="h-4 w-4 text-gray-600" />
                              </button>

                              {/* Add Task Button */}
                              <Button
                                variant="ghost"
                                className="h-6 w-6 p-0"
                                onClick={() => {
                                  setCurrentStageId(stage.id);
                                  setIsTaskModalOpen(true);
                                }}
                              >
                                <Plus className="h-4 w-4" />
                              </Button>

                              {/* Settings Dropdown */}
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className={`h-6 w-6 p-0 opacity-0 ${
                                      hoveredStageId === stage.id ? 'opacity-100' : ''
                                    } transition-opacity`}
                                  >
                                    <Settings className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem onClick={() => handleFoldStage(stage.id)}>
                                    <FolderOpen className="h-4 w-4 mr-2" />
                                    {foldedStages.has(stage.id) ? 'Unfold' : 'Fold'}
                                  </DropdownMenuItem>
                                  <DropdownMenuItem 
                                    onClick={() => {
                                      const newName = prompt('Enter new stage name:', stage.name);
                                      if (newName) handleStageEdit(stage.id, newName);
                                    }}
                                  >
                                    <Edit className="h-4 w-4 mr-2" />
                                    Edit
                                  </DropdownMenuItem>
                                  <DropdownMenuItem 
                                    onClick={() => {
                                      setStageToDelete(stage.id);
                                    }}
                                    className="text-red-600"
                                  >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete
                                  </DropdownMenuItem>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem onClick={() => handleArchiveAll(stage.id)}>
                                    <Archive className="h-4 w-4 mr-2" />
                                    Archive All
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => handleUnarchiveAll(stage.id)}>
                                    <Archive className="h-4 w-4 mr-2" />
                                    Unarchive All
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </>
                        )}
                      </div>

                      {/* Tasks Container - Only show if not folded */}
                      {!foldedStages.has(stage.id) && (
                        <div className="space-y-2 min-h-[200px]">
                          <Button
                            variant="ghost"
                            className="w-full flex items-center justify-center py-2 border-2 border-dashed border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                            onClick={() => {
                              setCurrentStageId(stage.id);
                              setIsTaskModalOpen(true);
                            }}
                          >
                            <Plus className="h-4 w-4 mr-2" />
                            Add Task
                          </Button>
                          {!stage.tasks?.length ? (
                            <div className="flex items-center justify-center h-[200px] border-2 border-dashed border-gray-200 rounded-lg">
                              <p className="text-sm text-gray-500">Drop tasks here</p>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {stage.tasks.map((task) => (
                                <Card 
                                  key={task.id} 
                                  className="p-3 cursor-pointer hover:shadow-md transition-shadow"
                                  onClick={() => router.push(`/dashboard/projects/${projectId}/tasks/${task.id}`)}
                                >
                                  {/* Task Header */}
                                  <div className="flex items-start justify-between mb-2">
                                    <div className="flex-1">
                                      <h4 className="text-sm font-medium mb-1">{task.name}</h4>
                                      {task.company && (
                                        <p className="text-xs text-gray-600">{task.company.name}</p>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                      {task.milestone && (
                                        <Badge variant="secondary" className="text-xs">
                                          {task.milestone}
                                        </Badge>
                                      )}
                                    </div>
                                  </div>

                                  {/* Task Details */}
                                  <div className="flex items-center justify-between mt-3">
                                    <div className="flex items-center gap-2">
                                      {task.assigned_to ? (
                                        <Avatar className="h-6 w-6">
                                          <AvatarImage 
                                            src={task.assignee?.profile_image_url || DEFAULT_AVATAR_URL} 
                                            alt={task.assignee?.name || ''} 
                                          />
                                          <AvatarFallback>
                                            {task.assignee?.name ? task.assignee.name[0] : '?'}
                                          </AvatarFallback>
                                        </Avatar>
                                      ) : (
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-6 w-6 p-0 rounded-full"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            // TODO: Open assignee selection
                                          }}
                                        >
                                          <Plus className="h-4 w-4" />
                                        </Button>
                                      )}
                                    </div>

                                    {task.deadline && (
                                      <div className="flex items-center gap-1 text-xs text-gray-500">
                                        <Calendar className="h-3 w-3" />
                                        <span>
                                          {Math.max(0, Math.ceil(
                                            (new Date(task.deadline).getTime() - new Date().getTime()) / 
                                            (1000 * 60 * 60 * 24)
                                          ))} days left
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                </Card>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Add Stage Button at the end of stages */}
                <button
                  onClick={() => setIsAddingStage(true)}
                  className="w-[300px] flex-shrink-0 h-[200px] flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                  disabled={isDeleting}
                >
                  <div className="flex flex-col items-center gap-2">
                    <Plus className="h-6 w-6 text-gray-400" />
                    <span className="text-sm text-gray-500">Add Stage</span>
                  </div>
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <table className="min-w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Task</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {stages?.flatMap(stage => 
                stage.tasks?.map(task => (
                  <tr 
                    key={task.id} 
                    className="border-b hover:bg-gray-50 cursor-pointer"
                    onClick={() => router.push(`/dashboard/projects/${projectId}/tasks/${task.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center">
                        <StatusIcon status={task.status} />
                        <span className="ml-2">{task.title}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">{stage.name}</td>
                    <td className="px-4 py-3">
                      {task.assignee && (
                        <div className="flex items-center">
                          <Avatar className="h-6 w-6">
                            <AvatarImage src={task.assignee.profile_image_url || DEFAULT_AVATAR_URL} />
                            <AvatarFallback>{task.assignee.name[0]}</AvatarFallback>
                          </Avatar>
                          <span className="ml-2 text-sm">{task.assignee.name}</span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {task.due_date && new Date(task.due_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs
                        ${task.status === 'done' ? 'bg-green-100 text-green-800' :
                          task.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'}`}>
                        {task.status.replace('_', ' ')}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog 
        open={stageToDelete !== null} 
        onOpenChange={(open) => {
          if (!open && !isDeleting) {
            setStageToDelete(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this stage and all its tasks. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={async () => {
                if (stageToDelete !== null) {
                  await handleStageDelete(stageToDelete);
                }
              }}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Deleting...
                </div>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
} 