// Import API_BASE_URL from constants
import { API_BASE_URL } from './constants';
import { fetchApi } from './api-helper';
import { useAuthStore } from '@/store/authStore';

export interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  has_user_tasks?: boolean;
  has_access?: boolean;
  created_by?: number;
  members?: {
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

// Dashboard API calls
export const getRecentProjects = async (): Promise<Project[]> => {
  try {
    // First try to get recent projects with query params
    const data = await fetchApi<Project[]>('/projects?sort=-created_at&limit=5');
    
    // Get user tasks to check which projects the user has tasks in
    let userTasks: any[] = [];
    try {
      userTasks = await fetchApi<any[]>('/tasks/');
    } catch (taskError) {
      console.error('Error fetching user tasks:', taskError);
      // Continue with empty user tasks instead of failing the whole operation
    }
    
    // Get current user info to check if they're the creator
    const currentUser = useAuthStore.getState().user;
    const isAdmin = !!currentUser?.is_superuser;
    
    // Add a flag to indicate if the user has tasks in each project
    const projectsWithUserTasksInfo = data.map(project => {
      const hasUserTasks = userTasks.length > 0
        ? userTasks.some(task => task.project_id === project.id)
        : false;
      
      const isCreator = project.created_by === Number(currentUser?.id);
      
      return {
        ...project,
        has_user_tasks: hasUserTasks,
        has_access: isAdmin || isCreator || hasUserTasks
      };
    });
    
    return projectsWithUserTasksInfo;
  } catch (error) {
    console.error('Error fetching recent projects:', error);
    // Return empty array to prevent UI errors
    return [];
  }
};

export async function getUpcomingTasks(): Promise<any[]> {
  try {
    return await fetchApi<any[]>('/tasks/upcoming');
  } catch (error) {
    console.error('Error fetching upcoming tasks:', error);
    // Return mock data for now
    return [
      {
        id: '1',
        title: 'Finalize Homepage Design',
        description: 'Complete the design for the homepage',
        status: 'IN_PROGRESS',
        due_date: '2023-11-15',
        project_id: '1',
        project_name: 'Website Redesign',
      },
      {
        id: '2',
        title: 'API Integration',
        description: 'Integrate payment API into the mobile app',
        status: 'TODO',
        due_date: '2023-11-20',
        project_id: '2',
        project_name: 'Mobile App Development',
      },
      {
        id: '3',
        title: 'Create Social Media Content',
        description: 'Develop content for social media platforms',
        status: 'COMPLETED',
        due_date: '2023-11-10',
        project_id: '3',
        project_name: 'Marketing Campaign',
      },
      {
        id: '4',
        title: 'User Testing',
        description: 'Conduct user testing sessions for the new features',
        status: 'TODO',
        due_date: '2023-11-25',
        project_id: '2',
        project_name: 'Mobile App Development',
      },
    ];
  }
}

// File attachment API functions
export const getTaskAttachments = async (taskId: number) => {
  const response = await fetch(`/api/tasks/${taskId}/attachments`, {
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch task attachments');
  }
  
  return response.json();
};

export const uploadTaskAttachment = async (taskId: number, file: File, description?: string) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('task_id', taskId.toString());
  
  if (description) {
    formData.append('description', description);
  }
  
  const response = await fetch('/api/file-attachments', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`
    },
    body: formData
  });
  
  if (!response.ok) {
    throw new Error('Failed to upload file');
  }
  
  return response.json();
};

export const deleteFileAttachment = async (fileId: number) => {
  const response = await fetch(`/api/file-attachments/${fileId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to delete file');
  }
  
  return true;
};

export const getProjectById = async (projectId: number): Promise<Project> => {
  try {
    const data = await fetchApi<Project>(`/projects/${projectId}`);
    return data;
  } catch (error) {
    console.error('Error fetching project details:', error);
    throw error;
  }
}; 