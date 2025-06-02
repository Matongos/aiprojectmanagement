export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  profile_image_url: string | null;
  project_roles?: { [key: number]: 'manager' | 'member' | 'viewer' };
  created_at: string;
  updated_at: string;
} 