"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Calendar, Star, Clock, Edit, Save, X } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { toast } from "react-hot-toast";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { use } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Project {
  id: number;
  name: string;
  description: string;
  status: 'on_track' | 'at_risk' | 'off_track' | 'on_hold' | 'done';
  created_at: string;
  start_date: string;
  end_date: string;
  customer: string;
  tags: string[];
  allocated_hours: string;
  project_manager: {
    id: number;
    name: string;
    profile_image_url?: string;
  };
}

interface EditedProject {
  name?: string;
  description?: string;
  status?: string;
  customer?: string;
  start_date?: string;
  end_date?: string;
  allocated_hours?: string;
  project_manager_id?: number;
  tags?: string[];
}

const statusConfig = {
  on_track: { label: 'On Track', color: 'bg-green-500', description: 'Project is progressing as planned' },
  at_risk: { label: 'At Risk', color: 'bg-yellow-500', description: 'Project might face some issues' },
  off_track: { label: 'Off Track', color: 'bg-red-500', description: 'Project is behind schedule' },
  on_hold: { label: 'On Hold', color: 'bg-gray-500', description: 'Project is temporarily paused' },
  done: { label: 'Done', color: 'bg-blue-500', description: 'Project is completed' }
};

const ProjectView = ({ params }: { params: Promise<{ id: string }> }) => {
  const resolvedParams = use(params);
  const [project, setProject] = useState<Project | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedProject, setEditedProject] = useState<EditedProject>({});
  const [isLoading, setIsLoading] = useState(true);
  const [projectManagers, setProjectManagers] = useState<Array<{ id: number; name: string; profile_image_url?: string }>>([]);
  const { token } = useAuthStore();

  // Fetch project managers
  useEffect(() => {
    const fetchProjectManagers = async () => {
      if (!token) return;
      try {
        const response = await fetch(`${API_BASE_URL}/users/project-managers`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        if (!response.ok) throw new Error('Failed to fetch project managers');
        const data = await response.json();
        setProjectManagers(data);
      } catch (error) {
        console.error('Error fetching project managers:', error);
        toast.error('Failed to load project managers');
      }
    };
    fetchProjectManagers();
  }, [token]);

  useEffect(() => {
    const fetchProjectData = async () => {
      if (!token || !resolvedParams?.id) return;
      
      try {
        setIsLoading(true);
        const response = await fetch(`${API_BASE_URL}/projects/${resolvedParams.id}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch project');
        }

        const data = await response.json();
        setProject(data);
        setEditedProject({
          name: data.name || '',
          description: data.description || '',
          status: data.status || 'on_track',
          customer: data.customer || '',
          start_date: data.start_date || '',
          end_date: data.end_date || '',
          allocated_hours: data.allocated_hours || '',
          project_manager_id: data.project_manager?.id,
          tags: data.tags || []
        });
      } catch (error) {
        console.error('Error fetching project:', error);
        toast.error('Failed to load project');
      } finally {
        setIsLoading(false);
      }
    };

    fetchProjectData();
  }, [resolvedParams?.id, token]);

  const handleSaveChanges = async () => {
    try {
      if (!token) {
        throw new Error("No authentication token found");
      }

      const response = await fetch(`${API_BASE_URL}/projects/${resolvedParams?.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editedProject)
      });

      if (!response.ok) {
        throw new Error('Failed to update project');
      }

      const updatedProject = await response.json();
      setProject(updatedProject);
      setIsEditing(false);
      toast.success('Project updated successfully');
    } catch (error) {
      console.error('Error updating project:', error);
      toast.error('Failed to update project');
    }
  };

  if (isLoading) return <div className="p-4">Loading project details...</div>;
  if (!project) return <div className="p-4">Project not found</div>;

  return (
    <div className="container mx-auto py-6 px-4">
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-400" />
            <h1 className="text-2xl font-bold">
              {isEditing ? (
                <Input
                  value={editedProject.name || ''}
                  onChange={(e) => setEditedProject(prev => ({ ...prev, name: e.target.value }))}
                  className="max-w-md"
                  placeholder="Project name"
                />
              ) : (
                project.name
              )}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            {/* Status Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Status:</span>
              {isEditing ? (
                <Select
                  value={editedProject.status}
                  onValueChange={(value) => setEditedProject(prev => ({ ...prev, status: value }))}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(statusConfig).map(([key, { label, description }]) => (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${statusConfig[key as keyof typeof statusConfig].color}`} />
                          <div>
                            <div className="font-medium">{label}</div>
                            <div className="text-xs text-gray-500">{description}</div>
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${statusConfig[project.status]?.color}`} />
                  <span className="text-sm font-medium">{statusConfig[project.status]?.label}</span>
                </div>
              )}
            </div>
            {/* Edit/Save Buttons */}
            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSaveChanges}>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </Button>
                </>
              ) : (
                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Project
                </Button>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="text-sm text-gray-500">Name of the Tasks</label>
            {isEditing ? (
              <Input
                value={editedProject.name || ''}
                onChange={(e) => setEditedProject(prev => ({ ...prev, name: e.target.value }))}
                className="mt-1"
                placeholder="Enter task name"
              />
            ) : (
              <div className="mt-1 font-medium">{project.name}</div>
            )}
          </div>

          <div>
            <label className="text-sm text-gray-500">Project Manager</label>
            {isEditing ? (
              <Select
                value={String(editedProject.project_manager_id)}
                onValueChange={(value) => setEditedProject(prev => ({ ...prev, project_manager_id: Number(value) }))}
              >
                <SelectTrigger className="w-full mt-1">
                  <SelectValue placeholder="Select project manager" />
                </SelectTrigger>
                <SelectContent>
                  {projectManagers.map((manager) => (
                    <SelectItem key={manager.id} value={String(manager.id)}>
                      <div className="flex items-center gap-2">
                        <Avatar className="h-6 w-6">
                          <AvatarImage src={manager.profile_image_url || '/default-avatar.svg'} />
                          <AvatarFallback>{manager.name[0]}</AvatarFallback>
                        </Avatar>
                        <span>{manager.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="flex items-center gap-2 mt-1">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={project.project_manager?.profile_image_url || '/default-avatar.svg'} />
                  <AvatarFallback>{project.project_manager?.name ? project.project_manager.name[0] : '?'}</AvatarFallback>
                </Avatar>
                <span className="font-medium">{project.project_manager?.name || 'No manager assigned'}</span>
              </div>
            )}
          </div>

          <div>
            <label className="text-sm text-gray-500">Customer</label>
            {isEditing ? (
              <Input
                value={editedProject.customer || ''}
                onChange={(e) => setEditedProject(prev => ({ ...prev, customer: e.target.value }))}
                className="mt-1"
                placeholder="Enter customer name"
              />
            ) : (
              <div className="mt-1 font-medium">{project.customer || 'No customer specified'}</div>
            )}
          </div>

          <div>
            <label className="text-sm text-gray-500">Planned Date</label>
            <div className="grid grid-cols-2 gap-4 mt-1">
              {isEditing ? (
                <>
                  <Input
                    type="date"
                    value={editedProject.start_date || ''}
                    onChange={(e) => setEditedProject(prev => ({ ...prev, start_date: e.target.value }))}
                  />
                  <Input
                    type="date"
                    value={editedProject.end_date || ''}
                    onChange={(e) => setEditedProject(prev => ({ ...prev, end_date: e.target.value }))}
                  />
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-500" />
                  <span>
                    {new Date(project.start_date).toLocaleDateString()} — {new Date(project.end_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="text-sm text-gray-500">Tags</label>
            <div className="flex gap-2 mt-1">
              {(project.tags || []).map((tag, index) => (
                <span
                  key={index}
                  className={`px-2 py-1 text-xs rounded-full ${
                    tag.toLowerCase() === 'bug' ? 'bg-red-100 text-red-600' :
                    tag.toLowerCase() === 'experiment' ? 'bg-blue-100 text-blue-600' :
                    tag.toLowerCase() === 'internal' ? 'bg-orange-100 text-orange-600' :
                    tag.toLowerCase() === 'usability' ? 'bg-purple-100 text-purple-600' :
                    'bg-gray-100 text-gray-600'
                  }`}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm text-gray-500">Allocated Hours</label>
            {isEditing ? (
              <Input
                type="text"
                value={editedProject.allocated_hours || ''}
                onChange={(e) => setEditedProject(prev => ({ ...prev, allocated_hours: e.target.value }))}
                className="mt-1"
                placeholder="Enter allocated hours"
              />
            ) : (
              <div className="flex items-center gap-2 mt-1">
                <Clock className="h-4 w-4 text-gray-500" />
                <span>{project.allocated_hours || '00:00'}</span>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6">
          <label className="text-sm text-gray-500">Description</label>
          {isEditing ? (
            <Textarea
              value={editedProject.description || ''}
              onChange={(e) => setEditedProject(prev => ({ ...prev, description: e.target.value }))}
              className="mt-1"
              placeholder="Enter project description"
              rows={4}
            />
          ) : (
            <div className="mt-1 prose max-w-none">
              {project.description || "No description provided."}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default ProjectView; 