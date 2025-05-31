export interface Stage {
  id: number;
  name: string;
  description: string | null;
  order: number;
  project_id: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  is_default: boolean;
  color: string;
  icon: string | null;
} 