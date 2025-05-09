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
  Upload,
  Download,
  Trash2
} from "lucide-react";
import { API_BASE_URL, DEFAULT_AVATAR_URL } from "@/lib/constants";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";
import AuthWrapper from "@/components/AuthWrapper";
import { use } from "react";

interface Task {
  id: number;
  name: string;
  description: string;
  state: 'draft' | 'in_progress' | 'done' | 'canceled';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  project_id: number;
  stage_id: number;
  parent_id: number | null;
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
  created_by: number;
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
  task_id: number;
  parent_id: number | null;
  created_at: string;
  user: {
    id: number;
    name: string;
    profile_image_url: string | null;
  };
}

interface FileAttachment {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  description: string | null;
  task_id: number;
  uploaded_by: number;
  created_at: string;
  updated_at: string | null;
}

function TaskDetailsContent({ projectId, taskId }: { projectId: string; taskId: string }) {
  const router = useRouter();
  const { token, user } = useAuthStore();
  const [task, setTask] = useState<Task | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editedTask, setEditedTask] = useState<Partial<Task>>({});
  const [loading, setLoading] = useState(true);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [projectUsers, setProjectUsers] = useState<Array<{
    id: number;
    name: string;
    profile_image_url: string | null;
  }>>([]);

  useEffect(() => {
    const fetchTaskDetails = async () => {
      try {
        const storedToken = token || localStorage.getItem('token');
        if (!storedToken) {
          console.error("No token available");
          router.push('/auth/login');
          return;
        }

        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${storedToken}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          mode: 'cors'
        });

        if (response.status === 401) {
          console.error("Unauthorized access");
          router.push('/auth/login');
          return;
        }

        if (!response.ok) {
          throw new Error("Failed to fetch task details");
        }

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
        const storedToken = token || localStorage.getItem('token');
        if (!storedToken) return;

        const response = await fetch(`${API_BASE_URL}/comments/task/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${storedToken}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          mode: 'cors'
        });

        if (!response.ok) throw new Error("Failed to fetch comments");

        const data = await response.json();
        setComments(data);
      } catch (error) {
        console.error("Error fetching comments:", error);
      }
    };

    const fetchAttachments = async () => {
      try {
        const storedToken = token || localStorage.getItem('token');
        if (!storedToken) return;

        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/attachments`, {
          headers: {
            'Authorization': `Bearer ${storedToken}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          mode: 'cors'
        });

        if (!response.ok) throw new Error("Failed to fetch attachments");

        const data = await response.json();
        setAttachments(data);
      } catch (error) {
        console.error("Error fetching attachments:", error);
      }
    };

    const fetchProjectUsers = async () => {
      try {
        const storedToken = token || localStorage.getItem('token');
        if (!storedToken) return;

        const response = await fetch(`${API_BASE_URL}/projects/${projectId}/members`, {
          headers: {
            'Authorization': `Bearer ${storedToken}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) throw new Error("Failed to fetch project members");

        const data = await response.json();
        setProjectUsers(data);
      } catch (error) {
        console.error("Error fetching project members:", error);
        toast.error("Failed to load project members");
      }
    };

    fetchTaskDetails();
    fetchComments();
    fetchAttachments();
    fetchProjectUsers();
  }, [taskId, token, router, projectId]);

  const handleSave = async () => {
    try {
      const storedToken = token || localStorage.getItem('token');
      if (!storedToken) {
        router.push('/auth/login');
        return;
      }

      // Only send fields that are allowed to be updated
      const updateData = {
        name: editedTask.name,
        description: editedTask.description,
        state: editedTask.state,
        priority: editedTask.priority,
        assigned_to: editedTask.assigned_to,
        deadline: editedTask.deadline,
        planned_hours: editedTask.planned_hours,
        start_date: editedTask.start_date,
        end_date: editedTask.end_date
      };

      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: "PUT",
        headers: {
          'Authorization': `Bearer ${storedToken}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        mode: 'cors',
        body: JSON.stringify(updateData)
      });

      if (response.status === 401) {
        router.push('/auth/login');
        return;
      }

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
      const storedToken = token || localStorage.getItem('token');
      if (!storedToken) {
        router.push('/auth/login');
        return;
      }

      const commentData = {
        content: newComment,
        task_id: parseInt(taskId),
        parent_id: null,
        mentions: []
      };

      const response = await fetch(`${API_BASE_URL}/comments`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${storedToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(commentData)
      });

      if (response.status === 401) {
        router.push('/auth/login');
        return;
      }

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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setUploadingFile(true);
      const storedToken = token || localStorage.getItem('token');
      if (!storedToken) {
        router.push('/auth/login');
        return;
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('description', '');

      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/attachments`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${storedToken}`
        },
        body: formData
      });

      if (response.status === 401) {
        router.push('/auth/login');
        return;
      }

      if (!response.ok) throw new Error("Failed to upload file");

      const newAttachment = await response.json();
      setAttachments(prev => [...prev, newAttachment]);
      toast.success("File uploaded successfully");
    } catch (error) {
      console.error("Error uploading file:", error);
      toast.error("Failed to upload file");
    } finally {
      setUploadingFile(false);
    }
  };

  const handleDownloadFile = async (fileId: number, filename: string) => {
    try {
      const storedToken = token || localStorage.getItem('token');
      if (!storedToken) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch(`${API_BASE_URL}/file-attachments/${fileId}/download`, {
        headers: {
          'Authorization': `Bearer ${storedToken}`
        }
      });

      if (response.status === 401) {
        router.push('/auth/login');
        return;
      }

      if (!response.ok) throw new Error("Failed to download file");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Error downloading file:", error);
      toast.error("Failed to download file");
    }
  };

  const handleDeleteFile = async (fileId: number) => {
    if (!window.confirm("Are you sure you want to delete this file?")) return;

    try {
      const storedToken = token || localStorage.getItem('token');
      if (!storedToken) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch(`${API_BASE_URL}/file-attachments/${fileId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${storedToken}`
        }
      });

      if (response.status === 401) {
        router.push('/auth/login');
        return;
      }

      if (!response.ok) throw new Error("Failed to delete file");

      setAttachments(prev => prev.filter(a => a.id !== fileId));
      toast.success("File deleted successfully");
    } catch (error) {
      console.error("Error deleting file:", error);
      toast.error("Failed to delete file");
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
              <TabsTrigger value="attachments">
                <Upload className="h-4 w-4 mr-2" />
                Attachments
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
                      alt={user?.full_name || ""}
                    />
                    <AvatarFallback>
                      {user?.full_name ? user.full_name[0] : "?"}
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

            <TabsContent value="attachments" className="mt-4">
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                  <Button
                    onClick={() => document.getElementById('file-upload')?.click()}
                    disabled={uploadingFile}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    {uploadingFile ? "Uploading..." : "Upload File"}
                  </Button>
                </div>

                <div className="space-y-2">
                  {attachments.map((attachment) => (
                    <Card key={attachment.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          <span>{attachment.original_filename}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownloadFile(attachment.id, attachment.original_filename)}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteFile(attachment.id)}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
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
                      setEditedTask({ ...editedTask, state: value as Task['state'] })
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

              {/* Priority */}
              <div>
                <label className="text-sm font-medium mb-1 block">Priority</label>
                {isEditing ? (
                  <Select
                    value={editedTask.priority}
                    onValueChange={(value) =>
                      setEditedTask({ ...editedTask, priority: value as Task['priority'] })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Badge>{task.priority}</Badge>
                )}
              </div>

              {/* Assignee */}
              <div>
                <label className="text-sm font-medium mb-1 block">Assignee</label>
                {isEditing ? (
                  <Select
                    value={editedTask.assigned_to ? String(editedTask.assigned_to) : "unassigned"}
                    onValueChange={(value) =>
                      setEditedTask({ ...editedTask, assigned_to: value === "unassigned" ? null : Number(value) })
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select assignee" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unassigned">Unassigned</SelectItem>
                      {projectUsers.map((projectUser) => (
                        <SelectItem key={projectUser.id} value={String(projectUser.id)}>
                          <div className="flex items-center gap-2">
                            <Avatar className="h-6 w-6">
                              <AvatarImage
                                src={projectUser.profile_image_url || DEFAULT_AVATAR_URL}
                                alt={projectUser.name}
                              />
                              <AvatarFallback>{projectUser.name[0]}</AvatarFallback>
                            </Avatar>
                            <span>{projectUser.name}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="flex items-center gap-2">
                    {task.assignee ? (
                      <>
                        <Avatar className="h-6 w-6">
                          <AvatarImage
                            src={task.assignee.profile_image_url || DEFAULT_AVATAR_URL}
                            alt={task.assignee.name}
                          />
                          <AvatarFallback>{task.assignee.name[0]}</AvatarFallback>
                        </Avatar>
                        <span>{task.assignee.name}</span>
                      </>
                    ) : (
                      <span className="text-gray-500">Unassigned</span>
                    )}
                  </div>
                )}
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

export default function TaskDetailsPage({ params }: { params: Promise<{ id: string; taskId: string }> }) {
  const resolvedParams = use(params);
  
  return (
    <AuthWrapper>
      <TaskDetailsContent projectId={resolvedParams.id} taskId={resolvedParams.taskId} />
    </AuthWrapper>
  );
}