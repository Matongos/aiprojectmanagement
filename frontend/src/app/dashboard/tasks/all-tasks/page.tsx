"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";
import { Card } from "@/components/ui/card";
import axios from 'axios';
import ApiDebugger from './debug-api';
import { Button } from "@/components/ui/button";

interface Task {
  id: number;
  name: string;
  description: string;
  state: string;
  priority: string;
  stage_id: number;
  project_id: number;
  assigned_to: number;
  created_by: number;
  project: {
    name: string;
  };
}

interface Stage {
  id: number;
  name: string;
  sequence: number;
  tasks: Task[];
}

function TaskBoardComponent() {
  const [stages, setStages] = useState<Stage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDebugger, setShowDebugger] = useState(false);
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);
  const [activeDropTarget, setActiveDropTarget] = useState<number | null>(null);
  const dragTaskRef = useRef<Task | null>(null);

  useEffect(() => {
    // Fetch stages and tasks
    fetchData();
  }, []);

  useEffect(() => {
    // Add event listener for dragover on the document
    const handleDocumentDragOver = (e: DragEvent) => {
      e.preventDefault();
      return false;
    };
    
    document.addEventListener('dragover', handleDocumentDragOver, false);
    
    return () => {
      document.removeEventListener('dragover', handleDocumentDragOver, false);
    };
  }, []);

  const fetchData = async () => {
    try {
      setError(null);
      const token = useAuthStore.getState().token;
      
      toast.loading('Loading task board...', { id: 'loading-board' });
      
      const [stagesRes, tasksRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/task_stages/`, { 
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE_URL}/tasks/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      
      // If no stages found, set error
      if (!stagesRes.data || stagesRes.data.length === 0) {
        setError('No stages found. Please create stages for your project first.');
        toast.error('No stages found', { id: 'loading-board' });
        setLoading(false);
        return;
      }
      
      // Organize tasks by stage
      const organizedStages = stagesRes.data.map((stage: Stage) => ({
        ...stage,
        tasks: tasksRes.data.filter((task: Task) => task.stage_id === stage.id)
      }));
      
      setStages(organizedStages);
      toast.success('Task board loaded successfully', { id: 'loading-board' });
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('Failed to load task board. See console for details or use the debugger.');
      toast.error('Failed to load task board', { id: 'loading-board' });
      setLoading(false);
    }
  };

  // Handle drag start
  const handleDragStart = (e: React.DragEvent, task: Task) => {
    e.stopPropagation();
    e.preventDefault();
    
    // Set draggable properties
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/json', JSON.stringify(task));
    e.dataTransfer.setData('text/plain', task.id.toString());
    
    // Set task in state and ref for access during drag operations
    setDraggedTask(task);
    dragTaskRef.current = task;
    
    // Create a drag image
    const taskCard = e.currentTarget as HTMLElement;
    const dragImage = taskCard.cloneNode(true) as HTMLElement;
    dragImage.classList.add('hidden-drag-image');
    dragImage.style.width = `${taskCard.offsetWidth}px`;
    document.body.appendChild(dragImage);
    
    // Add the drag image with offset
    e.dataTransfer.setDragImage(dragImage, 20, 20);
    
    // Remove the element after drag starts
    requestAnimationFrame(() => {
      document.body.removeChild(dragImage);
    });

    // Show visual feedback
    taskCard.classList.add('task-dragging');
    
    // Prevent text selection
    document.body.style.userSelect = 'none';
    document.body.style.webkitUserSelect = 'none';
    document.body.style.mozUserSelect = 'none';
    document.body.style.msUserSelect = 'none';
  };

  // Handle drag over
  const handleDragOver = (e: React.DragEvent, stageId: number) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'move';
    
    // Highlight the drop target
    setActiveDropTarget(stageId);
    return false;
  };

  // Handle drag leave
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    // Remove highlight
    setActiveDropTarget(null);
  };

  // Handle drop
  const handleDrop = async (e: React.DragEvent, targetStageId: number) => {
    e.preventDefault();
    
    // Get the task ID from the drag data
    const taskId = parseInt(e.dataTransfer.getData('text/plain'));
    if (!taskId || !draggedTask) return;
    
    // Don't do anything if dropping in the same stage
    if (draggedTask.stage_id === targetStageId) return;
    
    // Update local state first
    setStages(stages.map(stage => {
      if (stage.id === draggedTask.stage_id) {
        // Remove task from source stage
        return {
          ...stage,
          tasks: stage.tasks.filter(t => t.id !== taskId)
        };
      }
      if (stage.id === targetStageId) {
        // Add task to target stage
        return {
          ...stage,
          tasks: [...stage.tasks, { ...draggedTask, stage_id: targetStageId }]
        };
      }
      return stage;
    }));
    
    // Reset drag state
    setDraggedTask(null);
    setActiveDropTarget(null);
    
    // Update backend
    try {
      const token = useAuthStore.getState().token;
      await axios.post(`${API_BASE_URL}/stages/${targetStageId}/tasks/${taskId}`, {}, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      toast.success('Task moved successfully');
    } catch (error) {
      console.error('Error updating task stage:', error);
      toast.error('Failed to update task stage');
      // Revert the change in UI if backend update fails
      fetchData();
    }
  };

  // Handle drag end
  const handleDragEnd = () => {
    // Reset state
    setDraggedTask(null);
    setActiveDropTarget(null);
    dragTaskRef.current = null;
    
    // Remove any lingering drag classes
    const taskElements = document.querySelectorAll('.task-card');
    taskElements.forEach(el => {
      el.classList.remove('task-dragging');
    });
    
    // Remove any remaining hidden drag images
    const dragImages = document.querySelectorAll('.hidden-drag-image');
    dragImages.forEach(el => {
      if (document.body.contains(el)) {
        document.body.removeChild(el);
      }
    });
    
    // Restore text selection
    document.body.style.userSelect = '';
    document.body.style.webkitUserSelect = '';
    document.body.style.mozUserSelect = '';
    document.body.style.msUserSelect = '';
  };

  // Get task priority color
  const getPriorityColor = (priority: string) => {
    switch(priority) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <h2 className="text-xl font-semibold text-red-800 mb-4">Error Loading Task Board</h2>
        <p className="mb-4">{error}</p>
        <div className="flex space-x-4">
          <button 
            onClick={() => setShowDebugger(!showDebugger)}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            {showDebugger ? 'Hide Debugger' : 'Show API Debugger'}
          </button>
        </div>
        
        {showDebugger && <div className="mt-6"><ApiDebugger /></div>}
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold">Task Board</h1>
        <Button
          variant="outline"
          onClick={() => setShowDebugger(!showDebugger)}
        >
          {showDebugger ? 'Hide Debugger' : 'Show Debugger'}
        </Button>
      </div>

      {showDebugger && <ApiDebugger />}
      
      <style jsx global>{`
        .hidden-drag-image {
          position: absolute;
          top: -9999px;
          left: -9999px;
        }
        
        .task-board-container {
          display: flex;
          flex-direction: row;
          gap: 1rem;
          min-height: calc(100vh - 200px);
          width: 100%;
          overflow-x: auto;
          user-select: none;
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
        }
        
        .stage-column {
          min-width: 300px;
          flex: 1;
          display: flex;
          flex-direction: column;
          border-radius: 0.5rem;
          background-color: #f9fafb;
          max-height: calc(100vh - 200px);
        }
        
        .stage-header {
          background-color: #f3f4f6;
          padding: 0.75rem 1rem;
          border-top-left-radius: 0.5rem;
          border-top-right-radius: 0.5rem;
          border-bottom: 1px solid #e5e7eb;
          font-weight: 600;
          user-select: none;
        }
        
        .stage-content {
          flex: 1;
          padding: 0.5rem;
          overflow-y: auto;
          min-height: 100%;
        }
        
        .stage-active {
          background-color: #e0f2fe;
          border: 2px dashed #3b82f6;
        }
        
        .task-card {
          background: white;
          padding: 1rem;
          margin-bottom: 0.5rem;
          border-radius: 0.375rem;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
          cursor: grab;
          user-select: none;
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
          touch-action: none;
        }
        
        .task-card:hover {
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .task-card:active {
          cursor: grabbing;
        }
        
        .task-dragging {
          opacity: 0.5;
          cursor: grabbing;
          box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
          transform: scale(1.02);
          transition: all 0.2s ease;
        }
      `}</style>
      
      <div className="task-board-container">
        {stages.map((stage) => (
          <div 
            key={stage.id} 
            className="stage-column"
          >
            <div className="stage-header">
              <h2 className="font-semibold">{stage.name}</h2>
              <span className="text-sm text-gray-500">{stage.tasks.length} tasks</span>
            </div>
            
            <div 
              className={`stage-content ${activeDropTarget === stage.id ? 'stage-active' : ''}`}
              onDragOver={(e) => handleDragOver(e, stage.id)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, stage.id)}
            >
              {stage.tasks.map((task) => (
                <div 
                  key={task.id}
                  className={`task-card ${draggedTask?.id === task.id ? 'task-dragging' : ''}`}
                  draggable="true"
                  onDragStart={(e) => handleDragStart(e, task)}
                  onDragEnd={handleDragEnd}
                  onMouseDown={(e) => {
                    const target = e.currentTarget;
                    target.style.cursor = 'grabbing';
                  }}
                  onMouseUp={(e) => {
                    const target = e.currentTarget;
                    target.style.cursor = 'grab';
                  }}
                >
                  <h3 className="font-medium">{task.name}</h3>
                  <p className="text-sm text-gray-600 truncate">
                    {task.description}
                  </p>
                  <div className="flex items-center justify-between mt-2">
                    <span className={`px-2 py-0.5 rounded text-xs ${getPriorityColor(task.priority)}`}>
                      {task.priority}
                    </span>
                    {task.project && (
                      <span className="text-xs text-gray-500">
                        {task.project.name}
                      </span>
                    )}
                  </div>
                </div>
              ))}
              
              {stage.tasks.length === 0 && (
                <div className="flex items-center justify-center h-32 border-2 border-dashed border-gray-200 rounded-lg my-2">
                  <p className="text-sm text-gray-500">Drop tasks here</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {stages.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
          <p>No stages found or API connection issue. Check with debugger above.</p>
        </div>
      )}
    </div>
  );
}

export default function TaskBoardPage() {
  return (
    <AuthWrapper>
      <TaskBoardComponent />
    </AuthWrapper>
  );
} 