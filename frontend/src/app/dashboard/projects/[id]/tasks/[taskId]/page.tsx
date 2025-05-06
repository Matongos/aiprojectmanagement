"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Star,
  Calendar,
  Clock,
  MessageSquare,
  FileText,
  CheckSquare,
  Info,
  Send,
  Plus,
  Edit,
  Save,
  X,
} from "lucide-react";
import { API_BASE_URL, DEFAULT_AVATAR_URL } from "@/lib/constants";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";

interface Task {
  id: number;
  name: string;
  description: string;
  state: string;
  priority: string;
  project_id: number;
  stage_id: number;
  assigned_to: number | null;
  milestone_id: number | null;
  company_id: number | null;
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
  planned_hours: number;
  progress: number;
  created_at: string;
  updated_at: string | null;
  assignee: {
    id: number;
    name: string;
    profile_image_url: string | null;
  } | null;
  milestone: {
    id: number;
    name: string;
  } | null;
  company: {
    id: number;
    name: string;
  } | null;
}

interface Comment {
  id: number;
  content: string;
  created_at: string;
  user: {
    id: number;
    name: string;
    profile_image_url: string | null;
  };
}

export default function TaskDetailsPage({ params }: { params: { id: string; taskId: string } }) {
  const router = useRouter();
  const { token, user } = useAuthStore();
  const [task, setTask] = useState<Task | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editedTask, setEditedTask] = useState<Partial<Task>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTaskDetails = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tasks/${params.taskId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) throw new Error("Failed to fetch task details");

        const data = await response.json();
        setTask(data);
        setEditedTask(data);
      } catch (error) {
        console.error("Error fetching task details:", error);
        toast.error("Failed to load task details");
      } finally {
        setLoading(false);
      }
    };

    const fetchComments = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/tasks/${params.taskId}/comments`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) throw new Error("Failed to fetch comments");

        const data = await response.json();
        setComments(data);
      } catch (error) {
        console.error("Error fetching comments:", error);
      }
    };

    fetchTaskDetails();
    fetchComments();
  }, [params.taskId, token]);

  const handleSave = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${params.taskId}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(editedTask),
      });

      if (!response.ok) throw new Error("Failed to update task");

      const updatedTask = await response.json();
      setTask(updatedTask);
      setIsEditing(false);
      toast.success("Task updated successfully");
    } catch (error) {
      console.error("Error updating task:", error);
      toast.error("Failed to update task");
    }
  };

  const handleCommentSubmit = async () => {
    if (!newComment.trim()) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/tasks/${params.taskId}/comments`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ content: newComment }),
        }
      );

      if (!response.ok) throw new Error("Failed to add comment");

      const comment = await response.json();
      setComments((prev) => [...prev, comment]);
      setNewComment("");
      toast.success("Comment added successfully");
    } catch (error) {
      console.error("Error adding comment:", error);
      toast.error("Failed to add comment");
    }
  };

  if (loading) return <div className="p-4">Loading...</div>;
  if (!task) return <div className="p-4">Task not found</div>;

  return (
    <div className="container mx-auto p-4">
      <div className="flex items-start gap-6">
        {/* Main Content */}
        <div className="flex-1">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div className="flex-1">
              {isEditing ? (
                <Input
                  value={editedTask.name || ""}
                  onChange={(e) =>
                    setEditedTask({ ...editedTask, name: e.target.value })
                  }
                  className="text-xl font-semibold mb-2"
                />
              ) : (
                <h1 className="text-xl font-semibold mb-2">{task.name}</h1>
              )}
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span>Created {new Date(task.created_at).toLocaleDateString()}</span>
                {task.milestone && (
                  <Badge variant="secondary">{task.milestone.name}</Badge>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <Button variant="ghost" onClick={() => setIsEditing(false)}>
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>
                  <Button onClick={handleSave}>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </Button>
                </>
              ) : (
                <Button onClick={() => setIsEditing(true)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
              )}
            </div>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="description" className="w-full">
            <TabsList>
              <TabsTrigger value="description">
                <FileText className="h-4 w-4 mr-2" />
                Description
              </TabsTrigger>
              <TabsTrigger value="comments">
                <MessageSquare className="h-4 w-4 mr-2" />
                Comments
              </TabsTrigger>
              <TabsTrigger value="checklist">
                <CheckSquare className="h-4 w-4 mr-2" />
                Checklist
              </TabsTrigger>
            </TabsList>

            <TabsContent value="description" className="mt-4">
              {isEditing ? (
                <Textarea
                  value={editedTask.description || ""}
                  onChange={(e) =>
                    setEditedTask({ ...editedTask, description: e.target.value })
                  }
                  className="min-h-[200px]"
                  placeholder="Add a description..."
                />
              ) : (
                <div className="prose max-w-none">
                  {task.description || "No description provided."}
                </div>
              )}
            </TabsContent>

            <TabsContent value="comments" className="mt-4">
              <div className="space-y-4">
                {comments.map((comment) => (
                  <Card key={comment.id} className="p-4">
                    <div className="flex items-start gap-3">
                      <Avatar className="h-8 w-8">
                        <AvatarImage
                          src={comment.user.profile_image_url || DEFAULT_AVATAR_URL}
                          alt={comment.user.name}
                        />
                        <AvatarFallback>
                          {comment.user.name[0]}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{comment.user.name}</span>
                          <span className="text-sm text-gray-500">
                            {new Date(comment.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="mt-1 text-gray-700">{comment.content}</p>
                      </div>
                    </div>
                  </Card>
                ))}

                <div className="flex items-start gap-3 mt-4">
                  <Avatar className="h-8 w-8">
                    <AvatarImage
                      src={user?.profile_image_url || DEFAULT_AVATAR_URL}
                      alt={user?.name || ""}
                    />
                    <AvatarFallback>
                      {user?.name ? user.name[0] : "?"}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <Textarea
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      placeholder="Add a comment..."
                      className="mb-2"
                    />
                    <Button onClick={handleCommentSubmit}>
                      <Send className="h-4 w-4 mr-2" />
                      Send
                    </Button>
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="checklist" className="mt-4">
              <div className="space-y-4">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Checklist Item
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className="w-80">
          <Card className="p-4">
            <div className="space-y-4">
              {/* Status */}
              <div>
                <label className="text-sm font-medium mb-1 block">Status</label>
                {isEditing ? (
                  <Select
                    value={editedTask.state}
                    onValueChange={(value) =>
                      setEditedTask({ ...editedTask, state: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="draft">Draft</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="done">Done</SelectItem>
                      <SelectItem value="canceled">Canceled</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Badge>{task.state}</Badge>
                )}
              </div>

              {/* Assignee */}
              <div>
                <label className="text-sm font-medium mb-1 block">Assignee</label>
                <div className="flex items-center gap-2">
                  {task.assignee ? (
                    <>
                      <Avatar className="h-6 w-6">
                        <AvatarImage
                          src={task.assignee.profile_image_url || DEFAULT_AVATAR_URL}
                          alt={task.assignee.name}
                        />
                        <AvatarFallback>
                          {task.assignee.name[0]}
                        </AvatarFallback>
                      </Avatar>
                      <span>{task.assignee.name}</span>
                    </>
                  ) : (
                    <Button variant="ghost" size="sm">
                      <Plus className="h-4 w-4 mr-2" />
                      Assign
                    </Button>
                  )}
                </div>
              </div>

              {/* Dates */}
              <div>
                <label className="text-sm font-medium mb-1 block">Due Date</label>
                {isEditing ? (
                  <Input
                    type="datetime-local"
                    value={editedTask.deadline || ""}
                    onChange={(e) =>
                      setEditedTask({ ...editedTask, deadline: e.target.value })
                    }
                  />
                ) : (
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    <span>
                      {task.deadline
                        ? new Date(task.deadline).toLocaleDateString()
                        : "No due date"}
                    </span>
                  </div>
                )}
              </div>

              {/* Time Tracking */}
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Time Tracking
                </label>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  <span>{task.planned_hours || 0} hours planned</span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}