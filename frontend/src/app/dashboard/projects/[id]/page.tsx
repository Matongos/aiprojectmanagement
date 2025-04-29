"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "react-hot-toast";
import { fetchApi } from "@/lib/api-helper";
import { 
  Plus, 
  Star, 
  Calendar, 
  Clock, 
  Check,
  X,
  AlertCircle
} from "lucide-react";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { use } from "react";

interface TaskStatus {
  id: string;
  label: string;
  color: string;
  icon: 'check' | 'x' | 'alert';
}

const taskStatuses: TaskStatus[] = [
  { id: 'in_progress', label: 'In Progress', color: 'bg-gray-200', icon: 'check' },
  { id: 'changes_requested', label: 'Changes Requested', color: 'bg-yellow-200', icon: 'alert' },
  { id: 'approved', label: 'Approved', color: 'bg-green-200', icon: 'check' },
  { id: 'cancelled', label: 'Cancelled', color: 'bg-red-200', icon: 'x' },
  { id: 'done', label: 'Done', color: 'bg-green-500', icon: 'check' }
];

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: 'low' | 'medium' | 'high';
  due_date: string | null;
  created_at: string;
  assignee: {
    id: number;
    name: string;
    profile_image_url: string | null;
  } | null;
}

interface ProjectStage {
  id: number;
  name: string;
  tasks: Task[];
  progress: number;
  sequence_order: number;
}

interface Project {
  id: number;
  name: string;
  description: string;
  status: 'on_track' | 'at_risk' | 'off_track' | 'on_hold' | 'done' | 'default';
  stages: ProjectStage[];
  created_at: string;
  updated_at: string;
  creator_id: number;
  start_date: string | null;
  end_date: string | null;
}

export default function ProjectDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [collapsedStages, setCollapsedStages] = useState<Set<number>>(new Set());
  const router = useRouter();

  useEffect(() => {
    const fetchProject = async () => {
      if (!projectId) return;
      
      try {
        const data = await fetchApi<Project>(`/projects/${projectId}`);
        // Ensure stages is always an array
        setProject({
          ...data,
          stages: data.stages || []
        });
      } catch (error) {
        console.error("Error fetching project:", error);
        toast.error("Failed to load project");
        router.push("/dashboard/projects");
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [projectId, router]);

  const handleCreateStage = async () => {
    if (!projectId) return;

    try {
      await fetchApi(`/projects/${projectId}/stages`, {
        method: 'POST',
        body: JSON.stringify({
          name: 'New Stage',
          description: '',
          sequence_order: project?.stages.length || 0,
          project_id: parseInt(projectId)
        })
      });
      
      // Refresh project data
      const updatedProject = await fetchApi<Project>(`/projects/${projectId}`);
      setProject({
        ...updatedProject,
        stages: updatedProject.stages || []
      });
      toast.success('Stage created successfully');
    } catch (error) {
      console.error('Error creating stage:', error);
      toast.error('Failed to create stage');
    }
  };

  const handleCreateTask = () => {
    router.push(`/dashboard/tasks/create?projectId=${projectId}`);
  };

  const handleTaskStatusChange = async (taskId: number, newStatus: string) => {
    if (!projectId) return;

    try {
      await fetchApi(`/tasks/${taskId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus })
      });
      // Refresh project data
      const updatedProject = await fetchApi<Project>(`/projects/${projectId}`);
      setProject({
        ...updatedProject,
        stages: updatedProject.stages || []
      });
      toast.success('Task status updated');
    } catch (error) {
      console.error('Error updating task status:', error);
      toast.error('Failed to update task status');
    }
  };

  const getRelativeTime = (date: string) => {
    const days = Math.floor((new Date().getTime() - new Date(date).getTime()) / (1000 * 60 * 60 * 24));
    return `${days} days ago`;
  };

  const StatusIcon = ({ status }: { status: string }) => {
    const taskStatus = taskStatuses.find(s => s.id === status);
    if (!taskStatus) return null;

    return (
      <div className={`rounded-full p-0.5 ${taskStatus.color} cursor-pointer`}>
        {taskStatus.icon === 'check' && <Check className="h-2.5 w-2.5" />}
        {taskStatus.icon === 'x' && <X className="h-2.5 w-2.5" />}
        {taskStatus.icon === 'alert' && <AlertCircle className="h-2.5 w-2.5" />}
      </div>
    );
  };

  const toggleStageCollapse = (stageId: number) => {
    setCollapsedStages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stageId)) {
        newSet.delete(stageId);
      } else {
        newSet.add(stageId);
      }
      return newSet;
    });
  };

  if (loading) return <div className="p-4">Loading...</div>;
  if (!project) return <div className="p-4">Project not found</div>;

  return (
    <div className="container mx-auto p-4">
      {/* Project Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold">{project.name}</h1>
          <div className={`px-2 py-0.5 rounded text-xs ${
            project.status === 'off_track' ? 'bg-red-100 text-red-800' :
            project.status === 'on_track' ? 'bg-green-100 text-green-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {project.status.replace('_', ' ').charAt(0).toUpperCase() + project.status.slice(1)}
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={handleCreateTask}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            New Task
          </Button>
          <Button size="sm" variant="outline" onClick={handleCreateStage}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            New Stage
          </Button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {(project.stages || []).map((stage) => (
          <div key={stage.id} className="bg-gray-50 rounded-lg p-3">
            <div className="space-y-2">
              {/* Stage Header */}
              <div 
                className="flex items-center justify-between cursor-pointer"
                onClick={() => toggleStageCollapse(stage.id)}
              >
                <div className="flex items-center gap-2">
                  <div className="flex items-center">
                    <button className="p-1 hover:bg-gray-200 rounded">
                      {collapsedStages.has(stage.id) ? (
                        <Plus className="h-3.5 w-3.5" />
                      ) : (
                        <span className="h-3.5 w-3.5">-</span>
                      )}
                    </button>
                    <h3 className="text-sm font-medium ml-2">{stage.name}</h3>
                  </div>
                  <span className="text-xs text-gray-500 px-2 py-0.5 bg-gray-200 rounded-full">
                    {stage.tasks?.length || 0}
                  </span>
                </div>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </div>
              
              {/* Stage Progress Bar */}
              <div className="h-0.5 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-green-500 transition-all duration-300"
                  style={{ width: `${stage.progress}%` }}
                />
              </div>

              {/* Tasks */}
              {!collapsedStages.has(stage.id) && (
                <div className="space-y-2 transition-all duration-300">
                  {!stage.tasks?.length ? (
                    <div className="text-center py-6 text-gray-500 text-xs">
                      No tasks in this stage
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-[calc(100vh-300px)] overflow-y-auto">
                      {stage.tasks.map((task) => (
                        <Card 
                          key={task.id} 
                          className="p-2.5 cursor-pointer hover:shadow-md transition-shadow"
                          draggable
                          onDragStart={(e) => {
                            e.dataTransfer.setData('taskId', task.id.toString());
                            e.dataTransfer.setData('sourceStageId', stage.id.toString());
                          }}
                        >
                          <div className="flex items-start gap-2">
                            <div onClick={() => handleTaskStatusChange(task.id, task.status)}>
                              <StatusIcon status={task.status} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="text-sm font-medium mb-0.5 truncate">{task.title}</h4>
                              <p className="text-xs text-gray-600 line-clamp-2">{task.description}</p>
                              
                              <div className="mt-2 flex items-center justify-between text-xs">
                                <div className="flex items-center gap-1.5">
                                  {task.assignee && (
                                    <Avatar className="h-5 w-5">
                                      <AvatarImage 
                                        src={task.assignee.profile_image_url || '/default-avatar.png'} 
                                        alt={task.assignee.name} 
                                      />
                                      <AvatarFallback>{task.assignee.name[0]}</AvatarFallback>
                                    </Avatar>
                                  )}
                                  <div className="flex items-center text-gray-500">
                                    <Clock className="h-3 w-3 mr-0.5" />
                                    <span>{getRelativeTime(task.created_at)}</span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  {task.priority === 'high' && (
                                    <Star className="h-3 w-3 text-yellow-500 fill-current" />
                                  )}
                                  {task.due_date && (
                                    <div className="flex items-center text-gray-500">
                                      <Calendar className="h-3 w-3 mr-0.5" />
                                      <span>{new Date(task.due_date).toLocaleDateString()}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 