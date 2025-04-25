// Import API_BASE_URL from constants
import { API_BASE_URL } from './constants';
import { fetchApi } from './api-helper';

// Dashboard API calls
export async function getRecentProjects(): Promise<any[]> {
  try {
    return await fetchApi<any[]>('/projects/recent');
  } catch (error) {
    console.error('Error fetching recent projects:', error);
    // Return mock data for now
    return [
      {
        id: '1',
        name: 'Website Redesign',
        description: 'Redesign the company website with modern UI/UX principles',
        progress: 65,
        team_size: 4,
        deadline: '2023-12-15',
      },
      {
        id: '2',
        name: 'Mobile App Development',
        description: 'Develop a cross-platform mobile app for customer engagement',
        progress: 32,
        team_size: 6,
        deadline: '2024-02-28',
      },
      {
        id: '3',
        name: 'Marketing Campaign',
        description: 'Q4 marketing campaign for new product launch',
        progress: 78,
        team_size: 3,
        deadline: '2023-11-30',
      },
    ];
  }
}

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