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
  assignee?: {
    full_name: string;
    profile_image_url: string | null;
  };
}

export default function DashboardPage() {
  const { user, token } = useAuthStore();
  const { metrics, loading, error, fetchMetrics } = useDashboardStore();
  const [date, setDate] = useState<Date>(new Date());
  const [projects, setProjects] = useState<Project[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<string>("");
  const [teamMembers] = useState([
    { id: '1', name: 'Dana R.', role: 'Project Manager', avatar: '/default-avatar.png' },
    { id: '2', name: 'Peter McCloud', role: 'Team Lead', avatar: '/default-avatar.png' },
    { id: '3', name: 'Nancy K.', role: 'Account Manager', avatar: '/default-avatar.png' },
    { id: '4', name: 'James M.', role: 'Digital Manager', avatar: '/default-avatar.png' },
  ]);

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
        const accessibleProjects = projectsData
          .filter((project: ApiProject) => 
            project.created_by === Number(user?.id) || project.has_user_tasks === true
          )
          .map((project: ApiProject): Project => ({
            id: project.id,
            name: project.name,
            description: project.description || null,
            key: project.id.toString(),
            privacy_level: 'public',
            start_date: project.created_at,
            end_date: project.deadline || null,
            created_by: project.created_by || 0,
            color: '#2563eb',
            is_template: false,
            meta_data: {},
            created_at: project.created_at,
            updated_at: project.updated_at,
            is_active: true,
            has_user_tasks: project.has_user_tasks,
            has_access: project.has_access,
            member_count: project.members?.length || 0,
            members: project.members || []
          }));
        setProjects(accessibleProjects);
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      }
    }

    if (user) {
      fetchData();
    }
  }, [user]);

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

  const suggestions = metrics.aiInsights?.suggestions || [];
  const riskLevel = metrics.aiInsights?.riskLevel || 'Low';
  const predictedDelays = metrics.aiInsights?.predictedDelays || 0;

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
        
        {/* Weather and Quick Actions Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <WeatherWidget />
          {/* You can add more quick action widgets here */}
        </div>
      </div>

      {/* Debug Output - Remove in production */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="text-sm font-semibold mb-2">Debug Information:</h3>
        <pre className="text-xs overflow-auto max-h-40">
          {JSON.stringify({ taskSummaryData, isLoadingTaskSummary, taskSummaryError }, null, 2)}
        </pre>
      </div>

      {/* Metrics Section */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 mb-6">
        <KPICard
          title="Total Tasks"
          value={taskSummaryData?.total ?? 0}
          description={taskSummaryData ? 
            `Active: ${taskSummaryData.active}, Completed: ${taskSummaryData.completed}, Cancelled: ${taskSummaryData.cancelled}` : 
            'No data available'}
          isLoading={isLoadingTaskSummary}
          trend={undefined}
        />
        <KPICard
          title="Completed Tasks"
          value={completionRateData?.completed_tasks ?? 0}
          trend={completionRateData?.completion_rate ?? 0}
          description={`${completionRateData?.is_superuser_view ? 'Overall' : 'Your'} completion rate: ${completionRateData?.completion_rate?.toFixed(1)}%`}
          isLoading={isLoadingCompletionRate}
        />
        <KPICard
          title="Average Completion Time"
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
                          <p className="text-xs text-gray-500">{project.member_count || 0} members</p>
                        </div>
                      </div>
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
                  <p className={`text-lg ${
                    riskLevel === "Low"
                      ? "text-green-500"
                      : riskLevel === "Medium"
                      ? "text-yellow-500"
                      : "text-red-500"
                  }`}>
                    {riskLevel}
                  </p>
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Predicted Delays</h3>
                  <p className="text-lg">
                    {predictedDelays} task(s) at risk
                  </p>
                </div>
              </div>
              <div className="mt-4">
                <h3 className="font-semibold mb-2">AI Suggestions</h3>
                {suggestions && suggestions.length > 0 ? (
                  <ul className="list-disc list-inside space-y-1">
                    {suggestions.map((suggestion, index) => (
                      <li key={index} className="text-sm text-gray-600">
                        {suggestion}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-500">No suggestions available</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Team Directory */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Team directory</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {teamMembers.map((member) => (
                  <div key={member.id} className="flex items-center space-x-3">
                    <Avatar className="h-10 w-10">
                      <AvatarImage src={member.avatar} alt={member.name} />
                      <AvatarFallback>{member.name[0]}</AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="text-sm font-medium">{member.name}</p>
                      <p className="text-xs text-gray-500">{member.role}</p>
                    </div>
                  </div>
                ))}
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