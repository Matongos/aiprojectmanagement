"use client";

import { useEffect, useState, useRef } from "react";
import { KPICard } from "@/components/metrics/KPICard";
import { ProjectMetricsChart } from "@/components/charts/ProjectMetricsChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/authStore";
import { useDashboardStore } from "@/store/dashboardStore";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar } from "@/components/ui/calendar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { CalendarIcon, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/constants";
import { getRecentProjects } from "@/lib/api";
import { useWebSocket } from '@/hooks/useWebSocket';
import { Project } from "@/types/project";
import { WeatherWidget } from "@/components/weather/WeatherWidget";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface Comment {
  id: number;
  content: string;
  created_at: string;
  user: {
    id: number;
    username: string;
    full_name: string;
    profile_image_url: string | null;
  };
  task: {
    id: number;
    name: string;
  };
  project: {
    id: number;
    name: string;
  };
}

interface ApiProject {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
  description?: string;
  deadline?: string;
  state?: string;
  progress?: number;
  priority?: string;
  has_user_tasks?: boolean;
  has_access?: boolean;
  created_by?: number;
  members?: Array<{
    id: number;
    user_id: number;
    role: string;
    user: {
      id: number;
      name: string;
      profile_image_url: string | null;
    };
  }>;
}

interface TaskSummary {
  total: number;
  completed: number;
  active: number;
  cancelled: number;
  changes_requested: number;
  approved: number;
  completion_rate: number;
  tasks_by_state: {
    in_progress: number;
    completed: number;
    cancelled: number;
    changes_requested: number;
    approved: number;
  };
}

interface CompletionMetrics {
  averageCompletionTime: number;
  last7DaysAverage: number;
  last30DaysAverage: number;
  trend: number;
  period: string;
  insights: string[];
  tasksNeedingAttention: number;
  tasksOverEstimate: number;
  tasksNearDeadline: number;
  criticalInsights: string[];
  warningInsights: string[];
}

interface DashboardCompletionRate {
  completion_rate: number;
  total_tasks: number;
  completed_tasks: number;
  is_superuser_view: boolean;
}

// Add new interface for task trend data
interface TaskTrendItem {
  date: string;
  count: number;
}

interface TaskTrendResponse {
  created_tasks: TaskTrendItem[];
  completed_tasks: TaskTrendItem[];
}

interface Task {
  id: number;
  name: string;
  priority: string;
  priority_score: number;
  deadline?: string;
  state: string;
  progress: number;
  assignee?: {
    full_name: string;
    profile_image_url: string | null;
  };
}

// Add new interface for team directory user
interface TeamDirectoryUser {
  id: number;
  name: string;
  job_title?: string;
  project_names: string[];
  has_active_task: boolean;
  tasks: { id: number; name: string; state: string; project_id: number; project_name: string; deadline?: string; priority?: string; assigned_to?: number }[];
}

// Add interface for active tasks risk summary
interface ActiveTasksRiskSummary {
  status: string;
  summary: {
    total_active_tasks: number;
    average_risk_score: number;
    highest_risk_score: number;
    lowest_risk_score: number;
    risk_distribution: {
      extreme: number;
      critical: number;
      high: number;
      medium: number;
      low: number;
      minimal: number;
    };
    tasks_needing_immediate_attention: number;
    tasks_with_high_risk: number;
    total_ai_insights: number;
    total_specific_problems: number;
    critical_insights: string[];
    common_problems: string[];
  };
  tasks: Array<{
    task_id: number;
    task_name: string;
    project_name: string;
    assignee_name: string;
    state: string;
    progress: number;
    deadline: string;
    risk_score: number;
    risk_level: string;
    ai_insights: string[];
    specific_problems: string[];
    top_risk_factors: Array<{
      factor: string;
      score: number;
    }>;
    immediate_actions: string[];
    overall_assessment: {
      severity: string;
      success_probability: number;
      needs_attention: boolean;
    };
  }>;
  message: string;
}

// Add interface for personalized AI suggestions
interface PersonalizedAiSuggestions {
  status: string;
  source: string;
  cache_expires_in_seconds: number;
  data: {
    status: string;
    user_context: {
      user_id: number;
      user_name: string;
      email: string;
      role: string;
      is_superuser: boolean;
      current_workload: number;
      managed_projects: number;
      assigned_tasks: Task[];
    };
    top_risky_tasks: Array<{
      task_id: number;
      task_name: string;
      project_name: string;
      assignee_name: string;
      risk_score: number;
      risk_level: string;
      user_relationship: string;
    }>;
    ai_suggestions: {
      overall_assessment: string;
      user_role_analysis: string;
      task_suggestions: Array<{
        task_id: number;
        task_name: string;
        risk_score: number;
        risk_level: string;
        user_relationship: string;
        immediate_actions: string[];
        strategic_recommendations: string[];
        potential_impact: string;
        timeframe: string;
      }>;
      overall_recommendations: string[];
      next_steps: string[];
      final_message: string;
      ai_generated: boolean;
      ai_model: string;
    };
    generated_at: string;
    task_id: string;
    processed_at: string;
    cache_expires_at: string;
  };
}

export default function DashboardPage() {
  const { user, token } = useAuthStore();
  const { loading, error, fetchMetrics } = useDashboardStore();
  const [date, setDate] = useState<Date>(new Date());
  const [projects, setProjects] = useState<Project[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<string>("");
  const [teamSearch, setTeamSearch] = useState("");
  const [aiSuggestionDisplayIndex, setAiSuggestionDisplayIndex] = useState<number>(0);
  const [expandedTeamMembers, setExpandedTeamMembers] = useState<Set<number>>(new Set());
  const hasRotatedThisVisit = useRef<boolean>(false);

  // WebSocket connection
  const wsStatus = useWebSocket("");

  // Effect to update connection status
  useEffect(() => {
    setConnectionStatus(wsStatus);
  }, [wsStatus]);

  // Add completion rate query
  const { data: completionRateData, isLoading: isLoadingCompletionRate } = useQuery<DashboardCompletionRate>({
    queryKey: ["dashboard-completion-rate"],
    queryFn: async () => {
      if (!token) {
        throw new Error("Authentication token is missing");
      }

      const response = await fetch(`${API_BASE_URL}/analytics/dashboard/completion-rate`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch completion rate');
      }

      return response.json();
    },
    enabled: !!token,
  });

  // Add task summary query
  const { data: taskSummaryData, isLoading: isLoadingTaskSummary, error: taskSummaryError } = useQuery<TaskSummary>({
    queryKey: ["task-summary"],
    queryFn: async () => {
      if (!token) {
        throw new Error("Authentication token is missing");
      }

      const response = await fetch(`${API_BASE_URL}/analytics/tasks/summary`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch task summary');
      }

      return response.json();
    },
    enabled: !!token,
  });

  // Fetch latest comments
  const { data: latestComments = [], isLoading: isLoadingComments } = useQuery<Comment[]>({
    queryKey: ["latest-comments"],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/comments/latest?limit=5`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch latest comments');
        }

        return response.json();
      } catch (error) {
        console.error('Error fetching latest comments:', error);
        return [];
      }
    },
    enabled: !!token,
  });

  // Add completion time metrics query
  const { data: completionMetrics = { 
    averageCompletionTime: 0, 
    last7DaysAverage: 0,
    last30DaysAverage: 0,
    trend: 0, 
    period: "Last 30 days",
    insights: [],
    tasksNeedingAttention: 0,
    tasksOverEstimate: 0,
    tasksNearDeadline: 0,
    criticalInsights: [],
    warningInsights: []
  }, isLoading: isLoadingCompletionMetrics } = useQuery<CompletionMetrics>({
    queryKey: ["completion-metrics"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/analytics/tasks/completion-time`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch completion metrics');
      }
      return response.json();
    },
    enabled: !!token,
  });

  // Add task trend query
  const { data: taskTrendData, isLoading: isLoadingTaskTrend } = useQuery<TaskTrendResponse>({
    queryKey: ["task-trend"],
    queryFn: async () => {
      if (!token) {
        throw new Error("Authentication token is missing");
      }

      const response = await fetch(`${API_BASE_URL}/analytics/tasks/trend?days=15`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch task trend data');
      }

      return response.json();
    },
    enabled: !!token,
  });

  // Add query for top 3 personal tasks by priority
  const { data: myTopTasks, isLoading: isLoadingMyTopTasks } = useQuery<Task[]>({
    queryKey: ["my-top-tasks", user?.id],
    queryFn: async () => {
      if (!token) {
        throw new Error("Authentication token is missing");
      }
      const response = await fetch(`${API_BASE_URL}/tasks/my?limit=3`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch my top tasks');
      }
      return response.json();
    },
    enabled: !!token && !!user?.id,
  });

  // Add query for personalized AI suggestions
  const { data: personalizedAiSuggestions, isLoading: isLoadingPersonalizedAi } = useQuery<PersonalizedAiSuggestions>({
    queryKey: ["personalized-ai-suggestions"],
    queryFn: async () => {
      if (!token) {
        throw new Error("Authentication token is missing");
      }

      const response = await fetch(`${API_BASE_URL}/analytics/tasks/ai-suggestions/personalized/cached`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch personalized AI suggestions');
      }

      return response.json();
    },
    enabled: !!token,
    retry: 1,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  // Fetch team directory
  const { data: teamDirectory, isLoading: isLoadingTeamDirectory, error: teamDirectoryError } = useQuery<TeamDirectoryUser[]>({
    queryKey: ["team-directory"],
    queryFn: async () => {
      if (!token) throw new Error("Authentication token is missing");
      const response = await fetch(`${API_BASE_URL}/users/team-directory`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to fetch team directory');
      return response.json();
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  // Add query for active tasks risk summary
  const { data: activeTasksRiskSummary, isLoading: isLoadingActiveTasksRisk } = useQuery<ActiveTasksRiskSummary>({
    queryKey: ["active-tasks-risk-summary"],
    queryFn: async () => {
      if (!token) {
        throw new Error("Authentication token is missing");
      }

      const response = await fetch(`${API_BASE_URL}/analytics/tasks/active-risks-summary`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch active tasks risk summary');
      }

      return response.json();
    },
    enabled: !!token,
    retry: 1,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  // Log the auth state
  useEffect(() => {
    console.log("Auth state:", {
      hasToken: !!token,
      hasUser: !!user,
      userId: user?.id
    });
  }, [token, user]);

  // Rotate AI suggestions when user visits dashboard
  useEffect(() => {
    // Only rotate if we haven't already rotated this visit and AI suggestions are loaded
    if (!hasRotatedThisVisit.current && personalizedAiSuggestions?.status === "success") {
      const nextIndex = (aiSuggestionDisplayIndex + 1) % 3;
      console.log(`Rotating AI suggestions: ${aiSuggestionDisplayIndex} -> ${nextIndex}`);
      setAiSuggestionDisplayIndex(nextIndex);
      hasRotatedThisVisit.current = true;
    }
  }, [personalizedAiSuggestions?.status, aiSuggestionDisplayIndex]);

  // Debug: Log current state
  useEffect(() => {
    console.log("AI Suggestions Debug:", {
      status: personalizedAiSuggestions?.status,
      currentIndex: aiSuggestionDisplayIndex,
      hasRotated: hasRotatedThisVisit.current,
      data: personalizedAiSuggestions?.data?.ai_suggestions ? {
        overall_recommendations: personalizedAiSuggestions.data.ai_suggestions.overall_recommendations?.length,
        next_steps: personalizedAiSuggestions.data.ai_suggestions.next_steps?.length,
        final_message: !!personalizedAiSuggestions.data.ai_suggestions.final_message
      } : null
    });
  }, [personalizedAiSuggestions, aiSuggestionDisplayIndex, hasRotatedThisVisit.current]);

  // Reset rotation flag when component unmounts (user leaves dashboard)
  useEffect(() => {
    return () => {
      hasRotatedThisVisit.current = false;
    };
  }, []);

  // Helper function to toggle team member expansion
  const toggleTeamMemberExpansion = (memberId: number) => {
    setExpandedTeamMembers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(memberId)) {
        newSet.delete(memberId);
      } else {
        newSet.add(memberId);
      }
      return newSet;
    });
  };

  // Helper function to get current AI suggestion content
  const getCurrentAiSuggestionContent = () => {
    if (personalizedAiSuggestions?.status !== "success" || !personalizedAiSuggestions.data?.ai_suggestions) {
      console.log("No AI suggestions data available");
      return null;
    }

    const suggestions = personalizedAiSuggestions.data.ai_suggestions;
    console.log("Available suggestions data:", {
      overall_recommendations: suggestions.overall_recommendations,
      next_steps: suggestions.next_steps,
      final_message: suggestions.final_message
    });
    
    switch (aiSuggestionDisplayIndex) {
      case 0:
        console.log("Returning Overall Recommendations");
        return {
          title: "Overall Recommendations",
          content: suggestions.overall_recommendations || [],
          type: "recommendations"
        };
      case 1:
        console.log("Returning Next Steps");
        return {
          title: "Next Steps",
          content: suggestions.next_steps || [],
          type: "steps"
        };
      case 2:
        console.log("Returning Final Summary");
        return {
          title: "Final Summary",
          content: suggestions.final_message ? [suggestions.final_message] : [],
          type: "summary"
        };
      default:
        console.log("Returning default (Overall Recommendations)");
        return {
          title: "Overall Recommendations",
          content: suggestions.overall_recommendations || [],
          type: "recommendations"
        };
    }
  };

  useEffect(() => {
    if (token) {
      fetchMetrics(token);
    }
  }, [token, fetchMetrics]);

  useEffect(() => {
    async function fetchData() {
      try {
        const projectsData = await getRecentProjects();
        const projectPromises = projectsData
          .filter((project: ApiProject) => 
            project.created_by === Number(user?.id) || project.has_user_tasks === true
          )
          .map(async (project: ApiProject) => {
            // Fetch detailed project information including members
            const response = await fetch(`${API_BASE_URL}/projects/${project.id}`, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            });
            
            if (!response.ok) {
              throw new Error(`Failed to fetch project details for project ${project.id}`);
            }
            
            const detailedProject = await response.json();
            
            return {
              id: project.id,
              name: project.name,
              description: project.description || null,
              key: project.id.toString(),
              start_date: project.created_at,
              end_date: project.deadline || null,
              created_by: project.created_by || 0,
              is_template: false,
              meta_data: {},
              created_at: project.created_at,
              updated_at: project.updated_at,
              is_active: true,
              has_user_tasks: project.has_user_tasks,
              has_access: project.has_access,
              member_count: detailedProject.member_count || 0,
              members: detailedProject.members || []
            };
          });

        const accessibleProjects = await Promise.all(projectPromises);
        setProjects(accessibleProjects);
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      }
    }

    if (user && token) {
      fetchData();
    }
  }, [user, token]);

  if (loading || isLoadingTaskSummary) {
    return (
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Project Dashboard</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
          {Array(4).fill(0).map((_, i) => (
            <Card key={i}>
              <CardHeader className="space-y-0 pb-2">
                <Skeleton className="h-4 w-[100px]" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-[60px]" />
                <Skeleton className="h-4 w-[100px] mt-2" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 mb-6">
          {Array(2).fill(0).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-[150px]" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-[300px] w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || taskSummaryError) {
    return (
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Project Dashboard</h1>
        <Card className="bg-red-50">
          <CardContent className="p-4">
            <p className="text-red-600">
              {error || (taskSummaryError instanceof Error ? taskSummaryError.message : 'Unknown error')}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Update the chart dataset using taskSummaryData
  const chartData = {
    labels: taskSummaryData ? [
      "In Progress",
      "Changes Requested",
      "Approved",
      "Completed",
      "Cancelled"
    ] : ['No Data'],
    datasets: [
      {
        label: "Tasks",
        data: taskSummaryData ? [
          taskSummaryData.tasks_by_state.in_progress,
          taskSummaryData.tasks_by_state.changes_requested,
          taskSummaryData.tasks_by_state.approved,
          taskSummaryData.tasks_by_state.completed,
          taskSummaryData.tasks_by_state.cancelled
        ] : [0],
        backgroundColor: taskSummaryData ? [
          "#2563eb", // blue for in progress
          "#f59e0b", // amber for changes requested
          "#s0m436", // emerald for approved
          "#16a34a", // green for completed
          "#dc2626", // red for cancelled
        ] : ["#e5e7eb"], // gray for no data
      },
    ],
  };

  // Define chart options
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
      tooltip: {
        callbacks: {
          label(context: { parsed: number; label: string }) {
            const total = taskSummaryData?.total || 0;
            const value = context.parsed || 0;
            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
            return `${context.label}: ${value} (${percentage}%)`;
          }
        }
      }
    }
  };

  return (
    <div className="container mx-auto p-6">
      {/* Header with Search, Weather, and Connection Status */}
      <div className="flex flex-col gap-4 mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-semibold mb-1">Welcome, {user?.full_name || 'User'}!</h1>
            <p className="text-gray-600">Here is your agenda for today</p>
          </div>
          <div className="flex items-center gap-4">
            {/* Connection Status Indicator */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                connectionStatus === 'connected' 
                  ? 'bg-green-500' 
                  : connectionStatus === 'connecting' 
                  ? 'bg-yellow-500' 
                  : 'bg-red-500'
              }`} />
              <span className="text-sm text-gray-600">
                {connectionStatus === 'connected' 
                  ? 'Live Updates Active' 
                  : connectionStatus === 'connecting' 
                  ? 'Connecting...' 
                  : 'Offline'}
              </span>
            </div>
            {/* Search */}
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search..."
                className="pl-10 w-full"
              />
            </div>
          </div>
        </div>
        
        {/* Quick Actions Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* You can add more quick action widgets here */}
        </div>
      </div>

      {/* Debug Output - Remove in production */}
     {/* <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="text-sm font-semibold mb-2">Debug Information:</h3>
        <pre className="text-xs overflow-auto max-h-40">
          {JSON.stringify({ taskSummaryData, isLoadingTaskSummary, taskSummaryError }, null, 2)}
        </pre>
      </div>

      {/* Metrics Section */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 mb-6">
        <WeatherWidget />
        <KPICard
          title="Task Overview"
          value={taskSummaryData?.total ?? 0}
          description={
            <div className="space-y-1">
              <div className="flex justify-between">
                <span>Active:</span>
                <span>{taskSummaryData?.active ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Completed:</span>
                <span>{taskSummaryData?.completed ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Completion Rate:</span>
                <span>{completionRateData?.completion_rate?.toFixed(1)}%</span>
              </div>
            </div>
          }
          isLoading={isLoadingTaskSummary || isLoadingCompletionRate}
          trend={completionRateData?.completion_rate ?? 0}
        />
        <KPICard
          title="Time Metrics"
          value={`${completionMetrics.averageCompletionTime.toFixed(1)}h`}
          trend={completionMetrics.trend}
          description={
            <div className="space-y-1">
              <div className="flex justify-between">
                <span>Last 7 days:</span>
                <span>{completionMetrics.last7DaysAverage?.toFixed(1)}h</span>
              </div>
              <div className="flex justify-between">
                <span>Last 30 days:</span>
                <span>{completionMetrics.last30DaysAverage?.toFixed(1)}h</span>
              </div>
              <div className={`text-sm ${completionMetrics.trend > 0 ? 'text-red-500' : 'text-green-500'}`}>
                {completionMetrics.trend > 0 ? 'Slower' : 'Faster'} than previous period
              </div>
            </div>
          }
          isLoading={isLoadingCompletionMetrics}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column - Calendar, Project Directory, and Urgent Tasks */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* Calendar */}
          <Card>
            <CardContent className="p-4">
              <Calendar
                mode="single"
                selected={date}
                onSelect={(newDate) => newDate && setDate(newDate)}
                className="rounded-md"
              />
            </CardContent>
          </Card>

          {/* Project Directory */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Project directory</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {projects.length === 0 ? (
                  <p className="text-sm text-gray-500">No projects available</p>
                ) : (
                  projects.map((project) => (
                    <div key={project.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-gray-100 rounded-md flex items-center justify-center">
                          <CalendarIcon className="h-4 w-4 text-gray-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{project.name}</p>
                          <p className="text-xs text-gray-500">
                            {project.member_count ?? 0} {project.member_count === 1 ? 'member' : 'members'}
                          </p>
                        </div>
                      </div>
                      <div className="flex -space-x-2">
                        {project.members && project.members.length > 0 ? (
                          project.members.slice(0, 3).map((member) => (
                            <Avatar key={member.id} className="h-6 w-6 border-2 border-white">
                              <AvatarImage 
                                src={member.user?.profile_image_url || '/default-avatar.png'} 
                                alt={member.user?.name || 'Member'}
                                className="object-cover"
                              />
                              <AvatarFallback>
                                {member.user?.name ? member.user.name[0] : 'M'}
                              </AvatarFallback>
                            </Avatar>
                          ))
                        ) : null}
                        {typeof project.member_count === 'number' && project.member_count > 3 && (
                          <div className="h-6 w-6 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center">
                            <span className="text-xs text-gray-600">+{project.member_count - 3}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Urgent Tasks */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Urgent tasks</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {isLoadingMyTopTasks ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600" />
                  </div>
                ) : myTopTasks && myTopTasks.length > 0 ? (
                  myTopTasks.map((task) => (
                    <div key={task.id} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg">
                      <div className="flex flex-col">
                        <p className="text-sm font-medium">{task.name}</p>
                        {user?.is_superuser && task.assignee && (
                          <p className="text-xs text-gray-500">
                            Assigned to: {task.assignee.full_name}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-col items-end">
                        <span className="text-xs text-red-500">
                          {task.deadline ? new Date(task.deadline).toLocaleDateString() : 'No deadline'}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          task.priority === 'urgent' ? 'bg-red-100 text-red-700' :
                          task.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {task.priority}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 text-center">No urgent tasks</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Middle Column - Charts and AI Insights */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* Task Distribution Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Task Distribution</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {isLoadingTaskSummary ? (
                <div className="flex items-center justify-center h-[300px]">
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
                </div>
              ) : taskSummaryError ? (
                <div className="flex items-center justify-center h-[300px] text-red-500">
                  Error loading task distribution
                </div>
              ) : (
                <ProjectMetricsChart
                  title="Task Distribution"
                  type="doughnut"
                  data={chartData}
                  options={chartOptions}
                />
              )}
            </CardContent>
          </Card>

          {/* Task Trend Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Task Trend</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {isLoadingTaskTrend ? (
                <div className="flex items-center justify-center h-[300px]">
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
                </div>
              ) : !taskTrendData ? (
                <div className="flex items-center justify-center h-[300px] text-gray-500">
                  No trend data available
                </div>
              ) : (
                <ProjectMetricsChart
                  title="Task Trend"
                  type="line"
                  data={{
                    labels: taskTrendData.created_tasks.map(item => item.date).reverse(),
                    datasets: [
                      {
                        label: "Created Tasks",
                        data: taskTrendData.created_tasks.map(item => item.count).reverse(),
                        borderColor: "#2563eb",
                        backgroundColor: ["rgba(37, 99, 235, 0.1)"],
                        fill: true
                      },
                      {
                        label: "Completed Tasks",
                        data: taskTrendData.completed_tasks.map(item => item.count).reverse(),
                        borderColor: "#16a34a",
                        backgroundColor: ["rgba(22, 163, 74, 0.1)"],
                        fill: true
                      },
                    ],
                  }}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'top',
                      },
                      tooltip: {
                        mode: 'index',
                        intersect: false,
                      }
                    },
                    scales: {
                      x: {
                        title: {
                          display: true,
                          text: 'Date'
                        }
                      },
                      y: {
                        beginAtZero: true,
                        title: {
                          display: true,
                          text: 'Number of Tasks'
                        }
                      }
                    },
                    interaction: {
                      mode: 'nearest',
                      axis: 'x',
                      intersect: false
                    }
                  }}
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Team Directory and AI Insights */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* AI Insights Card */}
          <Card>
            <CardHeader>
              <CardTitle>AI Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h3 className="font-semibold mb-2">Risk Level</h3>
                  {isLoadingActiveTasksRisk ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-600" />
                      <span className="text-sm text-gray-500">Analyzing...</span>
                    </div>
                  ) : activeTasksRiskSummary ? (
                    <div className="space-y-2">
                      {(() => {
                        const avgScore = activeTasksRiskSummary.summary.average_risk_score;
                        let riskLevel = '';
                        let colorClass = '';
                        
                        if (avgScore >= 80) {
                          riskLevel = 'Extreme';
                          colorClass = 'text-red-600';
                        } else if (avgScore >= 60) {
                          riskLevel = 'Critical';
                          colorClass = 'text-orange-600';
                        } else if (avgScore >= 40) {
                          riskLevel = 'High';
                          colorClass = 'text-yellow-600';
                        } else if (avgScore >= 20) {
                          riskLevel = 'Medium';
                          colorClass = 'text-blue-600';
                        } else {
                          riskLevel = 'Low';
                          colorClass = 'text-green-600';
                        }
                        
                        return (
                          <>
                            <p className={`text-lg font-semibold ${colorClass}`}>
                    {riskLevel}
                  </p>
                            <p className="text-xs text-gray-600">
                              Average Score: {avgScore.toFixed(1)}
                            </p>
                          </>
                        );
                      })()}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No risk data available</p>
                  )}
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Tasks at Risk</h3>
                  {isLoadingActiveTasksRisk ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-600" />
                      <span className="text-sm text-gray-500">Analyzing...</span>
                    </div>
                  ) : activeTasksRiskSummary ? (
                    <div className="space-y-2">
                      <p className="text-lg font-semibold text-red-600">
                        {activeTasksRiskSummary.summary.risk_distribution.extreme + 
                         activeTasksRiskSummary.summary.risk_distribution.critical + 
                         activeTasksRiskSummary.summary.risk_distribution.high} task(s) at risk
                      </p>
                      <div className="text-xs text-gray-600 space-y-1">
                        <div className="flex justify-between">
                          <span>Extreme Risk:</span>
                          <span className="text-red-600 font-medium">
                            {activeTasksRiskSummary.summary.risk_distribution.extreme}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Critical Risk:</span>
                          <span className="text-orange-600 font-medium">
                            {activeTasksRiskSummary.summary.risk_distribution.critical}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>High Risk:</span>
                          <span className="text-yellow-600 font-medium">
                            {activeTasksRiskSummary.summary.risk_distribution.high}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No risk data available</p>
                  )}
                </div>
              </div>
              <div className="mt-4">
                <h3 className="font-semibold mb-2">AI Insights</h3>
                {isLoadingPersonalizedAi ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-600" />
                    <span className="text-sm text-gray-500">Loading AI insights...</span>
                  </div>
                ) : personalizedAiSuggestions?.status === "success" ? (
                  <div className="space-y-3">
                    {(() => {
                      const currentContent = getCurrentAiSuggestionContent();
                      if (!currentContent) return null;
                      
                      return (
                        <>
                          <div 
                            className="bg-blue-50 rounded-lg p-3 border-l-4 border-blue-400 cursor-pointer hover:bg-blue-100 transition-colors duration-200"
                            onClick={() => {
                              const nextIndex = (aiSuggestionDisplayIndex + 1) % 3;
                              console.log(`Manual rotation: ${aiSuggestionDisplayIndex} -> ${nextIndex}`);
                              setAiSuggestionDisplayIndex(nextIndex);
                            }}
                            title="Click to see different AI insights"
                          >
                            <h4 className="text-sm font-semibold text-blue-800 mb-2 flex items-center justify-between">
                              {currentContent.title}
                              <span className="text-xs text-blue-600 opacity-70">Click to rotate</span>
                            </h4>
                            <div className="space-y-2">
                              {currentContent.content.map((item, index) => (
                                <p key={index} className="text-xs text-blue-700">
                                  • {item}
                                </p>
                              ))}
                          </div>
                          </div>
                          
                          {/* Display indicator */}
                          <div className="flex justify-center space-x-1">
                            {[0, 1, 2].map((index) => (
                              <div
                                key={index}
                                className={`w-2 h-2 rounded-full ${
                                  index === aiSuggestionDisplayIndex 
                                    ? 'bg-blue-500' 
                                    : 'bg-gray-300'
                                }`}
                              />
                            ))}
                          </div>
                          


                    {/* Cache Status */}
                    <div className="text-xs text-gray-500 text-center pt-2">
                            AI insights cached • Click to see different recommendations
                        </div>
                        </>
                      );
                    })()}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-gray-500">No AI insights available</p>
                    <p className="text-xs text-gray-400">AI suggestions are generated based on your current tasks and role</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Team Directory */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                Team directory
                {teamDirectory && teamDirectory.length > 4 && (
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm">View all</Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-lg w-full">
                      <DialogHeader>
                        <DialogTitle>All Team Members</DialogTitle>
                      </DialogHeader>
                                            <div className="space-y-4 max-h-[400px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
                        <Input placeholder="Search team members..." className="mb-2" onChange={e => setTeamSearch(e.target.value)} />
                        {(teamDirectory.filter(u => u.name.toLowerCase().includes(teamSearch.toLowerCase()) || (u.job_title || '').toLowerCase().includes(teamSearch.toLowerCase()))).map((member) => (
                          <div key={member.id} className="p-3 rounded-lg border hover:bg-gray-50">
                            <div className="flex items-center space-x-3">
                            <Avatar className="h-10 w-10">
                              <AvatarImage src={"/default-avatar.png"} alt={member.name} />
                              <AvatarFallback>{member.name[0]}</AvatarFallback>
                            </Avatar>
                            <div className="flex-1">
                              <p className="text-sm font-medium">{member.name}</p>
                              <p className="text-xs text-gray-500">{member.job_title || 'No job title'}</p>
                            </div>
                              <div className="flex items-center space-x-2">
                                <div className="text-xs text-gray-600 font-semibold whitespace-nowrap">
                                  {member.tasks.length} tasks
                                </div>
                                {member.tasks.length > 0 && (
                                  <button
                                    onClick={() => toggleTeamMemberExpansion(member.id)}
                                    className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
                                  >
                                    {expandedTeamMembers.has(member.id) ? 'Hide' : 'Show'} tasks
                                  </button>
                                )}
                              </div>
                            </div>
                            {/* Show active tasks only when expanded */}
                            {member.tasks.length > 0 && expandedTeamMembers.has(member.id) && (
                              <div className="mt-3 ml-12 space-y-1 border-t pt-2">
                                <p className="text-xs text-gray-600 font-medium">Active Tasks:</p>
                                {member.tasks.slice(0, 5).map((task) => (
                                  <div key={task.id} className="flex items-center justify-between text-xs">
                                    <span className="text-gray-700 truncate flex-1 mr-2">{task.name}</span>
                                    <span className={`px-1 py-0.5 rounded text-xs flex-shrink-0 ${
                                      task.state === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                      task.state === 'completed' ? 'bg-green-100 text-green-700' :
                                      task.state === 'approved' ? 'bg-purple-100 text-purple-700' :
                                      task.state === 'changes_requested' ? 'bg-yellow-100 text-yellow-700' :
                                      'bg-gray-100 text-gray-700'
                                    }`}>
                                      {task.state.replace('_', ' ')}
                                    </span>
                                  </div>
                                ))}
                                {member.tasks.length > 5 && (
                                  <p className="text-xs text-gray-500">+{member.tasks.length - 5} more tasks</p>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-[300px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
                {isLoadingTeamDirectory ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600" />
                  </div>
                ) : teamDirectoryError ? (
                  <p className="text-sm text-red-500 text-center">Failed to load team directory</p>
                ) : teamDirectory && teamDirectory.length > 0 ? (
                  teamDirectory.slice(0, 4).map((member) => (
                    <div key={member.id} className="p-3 rounded-lg border hover:bg-gray-50">
                      <div className="flex items-center space-x-3">
                        <Avatar className="h-8 w-8">
                        <AvatarImage src={"/default-avatar.png"} alt={member.name} />
                        <AvatarFallback>{member.name[0]}</AvatarFallback>
                      </Avatar>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{member.name}</p>
                          <p className="text-xs text-gray-500 truncate">{member.job_title || 'No job title'}</p>
                      </div>
                        <div className="flex items-center space-x-2">
                          <div className="text-xs text-gray-600 font-semibold whitespace-nowrap">
                            {member.tasks.length} tasks
                          </div>
                          {member.tasks.length > 0 && (
                            <button
                              onClick={() => toggleTeamMemberExpansion(member.id)}
                              className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
                            >
                              {expandedTeamMembers.has(member.id) ? 'Hide' : 'Show'} tasks
                            </button>
                          )}
                        </div>
                      </div>
                      {/* Show active tasks only when expanded */}
                      {member.tasks.length > 0 && expandedTeamMembers.has(member.id) && (
                        <div className="mt-3 ml-11 space-y-1 border-t pt-2">
                          <p className="text-xs text-gray-600 font-medium">Active Tasks:</p>
                          {member.tasks.slice(0, 3).map((task) => (
                            <div key={task.id} className="flex items-center justify-between text-xs">
                              <span className="text-gray-700 truncate flex-1 mr-2">{task.name}</span>
                              <span className={`px-1 py-0.5 rounded text-xs flex-shrink-0 ${
                                task.state === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                task.state === 'completed' ? 'bg-green-100 text-green-700' :
                                task.state === 'approved' ? 'bg-purple-100 text-purple-700' :
                                task.state === 'changes_requested' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {task.state.replace('_', ' ')}
                              </span>
                            </div>
                          ))}
                          {member.tasks.length > 3 && (
                            <p className="text-xs text-gray-500">+{member.tasks.length - 3} more tasks</p>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 text-center">No team members found</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Bottom Row - Comments Section */}
      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {isLoadingComments ? (
                <div className="col-span-full flex justify-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600" />
                </div>
              ) : latestComments.length === 0 ? (
                <div className="col-span-full">
                  <p className="text-sm text-gray-500 text-center">No comments yet</p>
                </div>
              ) : (
                latestComments.map((comment) => (
                  <div key={comment.id} className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
                    <Avatar className="h-8 w-8">
                      <AvatarImage 
                        src={comment.user.profile_image_url || '/default-avatar.png'} 
                        alt={comment.user.full_name} 
                      />
                      <AvatarFallback>
                        {comment.user.full_name?.charAt(0) || comment.user.username?.charAt(0) || 'U'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium">{comment.user.full_name || comment.user.username}</p>
                        <p className="text-xs text-gray-500">in {comment.project.name}</p>
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-2 mt-1">{comment.content}</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {new Date(comment.created_at).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          hour12: true
                        })}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 