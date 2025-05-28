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

interface Project {
  id: number;
  name: string;
  description: string | null;
  key: string;
  status: string;
  privacy_level: string;
  start_date: string | null;
  end_date: string | null;
  created_by: number;
  color: string;
  is_template: boolean;
  meta_data: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  has_user_tasks?: boolean;
  has_access?: boolean;
  member_count: number;
  members: {
    id: number;
    user_id: number;
    role: string;
    user: {
      id: number;
      name: string;
      profile_image_url: string | null;
    };
  }[];
}

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

export default function DashboardPage() {
  const { user, token } = useAuthStore();
  const { metrics, loading, error, fetchMetrics } = useDashboardStore();
  const [date, setDate] = useState<Date>(new Date());
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [connectionStatus, setConnectionStatus] = useState<string>("");
  const [urgentTasks, setUrgentTasks] = useState([
    { id: '1', title: 'Finish monthly reporting', due_date: new Date().toISOString() },
    { id: '2', title: 'Report signing', due_date: new Date().toISOString() },
    { id: '3', title: 'Market overview keynote', due_date: new Date().toISOString() },
  ]);
  const [teamMembers] = useState([
    { id: '1', name: 'Dana R.', role: 'Project Manager', avatar: '/default-avatar.png' },
    { id: '2', name: 'Peter McCloud', role: 'Team Lead', avatar: '/default-avatar.png' },
    { id: '3', name: 'Nancy K.', role: 'Account Manager', avatar: '/default-avatar.png' },
    { id: '4', name: 'James M.', role: 'Digital Manager', avatar: '/default-avatar.png' },
  ]);

  // WebSocket connection
  const wsStatus = useWebSocket(selectedProject);

  // Effect to update connection status
  useEffect(() => {
    setConnectionStatus(wsStatus);
  }, [wsStatus]);

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

  useEffect(() => {
    if (token) {
      fetchMetrics(token);
    }
  }, [token, fetchMetrics]);

  useEffect(() => {
    async function fetchData() {
      try {
        const projectsData = await getRecentProjects();
        const accessibleProjects = projectsData.filter(project => 
          project.created_by === Number(user?.id) || project.has_user_tasks === true
        );
        setProjects(accessibleProjects);
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      }
    }

    if (user) {
      fetchData();
    }
  }, [user]);

  if (loading) {
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

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Project Dashboard</h1>
        <Card className="bg-red-50">
          <CardContent className="p-4">
            <p className="text-red-600">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const taskStates = Object.keys(metrics.tasksByState || {});
  const hasTaskData = taskStates.length > 0 && taskStates[0] !== 'No Data';
  const suggestions = metrics.aiInsights?.suggestions || [];
  const riskLevel = metrics.aiInsights?.riskLevel || 'Low';
  const predictedDelays = metrics.aiInsights?.predictedDelays || 0;

  return (
    <div className="container mx-auto p-6">
      {/* Header with Search and Connection Status */}
      <div className="flex justify-between items-center mb-8">
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

      {/* Metrics Section */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <KPICard
         title="Total Tasks"
          value={metrics.totalTasks || 0}
          description="Active tasks" 
        />
        <KPICard
          title="Completed Tasks"
          value={metrics.completedTasks || 0}
          trend={
            (metrics.completedTasks || 0) > 0
              ? (((metrics.completedTasks || 0) / (metrics.totalTasks || 1)) * 100)
              : 0
          }
          description="Completion rate"
        />
        <KPICard
          title="Avg. Completion Time"
          value={`${Math.round(metrics.averageCompletionTime || 0)}h`}
          description="Per task"
        />
        <KPICard
          title="Productivity Score"
          value={`${Math.round((metrics.productivityScore || 0) * 100)}%`}
          trend={10}
          description="Last 30 days"
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
                {urgentTasks.map((task) => (
                  <div key={task.id} className="flex items-center justify-between">
                    <p className="text-sm">{task.title}</p>
                    <span className="text-xs text-red-500">Today</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Middle Column - Charts and AI Insights */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* Charts Section */}
          <Card>
            <CardContent className="p-4">
              <ProjectMetricsChart
                title="Task Trend"
                type="line"
                data={{
                  labels: metrics.taskTrend?.labels || [],
                  datasets: [
                    {
                      label: "Created",
                      data: metrics.taskTrend?.created || [],
                      borderColor: "#2563eb",
                      fill: false,
                    },
                    {
                      label: "Completed",
                      data: metrics.taskTrend?.completed || [],
                      borderColor: "#16a34a",
                      fill: false,
                    },
                  ],
                }}
              />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <ProjectMetricsChart
                title="Task Distribution"
                type="doughnut"
                data={{
                  labels: hasTaskData ? taskStates : ['No Data'],
                  datasets: [
                    {
                      data: hasTaskData 
                        ? Object.values(metrics.tasksByState)
                        : [1],
                      backgroundColor: hasTaskData ? [
                        "#2563eb", // blue
                        "#16a34a", // green
                        "#dc2626", // red
                        "#ca8a04", // yellow
                        "#7c3aed", // purple
                      ] : ["#e5e7eb"], // gray for no data
                    },
                  ],
                }}
              />
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