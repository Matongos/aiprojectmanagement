"use client";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MessageSquare, Star, MoreHorizontal, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import React from "react";
import { API_BASE_URL } from "@/lib/constants";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Stage {
  id: string;
  name: string;
  order: number;
  duration?: string;
}

interface Task {
  id: string;
  name: string;
  description: string;
  stage_id: number;
  // ... other task properties
}

interface TaskDetailsProps {
  params: Promise<{
    id: string;
    taskId: string;
  }>;
}

export default function TaskDetails({ params }: TaskDetailsProps) {
  // Unwrap params using React.use()
  const { id, taskId } = React.use(params);
  const [currentStage, setCurrentStage] = useState<string>("");
  const [description, setDescription] = useState("");
  const { token } = useAuthStore();
  const [showAllStages, setShowAllStages] = useState(false);

  // Fetch task details including current stage
  const { data: taskDetails, isLoading: isLoadingTask, error: taskError } = useQuery<Task>({
    queryKey: ["task-details", taskId],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 401) {
          toast.error("Please log in to view this content");
          throw new Error("Unauthorized");
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch task details: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("Task Details Response:", data); // Debug log
        return data;
      } catch (error) {
        console.error("Error fetching task:", error);
        toast.error("Failed to load task details");
        throw error;
      }
    },
    enabled: !!token && !!taskId,
  });

  // Fetch project stages
  const { data: stages = [], isLoading: isLoadingStages, error: stagesError } = useQuery<Stage[]>({
    queryKey: ["project-stages", id],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/projects/${id}/stages`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (response.status === 401) {
          toast.error("Please log in to view this content");
          throw new Error("Unauthorized");
        }
        
        if (!response.ok) {
          throw new Error(`Failed to fetch project stages: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log("Stages Response:", data); // Debug log
        return data;
      } catch (error) {
        console.error("Error fetching stages:", error);
        toast.error("Failed to load project stages");
        throw error;
      }
    },
    enabled: !!token && !!id,
  });

  // Set current stage when task details are loaded
  useEffect(() => {
    if (taskDetails?.stage_id) {
      const stageId = taskDetails.stage_id.toString();
      console.log("Setting current stage to:", stageId); // Debug log
      setCurrentStage(stageId);
    }
  }, [taskDetails]);

  const actionButtons = (
    <div className="flex items-center gap-2 overflow-x-auto pb-2">
      <Button variant="outline" size="sm" className="whitespace-nowrap">Send message</Button>
      <Button variant="outline" size="sm" className="whitespace-nowrap">Log note</Button>
      <Button variant="outline" size="sm" className="whitespace-nowrap">Activities</Button>
      <Button variant="outline" size="sm" className="flex items-center gap-2 whitespace-nowrap">
        <MessageSquare className="w-4 h-4" />
        Comments
      </Button>
    </div>
  );

  // Handle stage change
  const handleStageChange = async (stageId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/stage`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stage_id: stageId }),
      });

      if (!response.ok) {
        throw new Error('Failed to update task stage');
      }

      setCurrentStage(stageId);
      toast.success('Task stage updated successfully');
    } catch (error) {
      console.error('Error updating task stage:', error);
      toast.error('Failed to update task stage');
    }
  };

  // Loading states
  if (isLoadingTask || isLoadingStages) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">Loading task details...</div>
      </div>
    );
  }

  // Error states
  if (!token) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Authentication Required</h2>
          <p className="text-gray-600">Please log in to view this content</p>
        </div>
      </div>
    );
  }

  if (stagesError || taskError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error</h2>
          <p className="text-gray-600">
            {stagesError ? "Failed to load project stages" : "Failed to load task details"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation with Stages and Actions */}
      <div className="container mx-auto px-6">
        <div className="flex justify-between items-center py-4">
          {/* Stage Navigation */}
          <div className="flex items-center gap-1.5">
            {stages.slice(0, showAllStages ? stages.length : 4).map((stage) => {
              const isCurrentStage = stage.id.toString() === currentStage;
              console.log(`Stage ${stage.id} comparison:`, { 
                stageId: stage.id, 
                currentStage, 
                isCurrentStage,
                taskStageId: taskDetails?.stage_id 
              }); // Debug log
              
              return (
                <Button
                  key={stage.id}
                  variant={isCurrentStage ? "default" : "outline"}
                  className={`transition-all duration-200 ${
                    isCurrentStage
                      ? "bg-purple-600 text-white hover:bg-purple-700 ring-2 ring-purple-300" 
                      : "hover:bg-purple-50"
                  } h-8 px-3 justify-center relative`}
                  onClick={() => handleStageChange(stage.id)}
                >
                  <div className="flex items-center">
                    <span className="text-sm">{stage.name}</span>
                    {isCurrentStage && stage.duration && (
                      <span className="text-xs opacity-80 ml-1">({stage.duration})</span>
                    )}
                    {isCurrentStage && (
                      <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-purple-600 rotate-45" />
                    )}
                  </div>
                </Button>
              );
            })}
            
            {!showAllStages && stages.length > 4 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 px-2"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[200px]">
                  {stages.slice(4).map((stage) => (
                    <DropdownMenuItem
                      key={stage.id}
                      onClick={() => handleStageChange(stage.id)}
                      className={stage.id.toString() === currentStage ? "bg-purple-50" : ""}
                    >
                      {stage.name}
                      {stage.id.toString() === currentStage && (
                        <ChevronRight className="ml-auto h-4 w-4" />
                      )}
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuItem
                    onClick={() => setShowAllStages(true)}
                    className="border-t mt-1 pt-1"
                  >
                    View All Stages
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {/* Action Buttons - Desktop */}
          <div className="hidden lg:block">
            {actionButtons}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Main Content Area */}
          <div className="flex-grow order-1 lg:order-1">
            <div className="bg-white rounded-lg shadow p-6">
              {/* Task Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Star className="text-gray-400" />
                  <h1 className="text-xl font-medium">
                    {isLoadingTask ? (
                      <div className="h-7 w-32 bg-gray-100 animate-pulse rounded"></div>
                    ) : (
                      taskDetails?.name || "Task Name"
                    )}
                  </h1>
                </div>
                <span className="text-sm bg-gray-100 px-3 py-1 rounded">In Progress</span>
              </div>

              {/* Task Details Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
                  <Input placeholder="Select project..." value="comments" readOnly />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Milestone</label>
                  <Input placeholder="e.g. Product Launch" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Assignees</label>
                  <Input placeholder="Select assignees..." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
                  <Input placeholder="Add tags..." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Customer</label>
                  <Input placeholder="Select customer..." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Allocated Time</label>
                  <div className="flex items-center gap-2">
                    <Input type="time" defaultValue="00:00" />
                    <span className="text-gray-500">(0%)</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Deadline</label>
                  <Input type="date" />
                </div>
              </div>

              {/* Tabs Navigation */}
              <div className="border-b mb-6 overflow-x-auto">
                <nav className="flex gap-4 min-w-max">
                  <Button variant="ghost" className="text-purple-700 border-b-2 border-purple-700 rounded-none px-0">
                    Description
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Timesheets
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Sub-tasks
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Extra Info
                  </Button>
                  <Button variant="ghost" className="text-gray-500 rounded-none px-0">
                    Checklist
                  </Button>
                </nav>
              </div>

              {/* Description Area */}
              <Textarea
                placeholder="Add details about this task..."
                className="min-h-[200px] w-full"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>

          {/* Action Buttons and Activity Feed for Mobile */}
          <div className="lg:w-80 order-2 lg:order-2">
            {/* Mobile Action Buttons */}
            <div className="lg:hidden mb-4">
              {actionButtons}
            </div>

            {/* Activity Feed */}
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium">Today</h3>
              </div>

              {/* Activity Items */}
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <Avatar className="w-8 h-8 bg-purple-600">
                    <span>M</span>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Marc Demo</span>
                      <span className="text-sm text-gray-500">1 hour ago</span>
                    </div>
                    <p>hi</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Avatar className="w-8 h-8 bg-purple-600">
                    <span>M</span>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Marc Demo</span>
                      <span className="text-red-500">@</span>
                      <span className="text-sm text-gray-500">1 hour ago</span>
                    </div>
                    <p>lets do it</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Avatar className="w-8 h-8 bg-purple-600">
                    <span>M</span>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Mitchell Admin</span>
                      <span className="text-sm text-gray-500">9 hours ago</span>
                    </div>
                    <p>Task Created</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}