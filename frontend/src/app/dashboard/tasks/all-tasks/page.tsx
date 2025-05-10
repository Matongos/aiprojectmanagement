"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";
import AuthWrapper from "@/components/AuthWrapper";
import { API_BASE_URL } from "@/lib/constants";
import { Card } from "@/components/ui/card";
import axios from 'axios';
import ApiDebugger from './debug-api';

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
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/json', JSON.stringify(task));
    e.dataTransfer.setData('text/plain', task.id.toString());
    
    // Set task in state and ref for access during drag operations
    setDraggedTask(task);
    dragTaskRef.current = task;
    
    // Create a drag image
    const dragImage = document.createElement('div');
    dragImage.classList.add('hidden-drag-image');
    dragImage.innerHTML = `<div class="p-3 bg-white shadow-lg rounded-md">${task.name}</div>`;
    document.body.appendChild(dragImage);
    
    // Add the drag image
    e.dataTransfer.setDragImage(dragImage, 20, 20);
    
    // Remove the element after drag starts
    setTimeout(() => {
      document.body.removeChild(dragImage);
    }, 0);

    // Show visual feedback
    const taskElement = e.currentTarget as HTMLElement;
    taskElement.classList.add('task-dragging');
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
    
    // Reset the active drop target
    setActiveDropTarget(null);
    
    // Get the task ID from the drag data
    const taskId = parseInt(e.dataTransfer.getData('text/plain'));
    
    // Check if we have a valid task to move
    if (!dragTaskRef.current || dragTaskRef.current.id !== taskId) {
      return;
    }
    
    // Check if the task is being moved to a different stage
    if (dragTaskRef.current.stage_id === targetStageId) {
      return;
    }
    
    // Find source and target stages
    const sourceStage = stages.find(s => s.id === dragTaskRef.current!.stage_id);
    const targetStage = stages.find(s => s.id === targetStageId);
    
    if (!sourceStage || !targetStage) {
      return;
    }
    
    // Prepare updated stages
    const updatedStages = [...stages];
    
    // Find source stage index and task index
    const sourceStageIndex = updatedStages.findIndex(s => s.id === sourceStage.id);
    const taskIndex = updatedStages[sourceStageIndex].tasks.findIndex(t => t.id === taskId);
    
    if (taskIndex === -1) {
      return;
    }
    
    // Find target stage index
    const targetStageIndex = updatedStages.findIndex(s => s.id === targetStage.id);
    
    // Remove task from source stage
    const [movedTask] = updatedStages[sourceStageIndex].tasks.splice(taskIndex, 1);
    
    // Update task stage_id
    movedTask.stage_id = targetStageId;
    
    // Add task to target stage
    updatedStages[targetStageIndex].tasks.push(movedTask);
    
    // Update state
    setStages(updatedStages);
    
    // Reset dragged task
    setDraggedTask(null);
    dragTaskRef.current = null;
    
    // Send update to backend
    try {
      const token = useAuthStore.getState().token;
      console.log('Sending task update:', {
        task_id: taskId,
        new_stage_id: targetStageId
      });
      
      await axios.put(`${API_BASE_URL}/tasks/${taskId}/move-stage`, {
        new_stage_id: targetStageId
      }, {
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
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Task Board</h1>
        <button 
          onClick={() => setShowDebugger(!showDebugger)}
          className="text-sm text-blue-500 hover:underline"
        >
          {showDebugger ? 'Hide Debugger' : 'Debug API'}
        </button>
      </div>
      
      {showDebugger && <div className="mb-6"><ApiDebugger /></div>}
      
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
          transition: all 0.2s ease;
        }
        
        .task-card {
          margin-bottom: 0.5rem;
          cursor: move !important;
          cursor: grab !important;
          user-select: none;
          transition: transform 0.2s, box-shadow 0.2s;
          -webkit-user-drag: element;
          touch-action: none;
        }
        
        .task-card:active {
          cursor: grabbing !important;
        }
        
        .task-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .task-dragging {
          opacity: 0.5;
          cursor: grabbing !important;
        }
        
        /* Prevent text selection during drag operations */
        * {
          -webkit-touch-callout: none;
          -webkit-user-select: none;
          -khtml-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
          user-select: none;
        }
        
        /* Restore text selection for specific elements */
        input, textarea, [contenteditable=true] {
          -webkit-user-select: text;
          -khtml-user-select: text;
          -moz-user-select: text;
          -ms-user-select: text;
          user-select: text;
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
              data-stage-id={stage.id}
            >
              {stage.tasks.map((task) => (
                <Card 
                  key={task.id}
                  className={`task-card p-3 shadow-sm ${draggedTask?.id === task.id ? 'task-dragging' : ''}`}
                  draggable={true}
                  onDragStart={(e) => handleDragStart(e, task)}
                  onDragEnd={handleDragEnd}
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
                </Card>
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