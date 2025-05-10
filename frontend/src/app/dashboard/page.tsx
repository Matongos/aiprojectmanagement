"use client";

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Calendar as CalendarIcon, Search } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { getRecentProjects } from '@/lib/api';
import { Calendar } from '@/components/ui/calendar';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";

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
  meta_data: Record<string, string | number | boolean | null> | null;
  created_at: string;
  updated_at: string;
  is_active: boolean;
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

interface Task {
  id: string;
  title: string;
  due_date: string;
}

interface Comment {
  id: string;
  user: TeamMember;
  project: string;
  message: string;
  timestamp: string;
}

interface TeamMember {
  id: string;
  name: string;
  role: string;
  avatar: string;
}

export default function Dashboard() {
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [urgentTasks, setUrgentTasks] = useState<Task[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [date, setDate] = useState<Date>(new Date());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        
        const projectsData = await getRecentProjects();
        setProjects(projectsData || []);
        
        // Mock data for now
        setUrgentTasks([
          { id: '1', title: 'Finish monthly reporting', due_date: new Date().toISOString() },
          { id: '2', title: 'Report signing', due_date: new Date().toISOString() },
          { id: '3', title: 'Market overview keynote', due_date: new Date().toISOString() },
        ]);

        setComments([
          {
            id: '1',
            user: { id: '1', name: 'Elsa S.', role: 'Designer', avatar: '/default-avatar.png' },
            project: 'Market research 2024',
            message: 'Find my keynote attached in the...',
            timestamp: new Date().toISOString()
          },
          {
            id: '2',
            user: { id: '2', name: 'Dana R.', role: 'Developer', avatar: '/default-avatar.png' },
            project: 'Market research 2024',
            message: "I've added some new data. Let's...",
            timestamp: new Date().toISOString()
          }
        ]);

        setTeamMembers([
          { id: '1', name: 'Dana R.', role: 'Project Manager', avatar: '/default-avatar.png' },
          { id: '2', name: 'Peter McCloud', role: 'Team Lead', avatar: '/default-avatar.png' },
          { id: '3', name: 'Nancy K.', role: 'Account Manager', avatar: '/default-avatar.png' },
          { id: '4', name: 'James M.', role: 'Digital Manager', avatar: '/default-avatar.png' },
        ]);

      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        setError(error instanceof Error ? error.message : 'Failed to load dashboard data. Please try again later.');
        setProjects([]); // Set empty projects array on error
      } finally {
        setLoading(false);
      }
    }

    if (user) {
      fetchData();
    } else {
      setLoading(false);
      setError('Please log in to view dashboard data.');
    }
  }, [user]);

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-gray-600">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="text-red-500 mb-4">{error}</div>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      {/* Header with Search */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-semibold mb-1">Welcome, {user?.full_name || 'User'}!</h1>
          <p className="text-gray-600">Here is your agenda for today</p>
        </div>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
          <Input
            placeholder="Search..."
            className="pl-10 w-full"
          />
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Column */}
        <div className="col-span-12 lg:col-span-4">
          {/* Calendar */}
          <Card className="mb-6">
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
          <Card className="mb-6">
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
                          <p className="text-xs text-gray-500">{project.members?.length || 0} members</p>
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
        </div>

        {/* Middle Column */}
        <div className="col-span-12 lg:col-span-4">
          {/* Urgent Tasks */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Urgent tasks</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {urgentTasks.map((task) => (
                  <div key={task.id} className="flex items-center justify-between">
                    <p className="text-sm">{task.name}</p>
                    <span className="text-xs text-red-500">Today</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* New Comments */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">New comments</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {comments.map((comment) => (
                  <div key={comment.id} className="flex items-start space-x-3">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={comment.user.avatar} alt={comment.user.name} />
                      <AvatarFallback>{comment.user.name[0]}</AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium">{comment.user.name}</p>
                        <p className="text-xs text-gray-500">in {comment.project}</p>
                      </div>
                      <p className="text-sm text-gray-600">{comment.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="col-span-12 lg:col-span-4">
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
    </div>
  );
} 