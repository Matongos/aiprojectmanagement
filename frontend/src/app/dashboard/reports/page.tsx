"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuthStore } from "@/store/authStore";
import { API_BASE_URL } from "@/lib/constants";
import { toast } from "react-hot-toast";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { Download, Filter, BarChart2, LineChart as LineChartIcon, PieChart as PieChartIcon } from "lucide-react";

interface Project {
  id: number;
  name: string;
}

interface ProjectStats {
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
}

interface TaskDistribution {
  status: string;
  count: number;
}

interface UserProductivity {
  completed_tasks: number;
  avg_completion_time_hours: number;
  over_budget_tasks: number;
  over_budget_percentage: number;
  days_analyzed: number;
}

interface TaskAnalytics {
  allocated_time: number;
  days_to_deadline: number;
  hours_spent: number;
  progress: number;
  remaining_hours: number;
  remaining_hours_percentage: number;
  total_hours: number;
  working_days_to_assign: number;
  working_hours_to_assign: number;
  working_hours_to_close: number;
  tasks_by_project: {
    project_name: string;
    task_count: number;
  }[];
  tasks_by_tag: {
    tag_name: string;
    task_count: number;
  }[];
}

interface TaskMetric {
  label: string;
  value: string;
  key: keyof TaskAnalytics;
}

type ChartType = 'bar' | 'line' | 'pie';

export default function ReportsPage() {
  const { token } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectStats, setProjectStats] = useState<ProjectStats | null>(null);
  const [taskDistribution, setTaskDistribution] = useState<TaskDistribution[]>([]);
  const [userProductivity, setUserProductivity] = useState<UserProductivity | null>(null);
  const [loading, setLoading] = useState(true);
  const [reportType, setReportType] = useState<"projects" | "tasks">(
    (searchParams.get("type") as "projects" | "tasks") || "projects"
  );
  const [taskSummary, setTaskSummary] = useState<any>(null);
  const [taskTrend, setTaskTrend] = useState<any[]>([]);
  const [taskAnalytics, setTaskAnalytics] = useState<TaskAnalytics | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<keyof TaskAnalytics>("hours_spent");
  const [chartType, setChartType] = useState<ChartType>('bar');
  const [stackedView, setStackedView] = useState(false);

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

  useEffect(() => {
    const type = searchParams.get("type") as "projects" | "tasks";
    if (type) {
      setReportType(type);
    }
    fetchProjects();
  }, [searchParams]);

  useEffect(() => {
    if (reportType === "tasks") {
      fetchTaskData();
    } else if (reportType === "projects" && selectedProject) {
      fetchProjectData(parseInt(selectedProject));
    }
  }, [reportType, selectedProject]);

  const fetchProjects = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/projects`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) throw new Error('Failed to fetch projects');
      const data = await response.json();
      setProjects(data);
      if (data.length > 0) {
        setSelectedProject(data[0].id.toString());
      }
    } catch (error) {
      console.error('Error fetching projects:', error);
      toast.error('Failed to load projects');
    }
  };

  const fetchProjectData = async (projectId: number) => {
    setLoading(true);
    try {
      const [statsRes, distributionRes, productivityRes] = await Promise.all([
        fetch(`${API_BASE_URL}/analytics/project/${projectId}/completion`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE_URL}/analytics/project/${projectId}/task-distribution`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE_URL}/analytics/user/productivity`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (!statsRes.ok || !distributionRes.ok || !productivityRes.ok) {
        throw new Error('Failed to fetch project analytics');
      }

      const [stats, distribution, productivity] = await Promise.all([
        statsRes.json(),
        distributionRes.json(),
        productivityRes.json(),
      ]);

      setProjectStats(stats);
      setTaskDistribution(distribution);
      setUserProductivity(productivity);
    } catch (error) {
      console.error('Error fetching project data:', error);
      toast.error('Failed to load project analytics');
    } finally {
      setLoading(false);
    }
  };

  const fetchTaskData = async () => {
    setLoading(true);
    try {
      const [summaryRes, trendRes, analyticsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/analytics/tasks/summary`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE_URL}/analytics/tasks/trend`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE_URL}/analytics/tasks/analysis`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (!summaryRes.ok || !trendRes.ok || !analyticsRes.ok) {
        throw new Error('Failed to fetch task analytics');
      }

      const [summary, trend, analytics] = await Promise.all([
        summaryRes.json(),
        trendRes.json(),
        analyticsRes.json(),
      ]);

      setTaskSummary(summary);
      setTaskTrend(trend);
      setTaskAnalytics(analytics);
    } catch (error) {
      console.error('Error fetching task data:', error);
      toast.error('Failed to load task analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    // TODO: Implement export functionality
    toast.success('Report exported successfully');
  };

  const handleReportTypeChange = (value: "projects" | "tasks") => {
    setReportType(value);
    router.push(`/dashboard/reports?type=${value}`, { scroll: false });
  };

  const renderChart = (data: any[], type: ChartType) => {
    switch (type) {
      case 'line':
        return (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="project_name" />
            <YAxis />
            <Tooltip />
            <Legend />
            {Object.keys(data[0] || {})
              .filter(key => key !== 'project_name' && key !== 'name')
              .map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                  stroke={COLORS[index % COLORS.length]}
                />
              ))}
          </LineChart>
        );
      case 'pie':
        return (
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        );
      default:
        return (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="project_name" />
            <YAxis />
            <Tooltip />
            <Legend />
            {Object.keys(data[0] || {})
              .filter(key => key !== 'project_name' && key !== 'name')
              .map((key, index) => (
                <Bar
                  key={key}
                  dataKey={key}
                  name={key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                  fill={COLORS[index % COLORS.length]}
                  stackId={stackedView ? "stack" : undefined}
                />
              ))}
          </BarChart>
        );
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96">Loading...</div>;
  }

  const renderProjectReport = () => (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Project Completion</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-2">
              {projectStats?.completion_rate.toFixed(1)}%
            </div>
            <p className="text-sm text-gray-500">
              {projectStats?.completed_tasks} of {projectStats?.total_tasks} tasks completed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Average Task Completion</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-2">
              {userProductivity?.avg_completion_time_hours.toFixed(1)}h
            </div>
            <p className="text-sm text-gray-500">
              Average time to complete tasks
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tasks Over Budget</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-2">
              {userProductivity?.over_budget_percentage.toFixed(1)}%
            </div>
            <p className="text-sm text-gray-500">
              {userProductivity?.over_budget_tasks} tasks exceeded estimated time
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Task Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={taskDistribution}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {taskDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Productivity Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    { name: 'Completed', value: userProductivity?.completed_tasks || 0 },
                    { name: 'Over Budget', value: userProductivity?.over_budget_tasks || 0 },
                  ]}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );

  const taskMetrics: TaskMetric[] = [
    { label: "Allocated Time", value: "allocated_time", key: "allocated_time" },
    { label: "Days to Deadline", value: "days_to_deadline", key: "days_to_deadline" },
    { label: "Hours Spent", value: "hours_spent", key: "hours_spent" },
    { label: "Progress", value: "progress", key: "progress" },
    { label: "Remaining Hours", value: "remaining_hours", key: "remaining_hours" },
    { label: "Remaining Hours %", value: "remaining_hours_percentage", key: "remaining_hours_percentage" },
    { label: "Total Hours", value: "total_hours", key: "total_hours" },
    { label: "Working Days to Assign", value: "working_days_to_assign", key: "working_days_to_assign" },
    { label: "Working Hours to Assign", value: "working_hours_to_assign", key: "working_hours_to_assign" },
    { label: "Working Hours to Close", value: "working_hours_to_close", key: "working_hours_to_close" },
  ];

  const renderTaskReport = () => (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Total Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-2">
              {taskSummary?.total_tasks || 0}
            </div>
            <p className="text-sm text-gray-500">
              All tasks in the system
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Hours Spent</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-2">
              {taskAnalytics?.hours_spent || 0}h
            </div>
            <p className="text-sm text-gray-500">
              Total hours spent on tasks
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Remaining Hours</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-2">
              {taskAnalytics?.remaining_hours || 0}h
            </div>
            <p className="text-sm text-gray-500">
              {taskAnalytics?.remaining_hours_percentage || 0}% of total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Average Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-2">
              {taskAnalytics?.progress || 0}%
            </div>
            <p className="text-sm text-gray-500">
              Overall task completion
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Task Analysis</CardTitle>
            <div className="flex items-center space-x-2">
              <Select value={selectedMetric} onValueChange={(value) => setSelectedMetric(value as keyof TaskAnalytics)}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select metric" />
                </SelectTrigger>
                <SelectContent>
                  {taskMetrics.map((metric) => (
                    <SelectItem key={metric.value} value={metric.key}>
                      {metric.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <div className="flex items-center space-x-1 border rounded-md">
                <Button
                  variant={chartType === 'bar' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setChartType('bar')}
                  className="px-2 py-1"
                >
                  <BarChart2 className="h-4 w-4" />
                </Button>
                <Button
                  variant={chartType === 'line' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setChartType('line')}
                  className="px-2 py-1"
                >
                  <LineChartIcon className="h-4 w-4" />
                </Button>
                <Button
                  variant={chartType === 'pie' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setChartType('pie')}
                  className="px-2 py-1"
                >
                  <PieChartIcon className="h-4 w-4" />
                </Button>
              </div>

              {chartType === 'bar' && (
                <Button
                  variant={stackedView ? 'secondary' : 'outline'}
                  size="sm"
                  onClick={() => setStackedView(!stackedView)}
                >
                  {stackedView ? 'Stacked' : 'Grouped'}
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                {renderChart(taskAnalytics?.tasks_by_project || [], chartType)}
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Tasks by Project Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={taskAnalytics?.tasks_by_project || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="project_name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="task_count" name="Tasks" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Task Distribution by Tag</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={taskAnalytics?.tasks_by_tag || []}
                    dataKey="task_count"
                    nameKey="tag_name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {(taskAnalytics?.tasks_by_tag || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Task Progress Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={taskTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="completed" name="Completed Tasks" stroke="#82ca9d" />
                  <Line type="monotone" dataKey="in_progress" name="In Progress" stroke="#8884d8" />
                  <Line type="monotone" dataKey="overdue" name="Overdue" stroke="#ff7300" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Reports & Analytics</h1>
        <div className="flex items-center gap-4">
          <Select value={reportType} onValueChange={handleReportTypeChange}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select report type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="projects">Project Reports</SelectItem>
              <SelectItem value="tasks">Task Reports</SelectItem>
            </SelectContent>
          </Select>

          {reportType === "projects" && (
            <Select value={selectedProject} onValueChange={setSelectedProject}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select project" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id.toString()}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {reportType === "projects" ? renderProjectReport() : renderTaskReport()}
    </div>
  );
} 