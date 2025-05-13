"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";
import TaskList from "@/components/TaskList";
import { toast } from "react-hot-toast";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";
import { TaskState } from "@/types/task";

interface Tag {
  id: number;
  name: string;
  color: number;
  active: boolean;
}

interface Task {
  id: number;
  title: string;
  description: string;
  state: TaskState;
  priority: "low" | "medium" | "high" | "urgent";
  project_id: number;
  stage_id: number;
  assigned_to: number;
  milestone_id: number;
  deadline: string;
  progress: number;
  created_at: string;
  updated_at: string;
  tags: Tag[];
  project: {
    id: number;
    name: string;
  };
  assignee: {
    id: number;
    username: string;
    full_name: string;
    profile_image_url: string | null;
  };
}

function MyTasksPage() {
  const router = useRouter();
  const { token } = useAuthStore();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTasks = async () => {
      if (!token) return;

      try {
        const response = await fetch(`${API_BASE_URL}/tasks/my-tasks`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch tasks');
        }

        const data = await response.json();
        setTasks(data);
      } catch (error) {
        console.error('Error fetching tasks:', error);
        toast.error('Failed to load tasks');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTasks();
  }, [token]);

  const handleTaskClick = (taskId: number) => {
    router.push(`/dashboard/tasks/${taskId}`);
  };

  return (
    <AuthWrapper>
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-semibold">My Tasks</h1>
          <Button onClick={() => router.push('/dashboard/tasks/new')}>
            Create Task
          </Button>
        </div>

        {isLoading ? (
          <div className="text-center py-10">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading tasks...</p>
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-10">
            <p className="text-gray-600">No tasks found</p>
          </div>
        ) : (
          <TaskList tasks={tasks} onTaskClick={handleTaskClick} />
        )}
      </div>
    </AuthWrapper>
  );
}

export default MyTasksPage; 