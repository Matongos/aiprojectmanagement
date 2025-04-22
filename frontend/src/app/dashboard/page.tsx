"use client";

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { BarChart, Calendar, CheckCircle2, Clock, TrendingUp, Users } from 'lucide-react';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { getRecentProjects, getUpcomingTasks } from '@/lib/api';

interface Project {
  id: string;
  name: string;
  description: string;
  progress: number;
  team_size: number;
  deadline: string;
}

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  due_date: string;
  project_id: string;
  project_name: string;
}

export default function Dashboard() {
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const projectsData = await getRecentProjects();
        const tasksData = await getUpcomingTasks();
        setProjects(projectsData);
        setTasks(tasksData);
      } catch (error) {
        console.error('Failed to fetch dashboard data', error);
      } finally {
        setLoading(false);
      }
    }

    if (user) {
      fetchData();
    }
  }, [user]);

  // These would be calculated from real data
  const stats = {
    totalProjects: projects.length || 0,
    completedTasks: 14,
    upcomingDeadlines: 3,
    teamMembers: 8,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-gray-100">
      <h1 className="text-2xl font-bold mb-6 text-blue-400">Dashboard</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="bg-gray-800 border border-gray-700">
          <CardContent className="p-6 flex items-center space-x-4">
            <div className="bg-blue-900/30 p-2 rounded-full">
              <TrendingUp className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-400">Active Projects</p>
              <h3 className="text-2xl font-bold text-white">{stats.totalProjects}</h3>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800 border border-gray-700">
          <CardContent className="p-6 flex items-center space-x-4">
            <div className="bg-green-900/30 p-2 rounded-full">
              <CheckCircle2 className="h-6 w-6 text-green-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-400">Completed Tasks</p>
              <h3 className="text-2xl font-bold text-white">{stats.completedTasks}</h3>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800 border border-gray-700">
          <CardContent className="p-6 flex items-center space-x-4">
            <div className="bg-amber-900/30 p-2 rounded-full">
              <Clock className="h-6 w-6 text-amber-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-400">Upcoming Deadlines</p>
              <h3 className="text-2xl font-bold text-white">{stats.upcomingDeadlines}</h3>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800 border border-gray-700">
          <CardContent className="p-6 flex items-center space-x-4">
            <div className="bg-blue-900/30 p-2 rounded-full">
              <Users className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-400">Team Members</p>
              <h3 className="text-2xl font-bold text-white">{stats.teamMembers}</h3>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Projects */}
        <div className="lg:col-span-2">
          <Card className="bg-gray-800 border border-gray-700">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-xl text-blue-400">Recent Projects</CardTitle>
                <Link 
                  href="/dashboard/projects" 
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  View all
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {projects.length > 0 ? (
                  projects.map((project) => (
                    <div key={project.id} className="bg-gray-700 p-4 rounded-lg border border-gray-600">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-medium text-white">{project.name}</h3>
                          <p className="text-sm text-gray-300 truncate">{project.description}</p>
                        </div>
                        <span className="bg-blue-900/50 text-blue-300 text-xs px-2.5 py-0.5 rounded">
                          {new Date(project.deadline).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <div className="w-full max-w-xs">
                          <div className="flex justify-between text-xs mb-1 text-gray-300">
                            <span>Progress</span>
                            <span>{project.progress}%</span>
                          </div>
                          <Progress value={project.progress} className="h-2" />
                        </div>
                        <div className="flex items-center space-x-1 ml-4">
                          <Users className="h-4 w-4 text-gray-400" />
                          <span className="text-xs text-gray-400">{project.team_size}</span>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 bg-gray-700 rounded-lg border border-gray-600">
                    <p className="text-gray-300">No projects found</p>
                    <Link 
                      href="/dashboard/projects/new" 
                      className="mt-2 inline-block text-sm text-blue-400 hover:text-blue-300"
                    >
                      Create your first project
                    </Link>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
        
        {/* Upcoming Tasks */}
        <div>
          <Card className="bg-gray-800 border border-gray-700">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-xl text-blue-400">Upcoming Tasks</CardTitle>
                <Link 
                  href="/dashboard/tasks" 
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  View all
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {tasks.length > 0 ? (
                  tasks.map((task) => (
                    <div 
                      key={task.id} 
                      className="p-3 bg-gray-700 rounded-lg border border-gray-600 flex items-start"
                    >
                      <div className="mr-3 mt-1">
                        <Calendar className="h-5 w-5 text-blue-400" />
                      </div>
                      <div>
                        <h4 className="font-medium text-white">{task.title}</h4>
                        <p className="text-xs text-gray-300 mb-1">Due: {new Date(task.due_date).toLocaleDateString()}</p>
                        <div className="flex items-center">
                          <span className="text-xs bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded">
                            {task.project_name}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 bg-gray-700 rounded-lg border border-gray-600">
                    <p className="text-gray-300">No upcoming tasks</p>
                    <Link 
                      href="/dashboard/tasks/new" 
                      className="mt-2 inline-block text-sm text-blue-400 hover:text-blue-300"
                    >
                      Create a task
                    </Link>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
} 