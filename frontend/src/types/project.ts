export interface Project {
  id: number;
  name: string;
  description: string | null;
  key: string;
  privacy_level: string;
  start_date: string | null;
  end_date: string | null;
  created_by: number;
  color: string;
  is_template: boolean;
  meta_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  has_user_tasks?: boolean;
  has_access?: boolean;
  member_count: number;
  members: {
    id: number;
    user_id: number;
    role: string;
    user: {
      id: number;
      name: string;
      profile_image_url: string | null;
    };
  }[];
} 