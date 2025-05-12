export enum TaskState {
  IN_PROGRESS = "in_progress",
  CHANGES_REQUESTED = "changes_requested",
  APPROVED = "approved",
  CANCELED = "canceled",
  DONE = "done"
}

export interface Task {
  id: number;
  name: string;
  description?: string;
  state: TaskState;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date?: string;
  created_at: string;
  assignee?: {
    id: number;
    name: string;
    profile_image_url: string | null;
  };
}

export const statusConfig: Record<TaskState, { icon: string; color: string }> = {
  [TaskState.IN_PROGRESS]: { icon: "⏳", color: "bg-blue-100 text-blue-800" },
  [TaskState.CHANGES_REQUESTED]: { icon: "⚠️", color: "bg-orange-100 text-orange-800" },
  [TaskState.APPROVED]: { icon: "✅", color: "bg-green-100 text-green-800" },
  [TaskState.CANCELED]: { icon: "❌", color: "bg-red-100 text-red-800" },
  [TaskState.DONE]: { icon: "✔️", color: "bg-purple-100 text-purple-800" }
}; 