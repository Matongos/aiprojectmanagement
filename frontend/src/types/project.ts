export interface Project {
  id: number;
  name: string;
  description?: string | null;
  key?: string;
  privacy_level?: string;
  start_date?: string;
  end_date?: string | null;
  created_by?: number;
  color?: string;
  is_template?: boolean;
  meta_data?: object;
  created_at?: string;
  updated_at?: string;
  is_active?: boolean;
  has_user_tasks?: boolean;
  has_access?: boolean;
  member_count?: number;
  members?: any[];
} 