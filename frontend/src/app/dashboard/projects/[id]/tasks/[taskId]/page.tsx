"use client";

import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MessageSquare, Star, MoreHorizontal, ChevronRight, Search, Settings, ChevronLeft, X, User, Paperclip, Pencil, ChevronUp, Users } from "lucide-react";
import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import React from "react";
import { API_BASE_URL, DEFAULT_AVATAR_URL } from "@/lib/constants";
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
import "@/styles/tags.css";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import { patchApi, postApi, putApi } from "@/lib/api-helper";

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
  profile_image_url: string | null;
}

interface ActivityUser {
  id: number;
  username: string;
  full_name: string;
  profile_image_url: string | null;
}

interface Tag {
  id: number;
  name: string;
  color: number;
  active: boolean;
}

interface Task {
  id: number;
  name: string;
  description: string;
  stage_id: number;
  milestone_id?: number;
  milestone?: {
    id: number;
    name: string;
  };
  assigned_to?: number;
  assignee?: User;
  created_by: number;
  deadline?: string;
  state: TaskState;
  tags: Tag[];
  comments: Comment[];
  planned_hours?: number;
}

type ActivityType = 'task_update' | 'comment' | 'log_note' | 'message';

interface Activity {
  id: number;
  activity_type: ActivityType;
  description: string;
  created_at: string;
  user: {
    id: number;
    username: string;
    full_name: string;
    profile_image_url: string | null;
  };
  user_id?: number;
  uniqueId?: string;
  attachments?: Array<{
    id: number;
    filename: string;
    original_filename: string;
    content_type: string;
  }>;
}

interface Comment {
  id: number;
  content: string;
  created_at: string;
  user: ActivityUser;
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
  description?: string;
  stage_id?: number;
  planned_hours?: number;
}

interface LogNote {
  id: number;
  content: string;
  created_at: string;
  user: {
    id: number;
    username: string;
    full_name: string;
    profile_image_url: string | null;
  };
  attachments: Array<{
    id: number;
    filename: string;
    original_filename: string;
    content_type: string;
  }>;
}

interface Task {
  id: number;
  title: string;
  description: string;
  comments: Comment[];
}

// Add TaskStage interface
interface TaskStage {
  id: number;
  name: string;
  sequence: number;
  description?: string;
  project_id: number;
  tasks?: Task[];
  duration?: string;
}

// Add interfaces for activity feed items
interface BaseActivityItem {
  id: number;
  created_at: string;
  user: ActivityUser;
}

interface LogNote extends BaseActivityItem {
  content: string;
  attachments: Array<{
    id: number;
    filename: string;
    original_filename: string;
    content_type: string;
  }>;
}

interface ActivityItem extends BaseActivityItem {
  activity_type: 'task_update' | 'comment' | 'message';
  description: string;
}

type FeedItem = LogNote | ActivityItem;

// Add Message interface
interface Message {
  id: number;
  content: string;
  created_at: string;
  sender: User;
  task_id: number;
}

export default function TaskDetails({ params }: TaskDetailsProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  
  // Unwrap params at the very start of the component
  const resolvedParams = React.use(params);
  const { id, taskId } = resolvedParams;

  // Constants
  const itemsPerPage = 4;

  // Auth store
  const { token, checkAuth } = useAuthStore();

  // Add state for log note form
  const [content, setContent] = useState("");
  
  // Change showMessageDialog to showMessageInput
  const [showMessageInput, setShowMessageInput] = useState(false);
  const [messageText, setMessageText] = useState("");
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  // Task query with loading and error states
  const { 
    isLoading: isLoadingTask, 
    error: taskError,
    refetch: refetchTask
  } = useQuery({
    queryKey: ['task', taskId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to fetch task');
      return response.json();
    },
    enabled: !!token && !!taskId,
  });

  // Milestones query with loading state
  const { data: milestonesData, isLoading: isLoadingMilestones, refetch: refetchMilestones } = useQuery({
    queryKey: ['milestones', id],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/milestones/project/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to fetch milestones');
      return response.json();
    },
    enabled: !!token && !!id,
  });

  // Users query with loading state
  const { data: usersData, isLoading: isLoadingUsers } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('You do not have permission to view users');
        }
        throw new Error('Failed to fetch users');
      }
      return response.json();
    },
    enabled: !!token,
    retry: false
  });

  // Stages query with loading and error states
  const { data: stagesData, isLoading: isLoadingStages, error: stagesError } = useQuery({
    queryKey: ['stages', id],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/stages/project/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to fetch stages');
      const data = await response.json();
      
      // Transform the data to use assignee_data instead of assignee
      return data.map((stage: any) => ({
        ...stage,
        tasks: stage.tasks?.map((task: any) => ({
          ...task,
          assignee: task.assignee_data || task.assignee
        }))
      }));
    },
    enabled: !!token && !!id,
  });

  // Activities query with loading state
  const { 
    data: activitiesData, 
    isLoading: isLoadingActivities
  } = useQuery({
    queryKey: ['activities', resolvedParams.taskId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/activities/task/${resolvedParams.taskId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to fetch activities');
      return response.json();
    },
    enabled: !!token && !!resolvedParams.taskId,
    refetchInterval: 5000, // Refetch every 5 seconds
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    staleTime: 0 // Consider data stale immediately
  });

  // Add log notes query
  const { data: logNotesData, isLoading: isLoadingLogNotes } = useQuery({
    queryKey: ['log-notes', resolvedParams.taskId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/log-notes/task/${resolvedParams.taskId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to fetch log notes');
      const data = await response.json();
      return data;
    },
    enabled: !!token && !!resolvedParams.taskId,
    refetchInterval: 5000, // Refetch every 5 seconds
    refetchOnWindowFocus: true,
    refetchOnMount: true,
  });

  // Derived state
  const users = usersData || [];
  const milestones = milestonesData || [];
  const stages = stagesData || [];
  const activities = activitiesData || [];

  // State declarations
  const [currentStage, setCurrentStage] = useState<string>("");
  const [description, setDescription] = useState("");
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
  const [showLogForm, setShowLogForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commentText, setCommentText] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [isDescriptionChanged, setIsDescriptionChanged] = useState(false);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [selectedTags, setSelectedTags] = useState<Tag[]>([]);
  const [currentStatus, setCurrentStatus] = useState<TaskState>(TaskState.IN_PROGRESS);
  const [isStatusChanged, setIsStatusChanged] = useState(false);
  const [task, setTask] = useState<Task | null>(null);
  const [taskActivities, setTaskActivities] = useState<Activity[]>([]);
  const [logNotes, setLogNotes] = useState<LogNote[]>([]);
  const [isTagPopoverOpen, setIsTagPopoverOpen] = useState(false);
  // Additional state declarations
  const [showTagDialog, setShowTagDialog] = useState(false);
  const [isStageChanged, setIsStageChanged] = useState(false);
  const [newStageId, setNewStageId] = useState<string | null>(null);
  // Add state for tracking original stage
  const [originalStageName, setOriginalStageName] = useState<string>("");
  const [showScrollToLatest, setShowScrollToLatest] = useState(false);
  const activityFeedRef = useRef<HTMLDivElement>(null);
  const [allocatedTime, setAllocatedTime] = useState<string>("");
  const [isAllocatedTimeChanged, setIsAllocatedTimeChanged] = useState(false);

  // Add scroll handler to show/hide scroll to latest button
  const handleActivityScroll = useCallback(() => {
    if (!activityFeedRef.current) return;
    
    const { scrollTop } = activityFeedRef.current;
    // Show button if scrolled down more than 100px
    setShowScrollToLatest(scrollTop > 100);
  }, []);

  // Scroll to latest function
  const scrollToLatest = useCallback(() => {
    if (!activityFeedRef.current) return;
    activityFeedRef.current.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  }, []);

  // Helper function to check if task exists and has required data
  const hasTaskData = () => {
    return task && task.id && task.name;
  };

  // Helper function to get task name safely
  const getTaskName = () => {
    return task?.name || taskName;
  };

  // Helper function to get task description safely
  const getTaskDescription = () => {
    return task?.description || description;
  };

  // Helper function to get task deadline safely
  const getTaskDeadline = () => {
    return task?.deadline || deadline;
  };

  // Helper function to get task state safely
  const getTaskState = () => {
    return task?.state || currentStatus;
  };

  // Helper function to get task comments safely
  const getTaskComments = () => {
    return task?.comments || [];
  };

  // Authentication check effect
  useEffect(() => {
    const validateAuth = async () => {
      try {
        const isAuthenticated = await checkAuth();
        if (!isAuthenticated) {
          toast.error("Your session has expired. Please log in again.");
          router.push('/auth/login');
          return;
        }
      } catch (error) {
        console.error("Authentication error:", error);
        toast.error("Authentication failed. Please log in again.");
        router.push('/auth/login');
      }
    };
    validateAuth();
  }, [checkAuth, router]);

  // Fetch task effect
  useEffect(() => {
    const fetchTask = async () => {
      if (!token || !taskId) return;
      
      try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          setTask(data);
          setTaskName(data.name);
          setDescription(data.description || "");
          setDeadline(data.deadline);
          setCurrentStage(data.stage_id);
          setCurrentStatus(data.state);
          setAllocatedTime(data.planned_hours?.toString() || "");
        } else {
          setError("Failed to load task details");
        }
      } catch (error) {
        console.error("Error fetching task:", error);
        setError("Failed to load task details");
      } finally {
        setLoading(false);
      }
    };

    fetchTask();
  }, [taskId, token]);

  // Fetch task activities effect
  useEffect(() => {
    const fetchActivities = async () => {
      if (!token || !taskId) return;

      try {
        const response = await fetch(`${API_BASE_URL}/activities/task/${taskId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setTaskActivities(data);
        } else {
          console.error("Failed to fetch task activities");
        }
      } catch (error) {
        console.error("Error fetching task activities:", error);
      }
    };

    fetchActivities();
  }, [taskId, token]);

  // Fetch log notes effect
  useEffect(() => {
    const fetchLogNotes = async () => {
      if (!token || !resolvedParams.taskId) return;
      
      try {
        console.log('Fetching log notes for task:', resolvedParams.taskId);
        const response = await fetch(`${API_BASE_URL}/log-notes/task/${resolvedParams.taskId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include',
          mode: 'cors'
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          console.error('Error response from server:', errorData);
          throw new Error(errorData?.detail || 'Failed to fetch log notes');
        }
        
          const data = await response.json();
        console.log('Log notes fetched successfully:', data);
          setLogNotes(data);
      } catch (error) {
        console.error('Error fetching log notes:', error);
        setError('Failed to fetch log notes');
      }
    };

    if (resolvedParams.taskId) {
      fetchLogNotes();
    }
  }, [resolvedParams.taskId, token]);

  // Fetch comments
  const { data: comments = [], isLoading: isLoadingComments } = useQuery<Comment[]>({
    queryKey: ['task-comments', taskId],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/comments/task/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch comments');
        }

        return response.json();
      } catch (error) {
        console.error('Error fetching comments:', error);
        return [];
      }
    },
    enabled: !!token && !!taskId,
  });

  // Fetch tags
  const { data: tags = [], isLoading: isLoadingTags } = useQuery<Tag[]>({
    queryKey: ["tags"],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tags/`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch tags');
        }

        return response.json();
      } catch (error) {
        console.error('Error fetching tags:', error);
        return [];
      }
    },
    enabled: !!token,
  });

  // Update the groupedActivities calculation
  const groupedActivities = useMemo(() => {
    if (!taskActivities || !comments || !logNotesData) return {};
    
    // Combine activities, comments, and log notes into a single array with unique keys
    const allItems = [
      ...(taskActivities || []).map((activity: Activity) => ({
        ...activity,
        uniqueId: `activity-${activity.id}`,
        user: activity.user || {
          id: activity.user_id || 0,
          username: 'Unknown',
          full_name: 'Unknown User',
          profile_image_url: null
        }
      })),
      ...(comments || []).map((comment: Comment): Activity => ({
        id: Number(comment.id),
        uniqueId: `comment-${comment.id}`,
        activity_type: 'comment',
        description: comment.content,
        created_at: comment.created_at,
        user: comment.user
      })),
      ...(logNotesData || []).map((logNote: any): Activity => ({
        id: logNote.id,
        uniqueId: `log-${logNote.id}`,
        activity_type: 'log_note',
        description: logNote.content,
        created_at: logNote.created_at,
        user: logNote.user,
        attachments: logNote.attachments
      }))
    ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    // Group by date
    return allItems.reduce<{ [key: string]: Activity[] }>((groups, item) => {
      const date = new Date(item.created_at).toLocaleDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(item);
      return groups;
    }, {});
  }, [taskActivities, comments, logNotesData]);

  // Update effects to use task state instead of taskDetails
  useEffect(() => {
    if (task?.stage_id) {
      const stageId = task.stage_id.toString();
      console.log("Setting current stage to:", stageId);
      setCurrentStage(stageId);
    }
  }, [task]);

  useEffect(() => {
    if (task?.assignee) {
      setSelectedAssignees([task.assignee]);
    } else {
      setSelectedAssignees([]);
    }
  }, [task]);

  useEffect(() => {
    if (task?.deadline) {
      // Convert the ISO string to local datetime-local format
      const date = new Date(task.deadline);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      setDeadline(`${year}-${month}-${day}T${hours}:${minutes}`);
    } else {
      setDeadline('');
    }
  }, [task]);

  // Update hasUnsavedChanges whenever any field changes
  useEffect(() => {
    setHasUnsavedChanges(
      isNameChanged || 
      isDeadlineChanged || 
      isAssigneesChanged ||
      isStatusChanged ||
      isStageChanged ||
      isAllocatedTimeChanged
    );
  }, [isNameChanged, isDeadlineChanged, isAssigneesChanged, isStatusChanged, isStageChanged, isAllocatedTimeChanged]);

  // Update currentStatus when task details are loaded
  useEffect(() => {
    if (task?.state) {
      // Validate that the state from the backend is a valid TaskState
      const stateFromBackend = task.state;
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
  }, [task]);

  // Set initial selected tags when task is loaded
  useEffect(() => {
    if (task?.tags) {
      console.log('Setting tags from task:', task.tags);
      setSelectedTags(task.tags);
    }
  }, [task]);

  // Update allocatedTime when task details are loaded
  useEffect(() => {
    if (task?.planned_hours !== undefined) {
      setAllocatedTime(task.planned_hours.toString());
      setIsAllocatedTimeChanged(false);
    }
  }, [task]);

  const actionButtons = (
    <div className="flex items-center gap-2 overflow-x-auto pb-2">
      <Button 
        variant="outline" 
        size="sm" 
        className="whitespace-nowrap"
        onClick={() => setShowMessageInput(prev => !prev)}
      >
        Send message
      </Button>
      <Button 
        variant="outline" 
        size="sm" 
        className="flex items-center gap-2 whitespace-nowrap"
        onClick={() => setShowLogForm(true)}
      >
        <Pencil className="w-4 h-4" />
        Log note
      </Button>
      <Button 
        variant="outline" 
        size="sm" 
        className="flex items-center gap-2 whitespace-nowrap"
        onClick={() => setShowCommentInput(prev => !prev)}
      >
        <MessageSquare className="w-4 h-4" />
        Comments
      </Button>
      <Button 
        variant="outline" 
        size="sm" 
        className="flex items-center gap-2 whitespace-nowrap"
      >
        <Paperclip className="w-4 h-4" />
        <span>0</span>
      </Button>
      <Button 
        variant="outline" 
        size="sm" 
        className="flex items-center gap-2 whitespace-nowrap"
      >
        <Users className="w-4 h-4" />
        <span>0</span>
      </Button>
    </div>
  );

  // Handle stage change
  const handleStageChange = (stageId: number) => {
    // Store the original stage name before changing
    const currentStageName = stages.find((s: TaskStage) => s.id.toString() === currentStage)?.name || "Unknown Stage";
    setOriginalStageName(currentStageName);
    
    setNewStageId(stageId.toString());
    setIsStageChanged(true);
      setCurrentStage(stageId.toString());
  };

  // Type-safe filter functions
  const filteredMilestones = milestones.filter((milestone: Milestone) =>
    milestone.name.toLowerCase().includes(searchMilestone.toLowerCase())
  );

  const filteredUsers = users.filter((user: User) =>
    user.full_name?.toLowerCase().includes(searchUser.toLowerCase()) ||
    user.username?.toLowerCase().includes(searchUser.toLowerCase()) ||
    user.email?.toLowerCase().includes(searchUser.toLowerCase())
  );

  // Calculate pagination
  const totalPages = Math.ceil(filteredMilestones.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentMilestones = filteredMilestones.slice(startIndex, endIndex);
  const paginationText = `${startIndex + 1}-${Math.min(endIndex, filteredMilestones.length)}/${filteredMilestones.length}`;

  // Handle milestone selection
  const handleMilestoneSelect = async (milestone: Milestone) => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ milestone_id: milestone.id }),
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
    if (!resolvedParams.taskId || !token) return;

    try {
      const updatedFields: TaskUpdateFields = {};
      const activities = [];

      if (isNameChanged) {
        updatedFields.name = taskName;
        activities.push({
          activity_type: 'task_update',
          description: `Changed task title from "${task?.name}" to "${taskName}"`,
          task_id: Number(resolvedParams.taskId),
          project_id: Number(id),
          user_id: useAuthStore.getState().user?.id
        });
      }
      if (isDeadlineChanged) {
        updatedFields.deadline = deadline ? new Date(deadline).toISOString() : null;
        const oldDeadline = task?.deadline ? new Date(task.deadline).toLocaleString() : 'none';
        const newDeadline = deadline ? new Date(deadline).toLocaleString() : 'none';
        activities.push({
          activity_type: 'task_update',
          description: `Updated task deadline from ${oldDeadline} to ${newDeadline}`,
          task_id: Number(resolvedParams.taskId),
          project_id: Number(id),
          user_id: useAuthStore.getState().user?.id
        });
      }
      if (isAssigneesChanged) {
        updatedFields.assigned_to = selectedAssignees.length > 0 ? selectedAssignees[0].id : null;
        const oldAssignee = task?.assignee?.full_name || 'none';
        const newAssignee = selectedAssignees.length > 0 ? selectedAssignees[0].full_name : 'none';
        activities.push({
          activity_type: 'task_update',
          description: `Changed task assignee from ${oldAssignee} to ${newAssignee}`,
          task_id: Number(resolvedParams.taskId),
          project_id: Number(id),
          user_id: useAuthStore.getState().user?.id
        });
      }
      if (isDescriptionChanged) {
        updatedFields.description = description;
        activities.push({
          activity_type: 'task_update',
          description: `Updated task description`,
          task_id: Number(resolvedParams.taskId),
          project_id: Number(id),
          user_id: useAuthStore.getState().user?.id
        });
      }
      if (isStatusChanged) {
        updatedFields.state = currentStatus;
        const oldStatus = task?.state || 'none';
        activities.push({
          activity_type: 'task_update',
          description: `Changed task status from ${oldStatus} to ${currentStatus}`,
          task_id: Number(resolvedParams.taskId),
          project_id: Number(id),
          user_id: useAuthStore.getState().user?.id
        });
      }
      if (isAllocatedTimeChanged) {
        updatedFields.planned_hours = parseFloat(allocatedTime);
        const oldTime = task?.planned_hours || 0;
        const newTime = parseFloat(allocatedTime);
        activities.push({
          activity_type: 'task_update',
          description: `Updated allocated time from ${oldTime} hours to ${newTime} hours`,
          task_id: Number(resolvedParams.taskId),
          project_id: Number(id),
          user_id: useAuthStore.getState().user?.id
        });
      }

      // First update the task details using patchApi helper
      await putApi(`/tasks/${resolvedParams.taskId}`, updatedFields);

      // Create activities for all changes
      for (const activityData of activities) {
        await postApi('/activities/', activityData);
      }

      // If stage was changed, handle stage update
      if (isStageChanged && newStageId) {
        try {
          // Get the new stage name
          const newStage = stages.find((s: TaskStage) => s.id.toString() === newStageId)?.name || 'Unknown Stage';

          console.log('Moving task to new stage:', {
            taskId: resolvedParams.taskId,
            newStageId,
            fromStage: originalStageName,
            toStage: newStage
          });

          // Use postApi helper for stage change
          await postApi(`/stages/${newStageId}/tasks/${resolvedParams.taskId}`, {});

          // Create activity log for stage change
          await postApi('/activities/', {
            task_id: Number(resolvedParams.taskId),
            project_id: Number(id),
            activity_type: 'task_update',
            description: `Changed task stage from "${originalStageName}" to "${newStage}"`,
            user_id: useAuthStore.getState().user?.id,
            created_at: new Date().toISOString()
          });

          // Update local state
          setCurrentStage(newStageId);
          setOriginalStageName("");
          
          // Reset stage change flag
          setIsStageChanged(false);
          setNewStageId(null);
        } catch (error) {
          console.error('Stage update error:', error);
          toast.error(error instanceof Error ? error.message : 'Failed to update task stage');
          throw error;
        }
      }

      // Reset all change flags
      setIsNameChanged(false);
      setIsDeadlineChanged(false);
      setIsAssigneesChanged(false);
      setIsDescriptionChanged(false);
      setIsStatusChanged(false);
      setIsStageChanged(false);
      setIsAllocatedTimeChanged(false);
      setNewStageId(null);

      // Refresh all data
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['task', resolvedParams.taskId] }),
        queryClient.invalidateQueries({ queryKey: ['activities', resolvedParams.taskId] }),
        queryClient.invalidateQueries({ queryKey: ['task-comments', resolvedParams.taskId] }),
        queryClient.invalidateQueries({ queryKey: ['stages', id] })
      ]);

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

  // Update the handleSendComment function
  const handleSendComment = async () => {
    if (!commentText.trim()) return;

    // Create optimistic comment
    const optimisticComment = {
      id: Date.now(),
      activity_type: 'comment' as const,
      description: commentText,
      created_at: new Date().toISOString(),
      user: useAuthStore.getState().user,
      uniqueId: `temp-comment-${Date.now()}`
    };

    // Optimistically update the activities
    queryClient.setQueryData(['activities', taskId], (old: Activity[] = []) => {
      return [optimisticComment, ...old];
    });

    try {
      const response = await fetch(`${API_BASE_URL}/comments/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          content: commentText,
          task_id: Number(taskId),
          parent_id: null,
          notification_type: 'task_comment' // Add the correct notification type
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to send comment');
      }

      // Clear the input and hide comment box
      setCommentText('');
      setShowCommentInput(false);

      // Refresh both task activities and comments
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['activities', taskId] }),
        queryClient.invalidateQueries({ queryKey: ['task-comments', taskId] })
      ]);

      toast.success('Comment added successfully');
    } catch (error) {
      // Revert optimistic update on error
      await queryClient.invalidateQueries({ queryKey: ['activities', taskId] });
      console.error('Error sending comment:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to add comment');
    }
  };

  // Update the filteredTags calculation
  const filteredTags = useMemo(() => {
    return tags.filter(tag => 
      tag.name.toLowerCase().includes(tagInput.toLowerCase()) &&
      !selectedTags.some(selectedTag => selectedTag.id === tag.id)
    );
  }, [tags, tagInput, selectedTags]);

  // Update the handleTagSelect function
  const handleTagSelect = async (tag: Tag) => {
    try {
      console.log('Attempting to add tag:', tag.id, 'to task:', taskId);

      // Check if tag is already selected locally
      if (selectedTags.some(t => t.id === tag.id)) {
        console.log('Tag already selected locally:', tag);
        setIsTagPopoverOpen(false);
        setTagInput('');
        return;
      }

      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/tags/${tag.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        if (data?.detail?.includes('already')) {
          console.log('Tag already exists on server, updating UI');
          setSelectedTags(prev => [...prev, tag]);
          setIsTagPopoverOpen(false);
          setTagInput('');
          return;
        }
        throw new Error(data?.detail || 'Failed to add tag to task');
      }

      console.log('Tag added successfully:', data);

      // Update local state immediately
      setSelectedTags(prev => [...prev, tag]);
      
      // Close the popover
      setIsTagPopoverOpen(false);
      
      // Clear the input
      setTagInput('');
      
      // Show success message
      toast.success('Tag added successfully');

      // Refresh task details to get the updated tags
      await refetchTask();
    } catch (error) {
      console.error('Error adding tag:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to add tag');
    }
  };

  // Update the handleTagRemove function
  const handleTagRemove = async (tagId: number) => {
    try {
      console.log('Attempting to remove tag:', tagId, 'from task:', taskId);

      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/tags/${tagId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || 'Failed to remove tag from task');
      }

      // Update local state
      setSelectedTags(prev => prev.filter(tag => tag.id !== tagId));
      
      // Show success message
      toast.success('Tag removed successfully');

      // Refresh task details
      await refetchTask();
    } catch (error) {
      console.error('Error removing tag:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to remove tag');
    }
  };

  // Add this helper function at the top level of your component
  const getTagColorClass = (colorIndex: number) => {
    const colors = {
      1: 'bg-blue-50 text-blue-700',
      2: 'bg-purple-50 text-purple-700',
      3: 'bg-green-50 text-green-700',
      4: 'bg-orange-50 text-orange-700',
      5: 'bg-pink-50 text-pink-700',
      6: 'bg-cyan-50 text-cyan-700',
      7: 'bg-lime-50 text-lime-700',
      8: 'bg-amber-50 text-amber-700',
      9: 'bg-stone-50 text-stone-700',
      10: 'bg-indigo-50 text-indigo-700',
      11: 'bg-red-50 text-red-700',
    };
    return colors[colorIndex as keyof typeof colors] || colors[1];
  };

  // Handle tag input change
  const handleTagInputChange = (value: string) => {
    setTagInput(value);
  };

  // Handle creating a new tag
  const handleCreateNewTag = async () => {
    if (!tagInput.trim()) return;

    try {
      // Check if tag already exists
      const existingTag = tags.find(t => t.name.toLowerCase() === tagInput.trim().toLowerCase());
      if (existingTag) {
        await handleTagSelect(existingTag);
        setTagInput("");
        return;
      }

      const response = await fetch(`${API_BASE_URL}/tags/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: tagInput.trim(),
          color: Math.floor(Math.random() * 11) + 1,
          active: true
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create tag');
      }

      const newTag = await response.json();
      await handleTagSelect(newTag);
      setTagInput("");
    } catch (error) {
      console.error('Error creating tag:', error);
      toast.error('Failed to create tag');
    }
  };

  // Add handleSendMessage function
  const handleSendMessage = async () => {
    if (!messageText.trim() || isSendingMessage) return;

    // Create optimistic message
    const optimisticMessage = {
      id: Date.now(),
      activity_type: 'message' as const,
      description: messageText,
      created_at: new Date().toISOString(),
      user: useAuthStore.getState().user,
      uniqueId: `temp-message-${Date.now()}`
    };

    // Optimistically update the activities
    queryClient.setQueryData(['activities', taskId], (old: Activity[] = []) => {
      return [optimisticMessage, ...old];
    });

    setIsSendingMessage(true);
    try {
      const response = await fetch(`${API_BASE_URL}/messages/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: messageText,
          task_id: Number(taskId),
          message_type: 'task_message'
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to send message');
      }

      // Clear input and close dialog
      setMessageText('');
      setShowMessageInput(false);

      // Refresh activities
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['activities', taskId] }),
        queryClient.invalidateQueries({ queryKey: ['messages', taskId] })
      ]);

      toast.success('Message sent successfully');
    } catch (error) {
      // Revert optimistic update on error
      await queryClient.invalidateQueries({ queryKey: ['activities', taskId] });
      console.error('Error sending message:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to send message');
    } finally {
      setIsSendingMessage(false);
    }
  };

  // Add MessageInput component similar to CommentInput
  const MessageInput = () => {
    const [localMessageText, setLocalMessageText] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmitMessage = async () => {
      if (!localMessageText.trim() || isSubmitting) return;

      setIsSubmitting(true);
      try {
        // Create optimistic message
        const optimisticMessage = {
          id: Date.now(),
          activity_type: 'message' as const,
          description: localMessageText,
          created_at: new Date().toISOString(),
          user: useAuthStore.getState().user,
          uniqueId: `temp-message-${Date.now()}`
        };

        // Optimistically update the activities
        queryClient.setQueryData(['activities', taskId], (old: Activity[] = []) => {
          return [optimisticMessage, ...old];
        });

        const response = await fetch(`${API_BASE_URL}/messages/`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            content: localMessageText,
            task_id: Number(taskId),
            message_type: 'task_message'
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(errorData?.detail || 'Failed to send message');
        }

        // Clear input and hide message box
        setLocalMessageText("");
        setShowMessageInput(false);

        // Refresh activities
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['activities', taskId] }),
          queryClient.invalidateQueries({ queryKey: ['messages', taskId] })
        ]);

        toast.success('Message sent successfully');
      } catch (error) {
        // Revert optimistic update on error
        await queryClient.invalidateQueries({ queryKey: ['activities', taskId] });
        console.error('Error sending message:', error);
        toast.error(error instanceof Error ? error.message : 'Failed to send message');
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <div className="flex items-start gap-3 p-4 border-b">
        <Avatar className="w-8 h-8">
          <AvatarImage 
            src={useAuthStore.getState().user?.profile_image_url || '/default-avatar.png'} 
            alt={useAuthStore.getState().user?.full_name || 'User'} 
          />
          <AvatarFallback>
            {useAuthStore.getState().user?.full_name?.charAt(0) || 
             useAuthStore.getState().user?.username?.charAt(0) || 
             'U'}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 space-y-2">
          <div className="relative">
            <Textarea
              value={localMessageText}
              onChange={(e) => setLocalMessageText(e.target.value)}
              placeholder="Type your message..."
              className="min-h-[80px] pr-24 resize-none focus-visible:ring-1 focus-visible:ring-offset-1"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmitMessage();
                }
              }}
            />
            <div className="absolute bottom-2 right-2 flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowMessageInput(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitMessage}
                disabled={!localMessageText.trim() || isSubmitting}
                className="bg-blue-600 text-white hover:bg-blue-700"
              >
                {isSubmitting ? 'Sending...' : 'Send'}
              </Button>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Press Enter to send, Shift + Enter for new line
          </div>
        </div>
      </div>
    );
  };

  // Loading states
  if (isLoadingTask || isLoadingStages || isLoadingMilestones || isLoadingUsers || isLoadingComments || isLoadingTags || isLoadingActivities) {
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
  if (task && !canAccessTask(task)) {
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
                {currentMilestones.map((milestone: Milestone) => (
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
                        onClick={() => handleMilestoneSelect(milestone)}
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
              
              {currentUsers.map((user: User) => (
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

  // Tag Dialog Component
  const TagDialog = () => (
    <Dialog open={showTagDialog} onOpenChange={setShowTagDialog}>
      <DialogContent 
        className="sm:max-w-[500px]" 
        aria-describedby="tag-dialog-description"
      >
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Add Tags</DialogTitle>
            <div id="tag-dialog-description" className="sr-only">
              Add or remove tags for this task
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowTagDialog(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Tags</label>
            <div className="relative">
              <div 
                className="flex flex-wrap gap-2 min-h-[38px] w-full border rounded-md px-3 py-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500"
              >
                {selectedTags.map(tag => (
                  <div
                    key={tag.id}
                    className="flex items-center bg-[#EFF6FF] text-[#3B82F6] rounded-full px-3 py-1 text-sm"
                  >
                    <span>{tag.name}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTagRemove(tag.id);
                      }}
                      className="ml-2 hover:text-blue-800"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => handleTagInputChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && tagInput.trim()) {
                      e.preventDefault();
                      handleCreateNewTag();
                    }
                  }}
                  onClick={() => setIsTagPopoverOpen(true)}
                  className="flex-1 outline-none min-w-[120px] bg-transparent"
                  placeholder={selectedTags.length === 0 ? "Type or select tags..." : ""}
                />
              </div>
              
              <Popover open={isTagPopoverOpen} onOpenChange={setIsTagPopoverOpen}>
                <PopoverContent className="w-[300px] p-0" align="start">
                  <Command>
                    <CommandInput 
                      placeholder="Search existing tags..." 
                      value={tagInput}
                      onValueChange={handleTagInputChange}
                    />
                    <CommandEmpty>
                      <div className="py-3 px-4">
                        <p className="text-sm text-gray-500">
                          {tagInput.trim() ? "Press Enter to create a new tag" : "No tags available"}
                        </p>
                      </div>
                    </CommandEmpty>
                    <CommandGroup>
                      {filteredTags.length > 0 ? (
                        filteredTags.map(tag => (
                          <CommandItem
                            key={tag.id}
                            value={tag.name}
                            onSelect={() => handleTagSelect(tag)}
                            className="cursor-pointer"
                          >
                            <div className="flex items-center w-full">
                              <div className={`w-2 h-2 rounded-full mr-2 ${getTagColorClass(tag.color)}`}></div>
                              <span>{tag.name}</span>
                            </div>
                          </CommandItem>
                        ))
                      ) : (
                        <div className="py-3 px-4">
                          <p className="text-sm text-gray-500">No matching tags found</p>
                        </div>
                      )}
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>
          </div>
          
          <div className="flex justify-end mt-4">
            <Button
              variant="ghost"
              onClick={() => setShowTagDialog(false)}
            >
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), "MMM d, yyyy 'at' h:mm a");
  };

  if (loading) return <div>Loading...</div>;
  if (!task) return <div>Task not found</div>;

  // Add this before the activity feed content
  const CommentInput = () => {
    const [localCommentText, setLocalCommentText] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const queryClient = useQueryClient();

    const handleSubmitComment = async () => {
      if (!localCommentText.trim() || isSubmitting) return;

      setIsSubmitting(true);
      try {
        // Create optimistic comment
        const optimisticComment = {
          id: Date.now(),
          activity_type: 'comment' as const,
          description: localCommentText,
          created_at: new Date().toISOString(),
          user: useAuthStore.getState().user,
          uniqueId: `temp-comment-${Date.now()}`
        };

        // Optimistically update the activities
        queryClient.setQueryData(['activities', taskId], (old: Activity[] = []) => {
          return [optimisticComment, ...old];
        });

        // Send only the required fields for a comment
        const commentData = {
          content: localCommentText,
          task_id: Number(taskId),
          parent_id: null,
          create_notification: false // Explicitly tell backend not to create notification
        };

        const response = await fetch(`${API_BASE_URL}/comments/`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(commentData),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(errorData?.detail || 'Failed to send comment');
        }

        // Clear input and hide comment box
        setLocalCommentText("");
        setShowCommentInput(false);

        // Refresh activities
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['activities', taskId] }),
          queryClient.invalidateQueries({ queryKey: ['task-comments', taskId] })
        ]);

        toast.success('Comment added successfully');
      } catch (error) {
        // Revert optimistic update on error
        await queryClient.invalidateQueries({ queryKey: ['activities', taskId] });
        console.error('Error sending comment:', error);
        toast.error(error instanceof Error ? error.message : 'Failed to add comment');
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <div className="flex items-start gap-3 p-4 border-b">
        <Avatar className="w-8 h-8">
          <AvatarImage 
            src={useAuthStore.getState().user?.profile_image_url || '/default-avatar.png'} 
            alt={useAuthStore.getState().user?.full_name || 'User'} 
          />
          <AvatarFallback>
            {useAuthStore.getState().user?.full_name?.charAt(0) || 
             useAuthStore.getState().user?.username?.charAt(0) || 
             'U'}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 space-y-2">
          <div className="relative">
            <Textarea
              value={localCommentText}
              onChange={(e) => setLocalCommentText(e.target.value)}
              placeholder="Add a comment..."
              className="min-h-[80px] pr-24 resize-none focus-visible:ring-1 focus-visible:ring-offset-1"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmitComment();
                }
              }}
            />
            <div className="absolute bottom-2 right-2 flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowCommentInput(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitComment}
                disabled={!localCommentText.trim() || isSubmitting}
                className="bg-blue-600 text-white hover:bg-blue-700"
              >
                {isSubmitting ? 'Sending...' : 'Comment'}
              </Button>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Press Enter to submit, Shift + Enter for new line
          </div>
        </div>
      </div>
    );
  };

  // Add LogNoteInput component
  const LogNoteInput = () => {
    const [localNoteText, setLocalNoteText] = useState("");
    const [localFiles, setLocalFiles] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const queryClient = useQueryClient();

    const handleSubmitNote = async () => {
      if (!localNoteText.trim() || isSubmitting) return;

      setIsSubmitting(true);
      try {
        // Create optimistic log note
        const optimisticNote = {
          id: Date.now(),
          activity_type: 'log_note' as const,
          description: localNoteText,
          created_at: new Date().toISOString(),
          user: useAuthStore.getState().user,
          uniqueId: `temp-log-${Date.now()}`,
          attachments: localFiles.map((file, index) => ({
            id: -index - 1,
            filename: file.name,
            original_filename: file.name,
            content_type: file.type
          }))
        };

        // Optimistically update the activities
        queryClient.setQueryData(['activities', resolvedParams.taskId], (old: Activity[] = []) => {
          return [optimisticNote, ...old];
        });

        const formData = new FormData();
        formData.append("content", localNoteText);
        formData.append("task_id", resolvedParams.taskId);
        
        if (localFiles.length > 0) {
          localFiles.forEach(file => {
            formData.append("files", file);
          });
        }

        const response = await fetch(`${API_BASE_URL}/log-notes/`, {
          method: "POST",
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(errorData?.detail || 'Failed to add log note');
        }

        // Clear input and hide log note box
        setLocalNoteText("");
        setLocalFiles([]);
        setShowLogForm(false);

        // Refresh activities and log notes
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['activities', resolvedParams.taskId] }),
          queryClient.invalidateQueries({ queryKey: ['log-notes', resolvedParams.taskId] })
        ]);

        toast.success("Log note added successfully");
      } catch (error) {
        // Revert optimistic update on error
        await queryClient.invalidateQueries({ queryKey: ['activities', resolvedParams.taskId] });
        console.error('Error adding log note:', error);
        toast.error(error instanceof Error ? error.message : 'Failed to add log note');
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <div className="flex items-start gap-3 p-4 border-b">
        <Avatar className="w-8 h-8">
          <AvatarImage 
            src={useAuthStore.getState().user?.profile_image_url || '/default-avatar.png'} 
            alt={useAuthStore.getState().user?.full_name || 'User'} 
          />
          <AvatarFallback>
            {useAuthStore.getState().user?.full_name?.charAt(0) || 
             useAuthStore.getState().user?.username?.charAt(0) || 
             'U'}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 space-y-3">
          <div className="relative">
            <Textarea
              value={localNoteText}
              onChange={(e) => setLocalNoteText(e.target.value)}
              placeholder="Log an internal note..."
              className="min-h-[120px] resize-none focus-visible:ring-1 focus-visible:ring-offset-1"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <input
                type="file"
                multiple
                onChange={(e) => setLocalFiles(Array.from(e.target.files || []))}
                className="hidden"
                id="log-note-attachments"
              />
              <label
                htmlFor="log-note-attachments"
                className="cursor-pointer text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                <Paperclip className="h-4 w-4" />
                Attach files
              </label>
              {localFiles.length > 0 && (
                <span className="text-sm text-gray-500">
                  {localFiles.length} file(s) selected
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button 
                type="button" 
                variant="ghost" 
                onClick={() => setShowLogForm(false)}
              >
                Cancel
              </Button>
              <Button 
                onClick={handleSubmitNote}
                disabled={!localNoteText.trim() || isSubmitting}
                className="bg-purple-600 text-white hover:bg-purple-700"
              >
                {isSubmitting ? 'Logging...' : 'Log'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  };

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
            {stages.slice(0, showAllStages ? stages.length : 4).map((stage: TaskStage) => {
              const isCurrentStage = stage.id.toString() === currentStage;
              console.log(`Stage ${stage.id} comparison:`, { 
                stageId: stage.id, 
                currentStage, 
                isCurrentStage,
                taskStageId: task?.stage_id 
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
                  {stages.slice(4).map((stage: TaskStage) => (
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
        <div className="activity-feed-layout">
          {/* Main Content Area */}
          <div className="activity-feed-main">
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
                            setIsNameChanged(e.target.value !== task?.name);
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
                      value={task?.milestone?.name || ""}
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
                  <Popover open={isTagPopoverOpen} onOpenChange={setIsTagPopoverOpen}>
                    <PopoverTrigger asChild>
                      <div 
                        className="flex flex-wrap gap-2 min-h-[38px] w-full border rounded-md px-3 py-2 cursor-text focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500"
                        onClick={() => setIsTagPopoverOpen(true)}
                      >
                        {selectedTags.map(tag => (
                          <div
                            key={tag.id}
                            className={`flex items-center rounded-full px-3 py-1 text-sm ${getTagColorClass(tag.color)}`}
                          >
                            <span>{tag.name}</span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleTagRemove(tag.id);
                              }}
                              className="ml-2 hover:text-blue-800"
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ))}
                        <input
                          type="text"
                          value={tagInput}
                          onChange={(e) => handleTagInputChange(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && tagInput.trim()) {
                              e.preventDefault();
                              handleCreateNewTag();
                            }
                          }}
                          className="flex-1 outline-none min-w-[120px] bg-transparent"
                          placeholder={selectedTags.length === 0 ? "Type or select tags..." : ""}
                        />
                      </div>
                    </PopoverTrigger>
                    <PopoverContent className="w-[300px] p-0" align="start">
                      <Command>
                        <CommandInput 
                          placeholder="Search existing tags..." 
                          value={tagInput}
                          onValueChange={handleTagInputChange}
                        />
                        <CommandEmpty>
                          <div className="py-3 px-4">
                            <p className="text-sm text-gray-500">Press Enter to create a new tag</p>
                          </div>
                        </CommandEmpty>
                        <CommandGroup>
                          {filteredTags.map(tag => (
                            <CommandItem
                              key={tag.id}
                              value={tag.name}
                              onSelect={() => handleTagSelect(tag)}
                              className="cursor-pointer"
                            >
                              <div className="flex items-center w-full">
                                <div className={`w-2 h-2 rounded-full mr-2 ${getTagColorClass(tag.color)}`}></div>
                                <span>{tag.name}</span>
                              </div>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Customer</label>
                  <Input placeholder="Select customer..." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Allocated Time</label>
                  <div className="flex items-center gap-2">
                    <Input 
                      type="number" 
                      min="0"
                      step="0.5"
                      value={allocatedTime}
                      onChange={(e) => {
                        const newTime = e.target.value;
                        setAllocatedTime(newTime);
                        setIsAllocatedTimeChanged(newTime !== task?.planned_hours?.toString());
                      }}
                      className="w-24"
                    />
                    <span className="text-gray-500">hours</span>
                    {isAllocatedTimeChanged && (
                      <Button
                        size="sm"
                        onClick={handleSaveChanges}
                      >
                        Save
                      </Button>
                    )}
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
                      const taskDeadline = task?.deadline ? new Date(task.deadline).toISOString().slice(0, 16) : null;
                      setIsDeadlineChanged(newDeadline !== taskDeadline);
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
              <div className="relative">
                <Textarea
                  placeholder="Add details about this task..."
                  className="min-h-[200px] w-full"
                  value={description}
                  onChange={(e) => {
                    setDescription(e.target.value);
                    setIsDescriptionChanged(true);
                  }}
                />
                {isDescriptionChanged && (
                  <Button
                    className="absolute bottom-4 right-4"
                    size="sm"
                    onClick={handleSaveChanges}
                  >
                    Save Changes
                  </Button>
                )}
              </div>
            </div>
          </div>

          {/* Activity Feed */}
          <div className="activity-feed-aside">
            {/* Mobile Action Buttons */}
            <div className="lg:hidden mb-4">
              {actionButtons}
            </div>

            <div className="activity-feed-container bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <h3 className="font-medium text-lg">Activity Feed</h3>
              </div>

              {/* Add Message Input if showMessageInput is true */}
              {showMessageInput && <MessageInput />}

              {/* Add Comment Input if showCommentInput is true */}
              {showCommentInput && <CommentInput />}

              {/* Add Log Note Input if showLogForm is true */}
              {showLogForm && <LogNoteInput />}

              {/* Activity Feed Content */}
              <div 
                ref={activityFeedRef}
                onScroll={handleActivityScroll}
                className="activity-feed-scroll overflow-hidden hover:overflow-y-auto p-4 relative"
              >
                {showScrollToLatest && (
                  <div className="scroll-to-latest-enter-active">
                    <Button
                      onClick={scrollToLatest}
                      className="fixed bottom-8 right-8 bg-white/90 backdrop-blur-sm shadow-lg rounded-full p-2 hover:bg-blue-50 hover:text-blue-600 transition-all duration-200 z-50 group"
                      size="icon"
                      variant="outline"
                    >
                      <div className="absolute -top-8 right-0 bg-gray-800 text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap">
                        Scroll to latest
                      </div>
                      <ChevronUp className="h-4 w-4" />
                    </Button>
                  </div>
                )}

                {isLoadingActivities && !activitiesData ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600" />
                  </div>
                ) : Object.entries(groupedActivities).length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-4">
                    No activities recorded yet
                  </p>
                ) : (
                  Object.entries(groupedActivities).map(([date, dateActivities]: [string, Activity[]]) => (
                    <div key={date} className="mb-6 last:mb-0">
                      <div className="flex items-center mb-3 sticky top-0 bg-white z-10 py-2">
                        <h3 className="text-sm font-medium text-gray-500 whitespace-nowrap">
                          {date === new Date().toLocaleDateString() ? 'Today' : date}
                        </h3>
                        <div className="flex-1 ml-3 border-t border-gray-200" />
                      </div>

                      <div className="space-y-4">
                        {dateActivities.map((activity: Activity) => (
                          <div key={activity.uniqueId} className="flex items-start gap-3 transition-opacity duration-200">
                            <Avatar className="w-8 h-8 flex-shrink-0">
                              <AvatarImage 
                                src={activity.user?.profile_image_url || '/default-avatar.png'} 
                                alt={activity.user?.full_name || 'User'} 
                              />
                              <AvatarFallback>
                                {activity.user?.full_name?.charAt(0) || 
                                 activity.user?.username?.charAt(0) || 
                                 'U'}
                              </AvatarFallback>
                            </Avatar>
                            <div className={`flex-1 min-w-0 rounded-lg p-3 ${
                              activity.activity_type === 'comment' ? 'bg-blue-50' :
                              activity.activity_type === 'log_note' ? 'bg-purple-50' :
                              activity.description.toLowerCase().includes('stage') ? 'bg-purple-100' :
                              activity.description.toLowerCase().includes('status') ? 'bg-purple-100' :
                              activity.description.toLowerCase().includes('deadline') ? 'bg-amber-100' :
                              activity.description.toLowerCase().includes('title') ? 'bg-emerald-100' :
                              'bg-gray-100'
                            }`}>
                              <div className="flex items-baseline justify-between flex-nowrap">
                                <span className="text-sm font-medium text-gray-700 whitespace-nowrap">
                                  {activity.user?.full_name || activity.user?.username || 'Unknown User'}
                                </span>
                                <span className="text-xs text-gray-500 whitespace-nowrap ml-3">
                                  {new Date(activity.created_at).toLocaleTimeString([], { 
                                    hour: '2-digit', 
                                    minute: '2-digit' 
                                  })}
                                </span>
                              </div>
                              <div className="mt-1">
                                {activity.activity_type === 'log_note' ? (
                                  <div className="text-sm text-gray-700">
                                    {activity.description}
                                    {activity.attachments && activity.attachments.length > 0 && (
                                      <div className="mt-2 space-y-1">
                                        {activity.attachments.map((attachment) => (
                                          <div key={attachment.id} className="flex items-center gap-2 text-xs text-blue-600">
                                            <Paperclip className="h-3 w-3" />
                                            <a 
                                              href={`${API_BASE_URL}/uploads/log_notes/${attachment.filename}`}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="hover:underline"
                                            >
                                              {attachment.original_filename}
                                            </a>
                                            </div>
                                        ))}
                                            </div>
                                        )}
                                      </div>
                                ) : activity.activity_type === 'comment' ? (
                                  <div className="text-sm text-gray-700">
                                        {activity.description}
                                      </div>
                                ) : (
                                  <div className="text-sm text-gray-700">
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
      </div>

      {/* Render all dialogs */}
      <MilestoneDialog />
      <CreateMilestoneDialog />
      <AssigneeDialog />
      <TagDialog />
    </div>
  );
}

// Update the LogNoteForm component
const LogNoteForm: React.FC<{ taskId: string; onLogAdded: () => void }> = ({ taskId, onLogAdded }) => {
  const [content, setContent] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { token } = useAuthStore();
  const queryClient = useQueryClient();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    // Create optimistic log note
    const optimisticLogNote = {
      id: Date.now(),
      activity_type: 'task_update' as const,
      description: content,
      created_at: new Date().toISOString(),
      user: useAuthStore.getState().user,
      uniqueId: `temp-log-${Date.now()}`
    };

    // Optimistically update the activities
    queryClient.setQueryData(['activities', taskId], (old: Activity[] = []) => {
      return [optimisticLogNote, ...old];
    });

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("content", content);
      formData.append("task_id", taskId);
      
      files.forEach(file => {
        formData.append("files", file);
      });

      const response = await fetch(`${API_BASE_URL}/log-notes/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to add log note');
      }

      setContent("");
      setFiles([]);
      
      // Refresh activities
      await queryClient.invalidateQueries({ queryKey: ['activities', taskId] });
      
      toast.success("Log note added successfully");
      onLogAdded();
    } catch (error) {
      // Revert optimistic update on error
      await queryClient.invalidateQueries({ queryKey: ['activities', taskId] });
      console.error('Error adding log note:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to add log note');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setContent("");
    setFiles([]);
    onLogAdded();
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-start gap-4">
          <Avatar className="h-8 w-8 mt-2">
            <AvatarImage 
              src={useAuthStore.getState().user?.profile_image_url || '/default-avatar.png'} 
              alt={useAuthStore.getState().user?.full_name || 'User'} 
            />
            <AvatarFallback>
              {useAuthStore.getState().user?.full_name?.charAt(0) || 
               useAuthStore.getState().user?.username?.charAt(0) || 
               'U'}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 space-y-3">
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write a log note..."
              className="min-h-[120px] resize-none focus-visible:ring-1 focus-visible:ring-offset-1"
            />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <input
                  type="file"
                  multiple
                  onChange={(e) => setFiles(Array.from(e.target.files || []))}
                  className="hidden"
                  id="log-attachments"
                />
                <label
                  htmlFor="log-attachments"
                  className="cursor-pointer text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <Paperclip className="h-4 w-4" />
                  Attach files
                </label>
                {files.length > 0 && (
                  <span className="text-sm text-gray-500">
                    {files.length} file(s) selected
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  type="button" 
                  variant="ghost" 
                  onClick={handleCancel}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={isSubmitting || !content.trim()}
                  className="bg-blue-600 text-white hover:bg-blue-700"
                >
                  Log Note
                </Button>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};