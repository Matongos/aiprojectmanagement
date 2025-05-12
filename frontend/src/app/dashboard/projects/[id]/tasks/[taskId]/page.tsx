"use client";

import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MessageSquare, Star, MoreHorizontal, ChevronRight, Search, Settings, ChevronLeft, X, User } from "lucide-react";
import { useEffect, useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import React from "react";
import { API_BASE_URL } from "@/lib/constants";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { useQueryClient } from "@tanstack/react-query";
import { TaskState, statusConfig } from "@/types/task";

interface Stage {
  id: string;
  name: string;
  order: number;
  duration?: string;
}

interface Milestone {
  id: number;
  name: string;
  description?: string;
  due_date: string;
  is_completed: boolean;
  is_active: boolean;
  project_id: number;
  created_at: string;
  created_by?: number;
  updated_at?: string;
}

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  profile_image_url?: string;
}

interface Task {
  id: string;
  name: string;
  description: string;
  stage_id: number;
  milestone_id?: number;
  milestone?: Milestone;
  assigned_to?: number;
  assignee?: User;
  created_by: number;
  deadline?: string;
  state: TaskState;
  // ... other task properties
}

interface Activity {
  id: number;
  activity_type: string;
  description: string;
  created_at: string;
  user: {
    id: number;
    username: string;
    full_name: string;
    profile_image_url: string | null;
  };
}

interface TaskDetailsProps {
  params: Promise<{
    id: string;
    taskId: string;
  }>;
}

interface CreateMilestoneData {
  name: string;
  description?: string;
  project_id: number;
  due_date: string;
  is_completed: boolean;
  is_active: boolean;
}

interface TaskUpdateFields {
  name?: string;
  deadline?: string | null;
  assigned_to?: number | null;
  state?: TaskState;
}

export default function TaskDetails({ params }: TaskDetailsProps) {
  // Unwrap params using React.use()
  const { id, taskId } = React.use(params);
  const [currentStage, setCurrentStage] = useState<string>("");
  const [description, setDescription] = useState("");
  const { token } = useAuthStore();
  const [showAllStages, setShowAllStages] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [taskName, setTaskName] = useState("");
  const [isNameChanged, setIsNameChanged] = useState(false);
  const [deadline, setDeadline] = useState<string | null>(null);
  const [isDeadlineChanged, setIsDeadlineChanged] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showDetailedMilestones, setShowDetailedMilestones] = useState(false);
  const [showCreateMilestone, setShowCreateMilestone] = useState(false);
  const [searchMilestone, setSearchMilestone] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [showAssigneeSelection, setShowAssigneeSelection] = useState(false);
  const [searchUser, setSearchUser] = useState("");
  const [userPage, setUserPage] = useState(1);
  const [selectedAssignees, setSelectedAssignees] = useState<User[]>([]);
  const [isAssigneesChanged, setIsAssigneesChanged] = useState(false);
  const [newMilestone, setNewMilestone] = useState<CreateMilestoneData>({
    name: "",
    description: "",
    project_id: Number(id),
    due_date: "",
    is_completed: false,
    is_active: true
  });
  const itemsPerPage = 4;
  const queryClient = useQueryClient();
  const [currentStatus, setCurrentStatus] = useState<TaskState>(TaskState.IN_PROGRESS);
  const [isStatusChanged, setIsStatusChanged] = useState(false);

  // Fetch task details including current stage
  const { data: taskDetails, isLoading: isLoadingTask, error: taskError, refetch } = useQuery<Task>({
    queryKey: ["task-details", taskId],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 401) {
          toast.error("Please log in to view this content");
          throw new Error("Unauthorized");
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch task details: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("Task Details Response:", data); // Debug log
        setTaskName(data.name); // Set initial task name
        return data;
      } catch (error) {
        console.error("Error fetching task:", error);
        toast.error("Failed to load task details");
        throw error;
      }
    },
    enabled: !!token && !!taskId,
  });

  // Fetch project stages
  const { data: stages = [], isLoading: isLoadingStages, error: stagesError } = useQuery<Stage[]>({
    queryKey: ["project-stages", id],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/projects/${id}/stages`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (response.status === 401) {
          toast.error("Please log in to view this content");
          throw new Error("Unauthorized");
        }
        
        if (!response.ok) {
          throw new Error(`Failed to fetch project stages: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("Stages Response:", data); // Debug log
        return data;
      } catch (error) {
        console.error("Error fetching stages:", error);
        toast.error("Failed to load project stages");
        throw error;
      }
    },
    enabled: !!token && !!id,
  });

  // Fetch milestones
  const { data: milestones = [], isLoading: isLoadingMilestones, refetch: refetchMilestones } = useQuery<Milestone[]>({
    queryKey: ["project-milestones", id],
    queryFn: async () => {
      try {
        console.log("Fetching milestones for project:", id); // Debug log
        const response = await fetch(`${API_BASE_URL}/milestones/project/${id}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 404) {
          console.log("No milestones found for project:", id); // Debug log
          return []; // Return empty array instead of throwing error
        }

        if (!response.ok) {
          throw new Error('Failed to fetch milestones');
        }

        const data = await response.json();
        console.log("Fetched milestones:", data); // Debug log
        return data;
      } catch (error) {
        console.error('Error fetching milestones:', error);
        toast.error('Failed to load milestones');
        return []; // Return empty array on error
      }
    },
    enabled: !!token && !!id,
  });

  // Fetch users
  const { data: users = [], isLoading: isLoadingUsers } = useQuery<User[]>({
    queryKey: ["users"],
    queryFn: async () => {
      try {
        console.log("Fetching users..."); // Debug log
        const response = await fetch(`${API_BASE_URL}/users/`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 401) {
          toast.error("Please log in to view this content");
          throw new Error("Unauthorized");
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch users: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("Users Response:", data); // Debug log
        return data;
      } catch (error) {
        console.error("Error fetching users:", error);
        toast.error("Failed to load users");
        return []; // Return empty array on error
      }
    },
    enabled: !!token,
  });

  // Fetch task activities
  const { data: taskActivities, isLoading: isLoadingActivities } = useQuery<Activity[]>({
    queryKey: ["task-activities", taskId],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/activities/task/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 401) {
          toast.error("Please log in to view this content");
          throw new Error("Unauthorized");
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch task activities: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
      } catch (error) {
        console.error('Error fetching task activities:', error);
        throw error;
      }
    },
    enabled: !!taskId && !!token,
  });

  // Group activities by date
  const groupedActivities = useMemo(() => {
    if (!taskActivities) return {};
    
    return taskActivities.reduce((groups: { [key: string]: Activity[] }, activity: Activity) => {
      const date = new Date(activity.created_at).toLocaleDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(activity);
      return groups;
    }, {});
  }, [taskActivities]);

  // Set current stage when task details are loaded
  useEffect(() => {
    if (taskDetails?.stage_id) {
      const stageId = taskDetails.stage_id.toString();
      console.log("Setting current stage to:", stageId); // Debug log
      setCurrentStage(stageId);
    }
  }, [taskDetails]);

  // Set selected assignees when task details are loaded
  useEffect(() => {
    if (taskDetails?.assignee) {
      setSelectedAssignees([taskDetails.assignee]);
    } else {
      setSelectedAssignees([]);
    }
  }, [taskDetails]);

  // Set deadline when task details are loaded
  useEffect(() => {
    if (taskDetails?.deadline) {
      // Convert the ISO string to local datetime-local format
      const date = new Date(taskDetails.deadline);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      setDeadline(`${year}-${month}-${day}T${hours}:${minutes}`);
    } else {
      setDeadline('');
    }
  }, [taskDetails]);

  // Update hasUnsavedChanges whenever any field changes
  useEffect(() => {
    setHasUnsavedChanges(
      isNameChanged || 
      isDeadlineChanged || 
      isAssigneesChanged ||
      isStatusChanged
    );
  }, [isNameChanged, isDeadlineChanged, isAssigneesChanged, isStatusChanged]);

  // Update currentStatus when task details are loaded
  useEffect(() => {
    if (taskDetails?.state) {
      // Validate that the state from the backend is a valid TaskState
      const stateFromBackend = taskDetails.state;
      if (Object.values(TaskState).includes(stateFromBackend as TaskState)) {
        setCurrentStatus(stateFromBackend as TaskState);
        setIsStatusChanged(false); // Reset the change flag when task details are loaded
      } else {
        // If the state is invalid, set it to IN_PROGRESS
        console.warn('Invalid task state received from backend:', stateFromBackend);
        setCurrentStatus(TaskState.IN_PROGRESS);
        setIsStatusChanged(false);
      }
    }
  }, [taskDetails]);

  const actionButtons = (
    <div className="flex items-center gap-2 overflow-x-auto pb-2">
      <Button variant="outline" size="sm" className="whitespace-nowrap">Send message</Button>
      <Button variant="outline" size="sm" className="whitespace-nowrap">Log note</Button>
      <Button variant="outline" size="sm" className="whitespace-nowrap">Activities</Button>
      <Button variant="outline" size="sm" className="flex items-center gap-2 whitespace-nowrap">
        <MessageSquare className="w-4 h-4" />
        Comments
      </Button>
    </div>
  );

  // Handle stage change
  const handleStageChange = async (stageId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/stage`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stage_id: stageId }),
      });

      if (!response.ok) {
        throw new Error('Failed to update task stage');
      }

      setCurrentStage(stageId);
      toast.success('Task stage updated successfully');
    } catch (error) {
      console.error('Error updating task stage:', error);
      toast.error('Failed to update task stage');
    }
  };

  // Filter milestones based on search
  const filteredMilestones = milestones.filter(milestone =>
    milestone.name.toLowerCase().includes(searchMilestone.toLowerCase())
  );

  // Calculate pagination
  const totalPages = Math.ceil(filteredMilestones.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentMilestones = filteredMilestones.slice(startIndex, endIndex);
  const paginationText = `${startIndex + 1}-${Math.min(endIndex, filteredMilestones.length)}/${filteredMilestones.length}`;

  // Handle milestone selection
  const handleMilestoneSelect = async (milestoneId: number | null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ milestone_id: milestoneId }),
      });

      if (!response.ok) {
        throw new Error('Failed to update milestone');
      }

      setShowDetailedMilestones(false);
      toast.success('Task milestone updated successfully');
      refetch(); // Refresh task data
    } catch (error) {
      console.error('Error updating milestone:', error);
      toast.error('Failed to update milestone');
    }
  };

  // Handle create milestone
  const handleCreateMilestone = async () => {
    try {
      // Format the date to YYYY-MM-DD
      const formattedDueDate = newMilestone.due_date ? new Date(newMilestone.due_date).toISOString().split('T')[0] : null;

      console.log("Creating milestone with data:", { ...newMilestone, due_date: formattedDueDate }); // Debug log

      const response = await fetch(`${API_BASE_URL}/milestones`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newMilestone,
          due_date: formattedDueDate,
          completed_date: null // Set initial completed_date as null
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to create milestone');
      }

      const createdMilestone = await response.json();
      console.log("Created milestone:", createdMilestone); // Debug log

      toast.success('Milestone created successfully');
      setShowCreateMilestone(false);
      setNewMilestone({
        name: "",
        description: "",
        project_id: Number(id),
        due_date: "",
        is_completed: false,
        is_active: true
      });
      
      // Refresh milestones list
      await refetchMilestones();
      console.log("Milestones refetched after creation"); // Debug log
    } catch (error) {
      console.error('Error creating milestone:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to create milestone');
    }
  };

  // Filter users based on search
  const filteredUsers = users.filter(user =>
    user.full_name?.toLowerCase().includes(searchUser.toLowerCase()) ||
    user.username?.toLowerCase().includes(searchUser.toLowerCase()) ||
    user.email?.toLowerCase().includes(searchUser.toLowerCase())
  );

  // Calculate pagination for users
  const userItemsPerPage = 5;
  const userTotalPages = Math.ceil(filteredUsers.length / userItemsPerPage);
  const userStartIndex = (userPage - 1) * userItemsPerPage;
  const userEndIndex = userStartIndex + userItemsPerPage;
  const currentUsers = filteredUsers.slice(userStartIndex, userEndIndex);
  const userPaginationText = `${userStartIndex + 1}-${Math.min(userEndIndex, filteredUsers.length)}/${filteredUsers.length}`;

  // Handle multiple assignee selection
  const handleAssigneeSelect = (user: User) => {
    // Check if the user is already selected
    const isAlreadySelected = selectedAssignees.some(a => a.id === user.id);
    
    if (isAlreadySelected) {
      // Remove user from selection
      const updatedAssignees = selectedAssignees.filter(a => a.id !== user.id);
      setSelectedAssignees(updatedAssignees);
      setIsAssigneesChanged(true);
    } else {
      // Add user to selection
      setSelectedAssignees([...selectedAssignees, user]);
      setIsAssigneesChanged(true);
    }
  };

  // Handle removing an assignee
  const handleRemoveAssignee = (userId: number) => {
    const updatedAssignees = selectedAssignees.filter(a => a.id !== userId);
    setSelectedAssignees(updatedAssignees);
    setIsAssigneesChanged(true);
  };

  // Handle unassign all
  const handleUnassignAll = () => {
    setSelectedAssignees([]);
    setIsAssigneesChanged(true);
  };

  // Handle save changes
  const handleSaveChanges = async () => {
    if (!taskId || !token) return;

    try {
      // If only status is changed, use the dedicated state update endpoint
      if (isStatusChanged && !isNameChanged && !isDeadlineChanged && !isAssigneesChanged) {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/state?state=${currentStatus}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          }
        });

        if (!response.ok) {
          const errorData = await response.json();
          console.error('Server response:', errorData);
          throw new Error(errorData.detail || 'Failed to update task state');
        }

        const updatedTask = await response.json();
        console.log('Task state updated successfully:', updatedTask);

        // Refresh task details and activities
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['task', taskId] }),
          queryClient.invalidateQueries({ queryKey: ['task-activities', taskId] })
        ]);

        // Reset change flags
        setIsStatusChanged(false);
        toast.success('Task status updated successfully');
        return;
      }

      // For other changes, use the general update endpoint
      const updatedFields: TaskUpdateFields = {};

      if (isNameChanged) {
        updatedFields.name = taskName;
      }
      if (isDeadlineChanged) {
        updatedFields.deadline = deadline ? new Date(deadline).toISOString() : null;
      }
      if (isAssigneesChanged) {
        updatedFields.assigned_to = selectedAssignees.length > 0 ? selectedAssignees[0].id : null;
      }

      // Debug logging
      console.log('Sending update with fields:', updatedFields);

      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedFields),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Server response:', errorData);
        throw new Error(errorData.detail || 'Failed to update task');
      }

      const updatedTask = await response.json();
      console.log('Task updated successfully:', updatedTask);

      // Refresh task details and activities
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['task', taskId] }),
        queryClient.invalidateQueries({ queryKey: ['task-activities', taskId] })
      ]);

      // Reset change flags
      setIsNameChanged(false);
      setIsDeadlineChanged(false);
      setIsAssigneesChanged(false);

      toast.success('Task updated successfully');
    } catch (error) {
      console.error('Error updating task:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to update task');
    }
  };

  // Check if user can access this task
  const canAccessTask = (task: Task | null | undefined) => {
    if (!task) return false;
    
    // Superusers can access all tasks
    if (useAuthStore.getState().user?.is_superuser) return true;
    
    const currentUserId = Number(useAuthStore.getState().user?.id);
    
    // Users can access tasks they created
    if (task.created_by === currentUserId) return true;
    
    // Users can access tasks assigned to them
    if (task.assigned_to === currentUserId) return true;
    
    return false;
  };

  // Loading states
  if (isLoadingTask || isLoadingStages || isLoadingMilestones || isLoadingUsers || isLoadingActivities) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">Loading task details...</div>
      </div>
    );
  }

  // Error states
  if (!token) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Authentication Required</h2>
          <p className="text-gray-600">Please log in to view this content</p>
        </div>
      </div>
    );
  }

  if (stagesError || taskError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error</h2>
          <p className="text-gray-600">
            {stagesError ? "Failed to load project stages" : "Failed to load task details"}
          </p>
        </div>
      </div>
    );
  }

  // Check permission to access this task
  if (taskDetails && !canAccessTask(taskDetails)) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Access Denied</h2>
          <p className="text-gray-600">
            You don&apos;t have permission to access this task. Only assigned users, the task creator, 
            or system administrators can view this task.
          </p>
          <Button 
            className="mt-4 bg-blue-800 text-white hover:bg-blue-900"
            onClick={() => window.history.back()}
          >
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  // Create Milestone Dialog
  const CreateMilestoneDialog = () => (
    <Dialog open={showCreateMilestone} onOpenChange={setShowCreateMilestone}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Create Milestone</DialogTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowCreateMilestone(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              placeholder="e.g. Product Launch"
              value={newMilestone.name}
              onChange={(e) => setNewMilestone({ ...newMilestone, name: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              placeholder="Enter milestone description..."
              value={newMilestone.description}
              onChange={(e) => setNewMilestone({ ...newMilestone, description: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Due Date</label>
            <Input
              type="date"
              value={newMilestone.due_date}
              onChange={(e) => setNewMilestone({ ...newMilestone, due_date: e.target.value })}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="completed"
              checked={newMilestone.is_completed}
              onCheckedChange={(checked) => 
                setNewMilestone({ ...newMilestone, is_completed: checked as boolean })
              }
            />
            <label 
              htmlFor="completed" 
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Completed
            </label>
          </div>
        </div>
        <div className="flex justify-between">
          <Button
            variant="default"
            className="bg-purple-600 hover:bg-purple-700 text-white"
            onClick={handleCreateMilestone}
          >
            Save & Close
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowCreateMilestone(false)}
          >
            Discard
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );

  // Milestone Selection Dialog
  const MilestoneDialog = () => (
    <Dialog open={showDetailedMilestones} onOpenChange={setShowDetailedMilestones}>
      <DialogContent className="sm:max-w-[800px]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Search: Milestone</DialogTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowDetailedMilestones(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>
        <div className="flex items-center justify-between mb-4">
          <Button variant="ghost" size="icon">
            <Settings className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2 flex-1 mx-4">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-500" />
              <Input
                placeholder="Search..."
                value={searchMilestone}
                onChange={(e) => setSearchMilestone(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          {filteredMilestones.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">{paginationText}</span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {isLoadingMilestones ? (
          <div className="py-8 text-center">
            <div className="animate-spin inline-block w-6 h-6 border-2 border-current border-t-transparent text-purple-600 rounded-full" />
            <p className="mt-2 text-sm text-gray-500">Loading milestones...</p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {currentMilestones.map((milestone) => (
                  <TableRow key={milestone.id}>
                    <TableCell>{milestone.name}</TableCell>
                    <TableCell>{milestone.description || '-'}</TableCell>
                    <TableCell>
                      {milestone.due_date ? new Date(milestone.due_date).toLocaleDateString() : '-'}
                    </TableCell>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={milestone.is_completed}
                        readOnly
                        className="h-4 w-4 rounded border-gray-300"
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMilestoneSelect(milestone.id)}
                      >
                        Select
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {currentMilestones.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8">
                      {searchMilestone ? (
                        <>
                          <p className="text-gray-500">No milestones found matching &quot;{searchMilestone}&quot;</p>
                          <Button
                            variant="link"
                            onClick={() => setSearchMilestone("")}
                            className="mt-2"
                          >
                            Clear search
                          </Button>
                        </>
                      ) : (
                        <p className="text-gray-500">No milestones found. Create one to get started.</p>
                      )}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            <div className="flex justify-between mt-4">
              <Button
                variant="default"
                size="sm"
                onClick={() => {
                  setShowDetailedMilestones(false);
                  setShowCreateMilestone(true);
                }}
              >
                New Milestone
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowDetailedMilestones(false)}
              >
                Close
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );

  // Assignee Selection Dialog
  const AssigneeDialog = () => (
    <Dialog open={showAssigneeSelection} onOpenChange={setShowAssigneeSelection}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Select Assignees</DialogTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowAssigneeSelection(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 flex-1">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-500" />
              <Input
                placeholder="Search users..."
                value={searchUser}
                onChange={(e) => setSearchUser(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          {filteredUsers.length > 0 && (
            <div className="flex items-center gap-2 ml-4">
              <span className="text-sm text-gray-500">{userPaginationText}</span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setUserPage(p => Math.max(1, p - 1))}
                disabled={userPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setUserPage(p => Math.min(userTotalPages, p + 1))}
                disabled={userPage === userTotalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {isLoadingUsers ? (
          <div className="py-8 text-center">
            <div className="animate-spin inline-block w-6 h-6 border-2 border-current border-t-transparent text-blue-600 rounded-full" />
            <p className="mt-2 text-sm text-gray-500">Loading users...</p>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={handleUnassignAll}
                disabled={selectedAssignees.length === 0}
              >
                <User className="mr-2 h-4 w-4" />
                <span>Unassign All</span>
              </Button>
              
              {currentUsers.map((user) => (
                <Button
                  key={user.id}
                  variant="outline"
                  className={`w-full justify-start ${selectedAssignees.some(a => a.id === user.id) ? 'bg-blue-50 border-blue-200' : ''}`}
                  onClick={() => handleAssigneeSelect(user)}
                >
                  <Avatar className="h-6 w-6 mr-2">
                    <span>{user.full_name?.charAt(0) || user.username?.charAt(0) || 'U'}</span>
                  </Avatar>
                  <div className="flex flex-col items-start">
                    <span>{user.full_name || user.username}</span>
                    <span className="text-xs text-gray-500">{user.email}</span>
                  </div>
                  {selectedAssignees.some(a => a.id === user.id) && (
                    <div className="ml-auto">
                      <ChevronRight className="h-4 w-4" />
                    </div>
                  )}
                </Button>
              ))}
              
              {filteredUsers.length === 0 && (
                <div className="text-center py-4">
                  <p className="text-gray-500">No users found matching &quot;{searchUser}&quot;</p>
                  {searchUser && (
                    <Button
                      variant="link"
                      onClick={() => setSearchUser("")}
                      className="mt-2"
                    >
                      Clear search
                    </Button>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-between mt-4">
              <Button
                variant="default"
                className="bg-blue-800 text-white hover:bg-blue-900"
                onClick={() => setShowAssigneeSelection(false)}
                disabled={selectedAssignees.length === 0}
              >
                {`Assign ${selectedAssignees.length} ${selectedAssignees.length === 1 ? 'Person' : 'People'}`}
              </Button>
              <Button
                variant="secondary"
                onClick={() => setShowAssigneeSelection(false)}
              >
                Cancel
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation with Stages and Actions */}
      <div className="container mx-auto px-6">
        <div className="flex justify-between items-center py-4">
          {/* Stage Navigation */}
          <div className="flex items-center gap-1.5">
            {hasUnsavedChanges && (
              <Button
                variant="default"
                size="sm"
                className="bg-blue-800 text-white hover:bg-blue-900"
                onClick={handleSaveChanges}
              >
                Save Changes
              </Button>
            )}
            {stages.slice(0, showAllStages ? stages.length : 4).map((stage) => {
              const isCurrentStage = stage.id.toString() === currentStage;
              console.log(`Stage ${stage.id} comparison:`, { 
                stageId: stage.id, 
                currentStage, 
                isCurrentStage,
                taskStageId: taskDetails?.stage_id 
              }); // Debug log
              
              return (
                <Button
                  key={stage.id}
                  variant={isCurrentStage ? "default" : "outline"}
                  className={`transition-all duration-200 ${
                    isCurrentStage
                      ? "bg-blue-800 text-white hover:bg-blue-900 ring-2 ring-blue-300" 
                      : "hover:bg-blue-50"
                  } h-8 px-3 justify-center relative`}
                  onClick={() => handleStageChange(stage.id)}
                >
                  <div className="flex items-center">
                    <span className="text-sm">{stage.name}</span>
                    {isCurrentStage && stage.duration && (
                      <span className="text-xs opacity-80 ml-1">({stage.duration})</span>
                    )}
                    {isCurrentStage && (
                      <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-blue-800 rotate-45" />
                    )}
                  </div>
                </Button>
              );
            })}
            
            {!showAllStages && stages.length > 4 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 px-2"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[200px]">
                  {stages.slice(4).map((stage) => (
                    <DropdownMenuItem
                      key={stage.id}
                      onClick={() => handleStageChange(stage.id)}
                      className={stage.id.toString() === currentStage ? "bg-purple-50" : ""}
                    >
                      {stage.name}
                      {stage.id.toString() === currentStage && (
                        <ChevronRight className="ml-auto h-4 w-4" />
                      )}
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuItem
                    onClick={() => setShowAllStages(true)}
                    className="border-t mt-1 pt-1"
                  >
                    View All Stages
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {/* Action Buttons - Desktop */}
          <div className="hidden lg:block">
            {actionButtons}
          </div>
            </div>
          </div>

      {/* Main Content */}
      <div className="container mx-auto px-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Main Content Area */}
          <div className="flex-grow order-1 lg:order-1">
            <div className="bg-white rounded-lg shadow p-6">
              {/* Task Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Star className="text-gray-400" />
                  {isLoadingTask ? (
                    <div className="h-7 w-32 bg-gray-100 animate-pulse rounded"></div>
                  ) : (
                    <div className="flex items-center gap-2">
                      {isEditingName ? (
                        <Input
                          value={taskName}
                          onChange={(e) => {
                            setTaskName(e.target.value);
                            setIsNameChanged(e.target.value !== taskDetails?.name);
                          }}
                          onBlur={() => setIsEditingName(false)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSaveChanges();
                            }
                          }}
                          className="text-xl font-medium h-8 py-0"
                          autoFocus
                />
              ) : (
                        <h1 
                          className="text-xl font-medium cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                          onClick={() => setIsEditingName(true)}
                        >
                          {taskName || "Task Name"}
                        </h1>
                      )}
                    </div>
                  )}
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      className={`${statusConfig[currentStatus]?.color || statusConfig[TaskState.IN_PROGRESS].color} flex items-center gap-2 px-3 py-1 rounded hover:opacity-90`}
                    >
                      <span>{statusConfig[currentStatus]?.icon || statusConfig[TaskState.IN_PROGRESS].icon}</span>
                      <span className="capitalize">{currentStatus.replace(/_/g, ' ')}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-[200px]">
                    {Object.values(TaskState).map((status) => (
                      <DropdownMenuItem
                        key={status}
                        onClick={() => {
                          setCurrentStatus(status);
                          setIsStatusChanged(true);
                        }}
                        className={`flex items-center gap-2 ${currentStatus === status ? 'bg-gray-100' : ''}`}
                      >
                        <span>{statusConfig[status].icon}</span>
                        <span className="capitalize">{status.replace(/_/g, ' ')}</span>
                        {currentStatus === status && (
                          <ChevronRight className="ml-auto h-4 w-4" />
                        )}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Task Details Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
                  <Input placeholder="Select project..." value="comments" readOnly />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Milestone</label>
                  <div className="relative">
                    <Input
                      placeholder="Select milestone..."
                      value={taskDetails?.milestone?.name || ""}
                      onClick={() => setShowDetailedMilestones(true)}
                      readOnly
                      className="cursor-pointer"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Assignees</label>
                  <div className="space-y-2">
                    <div 
                      className="flex items-center cursor-pointer border rounded-md p-2 hover:bg-gray-50"
                      onClick={() => setShowAssigneeSelection(true)}
                    >
                      {selectedAssignees.length === 0 ? (
                        <span className="text-gray-500">Click to assign users</span>
                      ) : (
                        <div className="flex flex-wrap gap-2 items-center">
                          {selectedAssignees.map(user => (
                            <div 
                              key={user.id} 
                              className="flex items-center bg-blue-50 rounded-full py-1 px-2 gap-1"
                            >
                              <Avatar className="h-5 w-5">
                                <span>{user.full_name?.charAt(0) || user.username?.charAt(0) || 'U'}</span>
                              </Avatar>
                              <span className="text-sm">{user.full_name || user.username}</span>
                              <X 
                                className="h-3 w-3 cursor-pointer" 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRemoveAssignee(user.id);
                                }}
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
                  <Input placeholder="Add tags..." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Customer</label>
                  <Input placeholder="Select customer..." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Allocated Time</label>
                  <div className="flex items-center gap-2">
                    <Input type="time" defaultValue="00:00" />
                    <span className="text-gray-500">(0%)</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Deadline</label>
                  <Input 
                    type="datetime-local" 
                    value={deadline || ''}
                    onChange={(e) => {
                      const newDeadline = e.target.value;
                      setDeadline(newDeadline);
                      setIsDeadlineChanged(newDeadline !== taskDetails?.deadline);
                    }}
                  />
                </div>
              </div>

              {/* Tabs Navigation */}
              <div className="border-b mb-6 overflow-x-auto">
                <nav className="flex gap-4 min-w-max">
                  <Button variant="ghost" className="text-purple-700 border-b-2 border-purple-700 rounded-none px-0">
                    Description
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Timesheets
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Sub-tasks
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Extra Info
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Checklist
                  </Button>
                </nav>
              </div>

              {/* Description Area */}
              <Textarea
                placeholder="Add details about this task..."
                className="min-h-[200px] w-full"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>

          {/* Action Buttons and Activity Feed for Mobile */}
          <div className="lg:w-80 order-2 lg:order-2">
            {/* Mobile Action Buttons */}
            <div className="lg:hidden mb-4">
              {actionButtons}
            </div>

            {/* Activity Feed */}
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium text-lg">Activity Feed</h3>
              </div>

              {isLoadingActivities ? (
                <div className="flex justify-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600" />
                </div>
              ) : Object.entries(groupedActivities).length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">
                  No activities recorded yet
                </p>
              ) : (
                Object.entries(groupedActivities).map(([date, dateActivities]: [string, Activity[]]) => (
                  <div key={date} className="mb-6">
                    <div className="flex items-center mb-3">
                      <h3 className="text-sm font-medium text-gray-500">
                        {date === new Date().toLocaleDateString() ? 'Today' : date}
                      </h3>
                      <div className="flex-1 ml-3 border-t border-gray-200" />
                    </div>

                    <div className="space-y-4">
                      {dateActivities.map((activity: Activity) => (
                        <div key={activity.id} className="flex items-start gap-3">
                          <Avatar className="w-8 h-8">
                            <AvatarImage 
                              src={activity.user.profile_image_url || '/default-avatar.png'} 
                              alt={activity.user.full_name} 
                            />
                            <AvatarFallback>
                              {activity.user.full_name.charAt(0)}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1">
                            <div className="flex items-baseline gap-2">
                              <span className="text-sm text-gray-500">
                                {new Date(activity.created_at).toLocaleTimeString([], { 
                                  hour: '2-digit', 
                                  minute: '2-digit' 
                                })}
                              </span>
                            </div>
                            <div className="mt-1">
                              {activity.activity_type === 'task_update' && (
                                <div className="text-sm">
                                  {activity.description.includes('→') ? (
                                    <div className="flex items-center gap-2">
                                      <span className="text-gray-600">{activity.user.full_name}</span>
                                      {activity.description.toLowerCase().includes('status') ? (
                                        <>
                                          <span className="text-gray-500">changed status from</span>
                                          <span className="text-gray-600">{activity.description.split('→')[0].split(':')[1].trim()}</span>
                                          <ChevronRight className="h-4 w-4 text-gray-400" />
                                          <span className={`font-medium ${
                                            activity.description.toLowerCase().includes('done') ? 'text-green-600' :
                                            activity.description.toLowerCase().includes('in progress') ? 'text-blue-600' :
                                            activity.description.toLowerCase().includes('changes requested') ? 'text-orange-600' :
                                            activity.description.toLowerCase().includes('approved') ? 'text-green-600' :
                                            activity.description.toLowerCase().includes('canceled') ? 'text-red-600' :
                                            'text-gray-600'
                                          }`}>
                                            {activity.description.split('→')[1].trim()}
                                          </span>
                                        </>
                                      ) : (
                                        <>
                                          <span>{activity.description.split('→')[0]}</span>
                                          <ChevronRight className="h-4 w-4 text-gray-400" />
                                          <span className="font-medium">{activity.description.split('→')[1]}</span>
                                        </>
                                      )}
                                    </div>
                                  ) : (
                                    <div className="flex items-center gap-2">
                                      <span className="text-gray-600">{activity.user.full_name}</span>
                                      <span className="text-gray-500">{activity.description}</span>
                                    </div>
                                  )}
                                </div>
                              )}
                              {activity.activity_type === 'comment' && (
                                <div className="text-sm bg-gray-50 rounded-md p-3 mt-1">
                                  {activity.description}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Render all dialogs */}
      <MilestoneDialog />
      <CreateMilestoneDialog />
      <AssigneeDialog />
    </div>
  );
}