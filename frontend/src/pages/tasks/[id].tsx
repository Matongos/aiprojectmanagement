import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CalendarIcon, Clock, Users, Tag, ArrowLeft, Calendar, MessageSquare, Paperclip } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { TaskProps } from '@/components/TaskProgressCard';
import { format } from 'date-fns';
import { Progress } from '@/components/ui/progress';
import { Separator, Avatar, Badge } from "@/components/ui";
import { FileAttachmentList, FileAttachmentProps } from '@/components/FileAttachment';
import { getTaskAttachments, uploadTaskAttachment, deleteFileAttachment } from '@/lib/api';

// Task interface
interface Task {
  id: string;
  name: string;
  description: string;
  status: 'todo' | 'in_progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high';
  project: {
    id: string;
    name: string;
  };
  assignees: {
    id: string;
    name: string;
    avatar: string;
  }[];
  createdAt: string;
  dueDate: string | null;
  comments: {
    id: string;
    user: {
      id: string;
      name: string;
      avatar: string;
    };
    content: string;
    createdAt: string;
  }[];
}

// Mock task data
const mockTask: Task = {
  id: '1',
  name: 'Implement user authentication',
  description: 'Create a secure authentication system with JWT tokens and user roles/permissions.',
  status: 'in_progress',
  priority: 'high',
  project: {
    id: '1',
    name: 'Project Management App'
  },
  assignees: [
    { id: '1', name: 'John Doe', avatar: '/avatars/john.png' },
    { id: '2', name: 'Jane Smith', avatar: '/avatars/jane.png' }
  ],
  createdAt: '2023-06-15T10:30:00Z',
  dueDate: '2023-06-25T23:59:59Z',
  comments: [
    {
      id: '1',
      user: { id: '2', name: 'Jane Smith', avatar: '/avatars/jane.png' },
      content: 'I\'ve started working on the authentication middleware.',
      createdAt: '2023-06-16T14:20:00Z'
    },
    {
      id: '2',
      user: { id: '1', name: 'John Doe', avatar: '/avatars/john.png' },
      content: 'Great! I\'ll focus on the frontend auth components.',
      createdAt: '2023-06-16T15:45:00Z'
    }
  ]
};

// Status and priority badges
const statusColors = {
  todo: 'bg-gray-200 text-gray-800',
  in_progress: 'bg-blue-200 text-blue-800',
  review: 'bg-purple-200 text-purple-800',
  done: 'bg-green-200 text-green-800'
};

const priorityColors = {
  low: 'bg-gray-200 text-gray-800',
  medium: 'bg-orange-200 text-orange-800',
  high: 'bg-red-200 text-red-800'
};

const TaskDetailPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const [task, setTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [attachments, setAttachments] = useState<FileAttachmentProps[]>([]);
  const [isLoadingAttachments, setIsLoadingAttachments] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: '',
    priority: '',
    estimated_hours: 0,
    actual_hours: 0,
    progress: 0,
    due_date: '',
    tags: ''
  });

  useEffect(() => {
    if (!id) return;
    
    // Simulate API call to fetch task details
    const fetchTask = async () => {
      setIsLoading(true);
      try {
        // In a real app, fetch task from API
        // const response = await fetch(`/api/tasks/${id}`);
        // const data = await response.json();
        
        // For demo purposes, using mock data
        setTimeout(() => {
          setTask(mockTask);
          setFormData({
            title: mockTask.name,
            description: mockTask.description || '',
            status: mockTask.status,
            priority: mockTask.priority,
            estimated_hours: mockTask.estimated_hours || 0,
            actual_hours: mockTask.actual_hours || 0,
            progress: mockTask.progress || 0,
            due_date: mockTask.dueDate || '',
            tags: mockTask.tags || ''
          });
          setIsLoading(false);
        }, 1000);
      } catch (error) {
        console.error('Error fetching task:', error);
        setIsLoading(false);
      }
    };

    fetchTask();
    
    // Fetch task attachments
    const fetchAttachments = async () => {
      if (typeof id !== 'string') return;
      
      setIsLoadingAttachments(true);
      try {
        // In a real app, fetch attachments from API
        // const data = await getTaskAttachments(parseInt(id));
        // setAttachments(data);
        
        // For demo purposes
        setAttachments([
          {
            id: 1,
            filename: 'abc123.pdf',
            original_filename: 'requirements.pdf',
            file_size: 1024 * 1024 * 2.5, // 2.5 MB
            content_type: 'application/pdf',
            description: 'Project requirements document',
            task_id: parseInt(id),
            uploaded_by: 1,
            created_at: new Date().toISOString(),
          },
          {
            id: 2,
            filename: 'def456.png',
            original_filename: 'mockup.png',
            file_size: 1024 * 500, // 500 KB
            content_type: 'image/png',
            description: 'UI mockup',
            task_id: parseInt(id),
            uploaded_by: 2,
            created_at: new Date().toISOString(),
          }
        ]);
      } catch (error) {
        console.error('Error fetching attachments:', error);
      } finally {
        setIsLoadingAttachments(false);
      }
    };
    
    fetchAttachments();
  }, [id]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleSelectChange = (name: string, value: string) => {
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const numValue = parseFloat(value);
    setFormData({
      ...formData,
      [name]: isNaN(numValue) ? 0 : numValue
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Simulate API call to update task
    setIsLoading(true);
    try {
      // In a real app, update task via API
      // const response = await fetch(`/api/tasks/${id}`, {
      //   method: 'PUT',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(formData)
      // });
      
      // For demo purposes
      setTimeout(() => {
        setTask({
          ...task,
          ...formData
        });
        setIsEditing(false);
        setIsLoading(false);
      }, 500);
    } catch (error) {
      console.error('Error updating task:', error);
      setIsLoading(false);
    }
  };

  const handleDeleteTask = async () => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    
    setIsLoading(true);
    try {
      // In a real app, delete task via API
      // await fetch(`/api/tasks/${id}`, {
      //   method: 'DELETE'
      // });
      
      // For demo purposes
      setTimeout(() => {
        router.push('/tasks');
      }, 500);
    } catch (error) {
      console.error('Error deleting task:', error);
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMMM d, yyyy');
    } catch {
      return 'No date set';
    }
  };

  const getStatusColor = (status: string) => {
    const statusColors = {
      todo: 'bg-gray-200 text-gray-800',
      in_progress: 'bg-blue-200 text-blue-800',
      review: 'bg-purple-200 text-purple-800',
      done: 'bg-green-200 text-green-800',
      cancelled: 'bg-red-200 text-red-800'
    };
    return statusColors[status as keyof typeof statusColors] || 'bg-gray-200 text-gray-800';
  };

  const getPriorityColor = (priority: string) => {
    const priorityColors = {
      low: 'bg-green-200 text-green-800',
      medium: 'bg-yellow-200 text-yellow-800',
      high: 'bg-orange-200 text-orange-800',
      urgent: 'bg-red-200 text-red-800'
    };
    return priorityColors[priority as keyof typeof priorityColors] || 'bg-gray-200 text-gray-800';
  };

  const handleAddComment = () => {
    if (!newComment.trim()) return;
    
    // In a real app, send the comment to the API
    console.log('Adding comment:', newComment);
    
    // Mock adding a comment
    const updatedTask = {
      ...task,
      comments: [
        ...task.comments,
        {
          id: `new-${Date.now()}`,
          user: { id: '1', name: 'Current User', avatar: '/avatars/user.png' },
          content: newComment,
          createdAt: new Date().toISOString()
        }
      ]
    };
    
    setTask(updatedTask);
    setNewComment('');
  };

  // Handle file upload
  const handleFileUpload = async (file: File, description?: string) => {
    if (typeof id !== 'string') return;
    
    try {
      // In a real app, upload file to API
      // const data = await uploadTaskAttachment(parseInt(id), file, description);
      // setAttachments([...attachments, data]);
      
      // For demo purposes
      const newAttachment: FileAttachmentProps = {
        id: Math.floor(Math.random() * 1000),
        filename: `file_${Date.now()}.${file.name.split('.').pop()}`,
        original_filename: file.name,
        file_size: file.size,
        content_type: file.type,
        description,
        task_id: parseInt(id),
        uploaded_by: 1, // Current user ID
        created_at: new Date().toISOString(),
      };
      
      setAttachments([...attachments, newAttachment]);
    } catch (error) {
      console.error('Error uploading file:', error);
      throw error;
    }
  };
  
  // Handle file deletion
  const handleFileDelete = async (fileId: number) => {
    try {
      // In a real app, delete file via API
      // await deleteFileAttachment(fileId);
      
      // Remove from state
      setAttachments(attachments.filter(a => a.id !== fileId));
    } catch (error) {
      console.error('Error deleting file:', error);
      throw error;
    }
  };

  if (isLoading && !task) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8">
          <div className="mb-4">
            <Skeleton className="h-6 w-32" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <Skeleton className="h-8 w-full mb-2" />
                </CardHeader>
                <CardContent className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-6 w-full" />
                  ))}
                </CardContent>
              </Card>
            </div>
            <div>
              <Card>
                <CardHeader>
                  <Skeleton className="h-6 w-24" />
                </CardHeader>
                <CardContent className="space-y-4">
                  {[...Array(6)].map((_, i) => (
                    <Skeleton key={i} className="h-6 w-full" />
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto py-6">
        <Button
          variant="ghost"
          className="mb-4"
          onClick={() => router.back()}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Tasks
        </Button>

        {isLoading ? (
          <TaskDetailSkeleton />
        ) : task ? (
          <>
            {isEditing ? (
              <div className="grid gap-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      name="description"
                      value={formData.description}
                      onChange={handleInputChange}
                      rows={5}
                    />
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="status">Status</Label>
                      <Select 
                        value={formData.status} 
                        onValueChange={(value) => handleSelectChange('status', value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="todo">To Do</SelectItem>
                          <SelectItem value="in_progress">In Progress</SelectItem>
                          <SelectItem value="review">Review</SelectItem>
                          <SelectItem value="done">Done</SelectItem>
                          <SelectItem value="cancelled">Cancelled</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label htmlFor="priority">Priority</Label>
                      <Select 
                        value={formData.priority} 
                        onValueChange={(value) => handleSelectChange('priority', value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select priority" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="low">Low</SelectItem>
                          <SelectItem value="medium">Medium</SelectItem>
                          <SelectItem value="high">High</SelectItem>
                          <SelectItem value="urgent">Urgent</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label htmlFor="estimated_hours">Estimated Hours</Label>
                      <Input
                        id="estimated_hours"
                        name="estimated_hours"
                        type="number"
                        value={formData.estimated_hours}
                        onChange={handleNumberChange}
                        min={0}
                        step={0.5}
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="actual_hours">Actual Hours</Label>
                      <Input
                        id="actual_hours"
                        name="actual_hours"
                        type="number"
                        value={formData.actual_hours}
                        onChange={handleNumberChange}
                        min={0}
                        step={0.5}
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="progress">Progress (%)</Label>
                      <Input
                        id="progress"
                        name="progress"
                        type="number"
                        value={formData.progress}
                        onChange={handleNumberChange}
                        min={0}
                        max={100}
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="due_date">Due Date</Label>
                      <Input
                        id="due_date"
                        name="due_date"
                        type="date"
                        value={formData.due_date}
                        onChange={handleInputChange}
                      />
                    </div>
                  </div>
                  
                  <div>
                    <Label htmlFor="tags">Tags</Label>
                    <Input
                      id="tags"
                      name="tags"
                      value={formData.tags}
                      onChange={handleInputChange}
                      placeholder="Separate tags with commas"
                    />
                  </div>
                  
                  <div className="flex justify-end space-x-2">
                    <Button variant="outline" type="button" onClick={() => setIsEditing(false)}>
                      Cancel
                    </Button>
                    <Button type="submit">Save Changes</Button>
                  </div>
                </form>
              </div>
            ) : (
              <div className="grid gap-6">
                <div className="lg:col-span-2">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <CardTitle>{task.name}</CardTitle>
                      <div className="flex space-x-2">
                        {!isEditing && (
                          <>
                            <Button variant="outline" onClick={() => setIsEditing(true)}>Edit</Button>
                            <Button variant="destructive" onClick={handleDeleteTask}>Delete</Button>
                          </>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div>
                        <h3 className="font-medium mb-2">Description</h3>
                        <p className="text-gray-700">{task.description || 'No description provided'}</p>
                      </div>
                      
                      <div>
                        <h3 className="font-medium mb-2">Progress</h3>
                        <Progress value={task.progress || 0} className="h-2" />
                        <span className="text-sm text-gray-500 mt-1 inline-block">{task.progress}% complete</span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h3 className="font-medium mb-2">Status</h3>
                          <span className={`inline-block px-2 py-1 rounded text-sm ${getStatusColor(task.status)}`}>
                            {task.status.replace('_', ' ').toUpperCase()}
                          </span>
                        </div>
                        
                        <div>
                          <h3 className="font-medium mb-2">Priority</h3>
                          <span className={`inline-block px-2 py-1 rounded text-sm ${getPriorityColor(task.priority)}`}>
                            {task.priority.toUpperCase()}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
                
                <div>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Details</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center">
                        <CalendarIcon className="h-5 w-5 mr-2 text-gray-500" />
                        <div>
                          <p className="text-sm font-medium">Due Date</p>
                          <p className="text-sm text-gray-500">
                            {task.dueDate ? formatDate(task.dueDate) : 'No due date'}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center">
                        <Clock className="h-5 w-5 mr-2 text-gray-500" />
                        <div>
                          <p className="text-sm font-medium">Time Tracking</p>
                          <p className="text-sm text-gray-500">
                            {task.actual_hours || 0} / {task.estimated_hours || 0} hours
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center">
                        <Users className="h-5 w-5 mr-2 text-gray-500" />
                        <div>
                          <p className="text-sm font-medium">Assignees</p>
                          <p className="text-sm text-gray-500">
                            {task.assignees.map(assignee => assignee.name).join(', ')}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-start">
                        <Tag className="h-5 w-5 mr-2 text-gray-500 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">Tags</p>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {task.tags && task.tags.split(',').map((tag, index) => (
                              <span 
                                key={index} 
                                className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded"
                              >
                                {tag.trim()}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
                
                {/* File Attachments */}
                <FileAttachmentList
                  taskId={typeof id === 'string' ? parseInt(id) : 0}
                  attachments={attachments}
                  onUpload={handleFileUpload}
                  onDelete={handleFileDelete}
                  isLoading={isLoadingAttachments}
                />
                
                {/* Comments */}
                <Card className="p-6">
                  <div className="flex items-center mb-4">
                    <MessageSquare className="mr-2 h-5 w-5" />
                    <h2 className="text-xl font-semibold">Comments</h2>
                  </div>
                  
                  <div className="space-y-4 mb-6">
                    {task.comments.map(comment => (
                      <div key={comment.id} className="flex gap-3">
                        <Avatar className="h-10 w-10">
                          <div className="bg-gray-300 h-full w-full rounded-full" />
                        </Avatar>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{comment.user.name}</p>
                            <p className="text-xs text-gray-500">
                              {formatDate(comment.createdAt)}
                            </p>
                          </div>
                          <p className="mt-1">{comment.content}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <div className="flex flex-col gap-3">
                    <Textarea
                      placeholder="Add a comment..."
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      className="min-h-[100px]"
                    />
                    <Button onClick={handleAddComment} className="self-end">
                      Add Comment
                    </Button>
                  </div>
                </Card>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12">
            <p>Task not found</p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default TaskDetailPage; 