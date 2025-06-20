"use client";

import { useEffect, useState } from "react";
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

// Add interface for user risk score
interface UserRiskScore {
  scope: string;
  user_id: number | null;
  average_risk_score: number;
  min_risk_score: number;
  max_risk_score: number;
  median_risk_score: number;
  task_count: number;
  risk_level: string;
  ai_explanation: string;
  high_risk_task_count: number;
  critical_risk_task_count: number;
}

// Add interface for AI Task Insight
interface AiTaskInsight {
  task_id: number;
  task_name: string;
  assigned_to: string | null;
  ai_insights: {
    root_cause: string;
    predicted_impact: string;
    suggested_action: string;
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

export default function DashboardPage() {
  const { user, token } = useAuthStore();
  const { loading, error, fetchMetrics } = useDashboardStore();
  const [date, setDate] = useState<Date>(new Date());
  const [projects, setProjects] = useState<Project[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<string>("");
  const [teamSearch, setTeamSearch] = useState("");

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

  // Add query for prioritized tasks
  const { data: prioritizedTasks, isLoading: isLoadingPrioritizedTasks } = useQuery<Task[]>({
    queryKey: ["prioritized-tasks"],
    queryFn: async () => {
      if (!token) {
        throw new Error("Authentication token is missing");
      }

      const response = await fetch(`${API_BASE_URL}/task-priority/tasks?limit=3`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch prioritized tasks');
      }

      return response.json();
    },
    enabled: !!token,
  });

  // Add user risk score query
  const { data: userRiskScore, isLoading: isLoadingRiskScore, error: riskScoreError } = useQuery<UserRiskScore>({
    queryKey: ["user-risk-score", user?.id],
    queryFn: async () => {
      if (!token || !user?.id) {
        throw new Error("Authentication token or user ID is missing");
      }
      const response = await fetch(`${API_BASE_URL}/ai/user/${user.id}/risk-score/latest`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch user risk score');
      }
      return response.json();
    },
    enabled: !!token && !!user?.id,
    retry: 1,
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  // Add query for AI task insights (for superusers and users)
  const { data: aiTaskInsights, isLoading: isLoadingAiTaskInsights, error: aiTaskInsightsError } = useQuery<AiTaskInsight[]>({
    queryKey: ["ai-task-insights", user?.id],
    queryFn: async () => {
      if (!token || !user?.id) {
        throw new Error("Authentication token or user ID is missing");
      }
      const response = await fetch(`${API_BASE_URL}/ai/ai/analyze-tasks/history?user_id=${user.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch AI task insights');
      }
      return response.json();
    },
    enabled: !!token && !!user?.id,
    retry: 1,
    staleTime: 10 * 60 * 1000,
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
  });

  // Log the auth state
  useEffect(() => {
    console.log("Auth state:", {
      hasToken: !!token,
      hasUser: !!user,
      userId: user?.id
    });
  }, [token, user]);

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

  // Get risk level from the new endpoint
  const riskLevel = userRiskScore?.risk_level || 'Loading...';

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
                {isLoadingPrioritizedTasks ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600" />
                  </div>
                ) : prioritizedTasks && prioritizedTasks.length > 0 ? (
                  prioritizedTasks.map((task) => (
                    <div key={task.id} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg">
                      <div className="flex flex-col">
                        <p className="text-sm font-medium">{task.name}</p>
                        {task.assignee && (
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
                  {isLoadingRiskScore ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-600" />
                      <span className="text-sm text-gray-500">Analyzing...</span>
                    </div>
                  ) : riskScoreError ? (
                    <p className="text-sm text-red-500">Failed to load risk level</p>
                  ) : (
                  <p className={`text-lg ${
                      riskLevel === "Very Low" || riskLevel === "Low"
                      ? "text-green-500"
                      : riskLevel === "Medium"
                      ? "text-yellow-500"
                        : riskLevel === "High" || riskLevel === "Critical"
                        ? "text-red-500"
                        : "text-gray-500"
                  }`}>
                    {riskLevel}
                  </p>
                  )}
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Tasks at Risk</h3>
                  {isLoadingRiskScore ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-600" />
                      <span className="text-sm text-gray-500">Analyzing...</span>
                    </div>
                  ) : riskScoreError ? (
                    <p className="text-sm text-red-500">Failed to load</p>
                  ) : (
                  <p className="text-lg">
                      {(userRiskScore?.high_risk_task_count ?? 0) + (userRiskScore?.critical_risk_task_count ?? 0)} task(s) at risk
                  </p>
                  )}
                </div>
              </div>
              <div className="mt-4">
                <h3 className="font-semibold mb-2">AI Task Suggestions</h3>
                {isLoadingAiTaskInsights ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-600" />
                    <span className="text-sm text-gray-500">Loading AI suggestions...</span>
                  </div>
                ) : aiTaskInsightsError ? (
                  <p className="text-sm text-red-500">Failed to load AI task suggestions</p>
                ) : aiTaskInsights && aiTaskInsights.length > 0 ? (
                  <ul className="space-y-4">
                    {aiTaskInsights.map((insight) => (
                      <li key={insight.task_id} className="bg-blue-50 rounded-lg p-3 shadow-sm">
                        <div className="mb-1 text-sm text-gray-700 font-semibold">
                          Task: <span className="text-blue-700">{insight.task_name}</span> (ID: {insight.task_id})
                        </div>
                        {insight.assigned_to && (
                          <div className="mb-1 text-xs text-gray-500">
                            Assigned to: <span className="font-medium text-gray-700">{insight.assigned_to}</span>
                          </div>
                        )}
                        <div className="text-sm">
                          <span className="font-semibold text-green-700">Suggested Action:</span> {insight.ai_insights.suggested_action || <span className="text-gray-400">No suggestion</span>}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-500">No AI task suggestions available</p>
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
                      <div className="space-y-4 max-h-[400px] overflow-y-auto">
                        <Input placeholder="Search team members..." className="mb-2" onChange={e => setTeamSearch(e.target.value)} />
                        {(teamDirectory.filter(u => u.name.toLowerCase().includes(teamSearch.toLowerCase()) || (u.job_title || '').toLowerCase().includes(teamSearch.toLowerCase()))).map((member) => (
                          <div key={member.id} className="flex items-center space-x-3 p-2 rounded hover:bg-gray-50">
                            <Avatar className="h-10 w-10">
                              <AvatarImage src={"/default-avatar.png"} alt={member.name} />
                              <AvatarFallback>{member.name[0]}</AvatarFallback>
                            </Avatar>
                            <div className="flex-1">
                              <p className="text-sm font-medium">{member.name}</p>
                              <p className="text-xs text-gray-500">{member.job_title || 'No job title'}</p>
                            </div>
                            <div className="text-xs text-gray-600 font-semibold whitespace-nowrap">{member.tasks.length} tasks</div>
                          </div>
                        ))}
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {isLoadingTeamDirectory ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600" />
                  </div>
                ) : teamDirectoryError ? (
                  <p className="text-sm text-red-500 text-center">Failed to load team directory</p>
                ) : teamDirectory && teamDirectory.length > 0 ? (
                  teamDirectory.slice(0, 4).map((member) => (
                    <div key={member.id} className="flex items-center space-x-3 p-2 rounded hover:bg-gray-50">
                      <Avatar className="h-10 w-10">
                        <AvatarImage src={"/default-avatar.png"} alt={member.name} />
                        <AvatarFallback>{member.name[0]}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <p className="text-sm font-medium">{member.name}</p>
                        <p className="text-xs text-gray-500">{member.job_title || 'No job title'}</p>
                      </div>
                      <div className="text-xs text-gray-600 font-semibold whitespace-nowrap">{member.tasks.length} tasks</div>
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