"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Plus, Search } from "lucide-react";
import { toast } from "react-hot-toast";
import { useRouter } from "next/navigation";

interface Task {
  id: number;
  title: string;
  description: string;
  status: "todo" | "in_progress" | "review" | "done" | "cancelled";
  priority: "low" | "medium" | "high" | "urgent";
  due_date: string;
  project_id: number;
  assignee_id: number;
  creator_id: number;
}

const statusColumns = [
  { id: "todo", label: "To Do", color: "bg-gray-100" },
  { id: "in_progress", label: "In Progress", color: "bg-blue-100" },
  { id: "review", label: "Review", color: "bg-yellow-100" },
  { id: "done", label: "Done", color: "bg-green-100" },
];

const priorityColors = {
  low: "bg-gray-100 text-gray-800",
  medium: "bg-blue-100 text-blue-800",
  high: "bg-orange-100 text-orange-800",
  urgent: "bg-red-100 text-red-800",
};

export default function TaskBoardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const { token } = useAuthStore();
  const router = useRouter();

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://192.168.56.1:8003/tasks/", {
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

  useEffect(() => {
    fetchTasks();
  }, [token]);

  const handleUpdateTaskStatus = async (taskId: number, newStatus: string) => {
    try {
      const response = await fetch(`http://192.168.56.1:8003/tasks/${taskId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: newStatus,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to update task status");
      }

      toast.success("Task status updated");
      fetchTasks();
    } catch (error) {
      console.error("Error updating task status:", error);
      toast.error("Failed to update task status");
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!window.confirm("Are you sure you want to delete this task?")) {
      return;
    }

    try {
      const response = await fetch(`http://192.168.56.1:8003/tasks/${taskId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to delete task");
      }

      toast.success("Task deleted successfully");
      fetchTasks();
    } catch (error) {
      console.error("Error deleting task:", error);
      toast.error("Failed to delete task");
    }
  };

  const filteredTasks = tasks.filter((task) =>
    task.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTasksByStatus = (status: string) =>
    filteredTasks.filter((task) => task.status === status);

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Task Board</h1>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 w-64"
            />
          </div>
          <Button onClick={() => router.push("/dashboard/tasks/create")}>
            <Plus className="h-4 w-4 mr-2" />
            New Task
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {statusColumns.map((column) => (
          <div key={column.id} className={`${column.color} rounded-lg p-4`}>
            <h2 className="font-semibold mb-4">{column.label}</h2>
            <div className="space-y-4">
              {getTasksByStatus(column.id).map((task) => (
                <Card key={task.id} className="p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-medium">{task.title}</h3>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() =>
                            router.push(`/dashboard/tasks/${task.id}`)
                          }
                        >
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() =>
                            router.push(`/dashboard/tasks/${task.id}/edit`)
                          }
                        >
                          Edit
                        </DropdownMenuItem>
                        {statusColumns.map(
                          (col) =>
                            col.id !== task.status && (
                              <DropdownMenuItem
                                key={col.id}
                                onClick={() =>
                                  handleUpdateTaskStatus(task.id, col.id)
                                }
                              >
                                Move to {col.label}
                              </DropdownMenuItem>
                            )
                        )}
                        <DropdownMenuItem
                          onClick={() => handleDeleteTask(task.id)}
                          className="text-red-600"
                        >
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                    {task.description}
                  </p>
                  <div className="flex justify-between items-center">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        priorityColors[task.priority]
                      }`}
                    >
                      {task.priority}
                    </span>
                    <span className="text-xs text-gray-500">
                      Due: {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 