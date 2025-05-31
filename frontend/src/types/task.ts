export enum TaskState {
  IN_PROGRESS = "in_progress",
  CHANGES_REQUESTED = "changes_requested",
  APPROVED = "approved",
  CANCELED = "canceled",
  DONE = "done"
}

export enum TaskPriority {
  LOW = "low",
  NORMAL = "normal",
  HIGH = "high",
  URGENT = "urgent"
}

export interface Task {
  id: number;
  name: string;
  description?: string;
  priority: TaskPriority;
  state: TaskState;
  project_id: number;
  stage_id: number;
  parent_id?: number;
  assigned_to?: number;
  milestone_id?: number;
  company_id?: number;
  start_date?: string;
  end_date?: string;
  deadline?: string;
  planned_hours?: number;
  created_by: number;
  progress?: number;
  created_at: string;
  updated_at?: string;
  date_last_stage_update?: string;
  assignee?: {
    id: number;
    username: string;
    email: string;
    full_name: string;
    profile_image_url?: string;
  };
  milestone?: {
    id: number;
    name: string;
    description?: string;
    due_date?: string;
    is_completed: boolean;
    is_active: boolean;
    project_id: number;
    created_at: string;
    created_by?: number;
    updated_at?: string;
  };
  company?: {
    id: number;
    name: string;
  };
  depends_on_ids: number[];
  subtask_ids: number[];
  attachments?: FileAttachment[];
  tags?: Tag[];
  is_active: boolean;
}

export interface TaskCreate {
  name: string;
  description?: string;
  priority?: string;
  deadline?: string;
  planned_hours?: number;
  assigned_to?: number;
  project_id?: number;
  stage_id?: number;
  parent_id?: number;
  tag_ids?: number[];
}

export const statusConfig: Record<TaskState, { icon: string; color: string }> = {
  [TaskState.IN_PROGRESS]: { icon: "⏳", color: "bg-blue-100 text-blue-800" },
  [TaskState.CHANGES_REQUESTED]: { icon: "⚠️", color: "bg-orange-100 text-orange-800" },
  [TaskState.APPROVED]: { icon: "✅", color: "bg-green-100 text-green-800" },
  [TaskState.CANCELED]: { icon: "❌", color: "bg-red-100 text-red-800" },
  [TaskState.DONE]: { icon: "✔️", color: "bg-purple-100 text-purple-800" }
}; 