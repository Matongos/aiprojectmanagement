// Dashboard API calls
export async function getRecentProjects(): Promise<any[]> {
  try {
    const token = localStorage.getItem('token');
    
    if (!token) {
      throw new Error('Not authenticated');
    }
    
    const response = await fetch(`${API_BASE_URL}/projects/recent`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch recent projects');
    }
    
    const data = await response.json();
    return data;
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
    const token = localStorage.getItem('token');
    
    if (!token) {
      throw new Error('Not authenticated');
    }
    
    const response = await fetch(`${API_BASE_URL}/tasks/upcoming`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch upcoming tasks');
    }
    
    const data = await response.json();
    return data;
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