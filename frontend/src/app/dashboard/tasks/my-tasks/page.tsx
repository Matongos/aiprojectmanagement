"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Search } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import TaskList from "@/components/TaskList";
import { toast } from "react-hot-toast";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: string;
  due_date: string;
  project_id: number;
  assignee_id: number;
  creator_id: number;
  project: {
    name: string;
  };
}

function MyTasksContent() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const { token, user } = useAuthStore();

  useEffect(() => {
    const fetchMyTasks = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/tasks/my-tasks`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch tasks");
        }

        const data = await response.json();
        setTasks(data);
      } catch (error) {
        console.error("Error fetching tasks:", error);
        toast.error("Failed to load tasks");
      } finally {
        setLoading(false);
      }
    };

    fetchMyTasks();
  }, [token]);

  const handleTaskClick = (taskId: number) => {
    router.push(`/dashboard/tasks/${taskId}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">My Tasks</h1>
          <p className="text-gray-600">Tasks assigned to {user?.full_name}</p>
        </div>
        <div className="flex items-center gap-4">
          <Button onClick={() => router.push("/dashboard/tasks/create")}>
            <Plus className="h-4 w-4 mr-2" />
            New Task
          </Button>
        </div>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold mb-2">No tasks assigned to you</h2>
          <p className="text-gray-600 mb-4">
            You currently don't have any tasks assigned. Create a new task or wait for assignments.
          </p>
          <Button onClick={() => router.push("/dashboard/tasks/create")}>
            Create New Task
          </Button>
        </div>
      ) : (
        <TaskList tasks={tasks} onTaskClick={handleTaskClick} />
      )}
    </div>
  );
}

export default function MyTasksPage() {
  return (
    <AuthWrapper>
      <MyTasksContent />
    </AuthWrapper>
  );
} 