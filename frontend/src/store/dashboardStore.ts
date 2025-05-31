import { create } from 'zustand';
import { API_BASE_URL } from '@/lib/constants';

interface TaskTrendItem {
  date: string;
  count: number;
}

interface TaskTrendResponse {
  created_tasks: TaskTrendItem[];
  completed_tasks: TaskTrendItem[];
}

interface DashboardMetrics {
  totalTasks: number;
  completedTasks: number;
  completionRate: number;
  averageCompletionTime: number;
  tasksByState: Record<string, number>;
  productivityScore: number;
  taskTrend: {
    labels: string[];
    created: number[];
    completed: number[];
  };
  aiInsights: {
    riskLevel: string;
    suggestions: string[];
    predictedDelays: number;
    taskPriorities: {
      high: number;
      medium: number;
      low: number;
    };
    resourceUtilization: {
      current: number;
      optimal: number;
      recommendations: string[];
    };
    performanceMetrics: {
      velocity: number;
      qualityScore: number;
      bottlenecks: string[];
    };
    milestoneRisk: {
      atRisk: number;
      onTrack: number;
      completed: number;
      predictions: Array<{
        milestone: string;
        probability: number;
        suggestedActions: string[];
      }>;
    };
  };
}

const defaultMetrics: DashboardMetrics = {
  totalTasks: 0,
  completedTasks: 0,
  completionRate: 0,
  averageCompletionTime: 0,
  tasksByState: { 'No Data': 0 },
  productivityScore: 0,
  taskTrend: {
    labels: [],
    created: [],
    completed: [],
  },
  aiInsights: {
    riskLevel: 'Low',
    suggestions: [],
    predictedDelays: 0,
    taskPriorities: {
      high: 0,
      medium: 0,
      low: 0
    },
    resourceUtilization: {
      current: 0,
      optimal: 0,
      recommendations: []
    },
    performanceMetrics: {
      velocity: 0,
      qualityScore: 0,
      bottlenecks: []
    },
    milestoneRisk: {
      atRisk: 0,
      onTrack: 0,
      completed: 0,
      predictions: []
    }
  },
};

interface DashboardStore {
  metrics: DashboardMetrics;
  loading: boolean;
  error: string | null;
  fetchMetrics: (token: string) => Promise<void>;
  setMetrics: (metrics: Partial<DashboardMetrics>) => void;
  updateAIInsights: (insights: Partial<DashboardMetrics['aiInsights']>) => void;
  clearMetrics: () => void;
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  metrics: defaultMetrics,
  loading: false,
  error: null,
  fetchMetrics: async (token: string) => {
    set({ loading: true, error: null });
    try {
      if (!token) {
        throw new Error('No authentication token available');
      }

      // Fetch task metrics and trend data (these endpoints exist)
      const [taskMetrics, taskTrendResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/analytics/tasks/summary`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
        }).then(async (res) => {
          if (!res.ok) {
            const errorText = await res.text();
            console.error('Task summary response not OK:', errorText);
            throw new Error(`Failed to fetch task summary: ${res.status} ${res.statusText}`);
          }
          return res.json();
        }),
        fetch(`${API_BASE_URL}/analytics/tasks/trend?days=30`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
        }).then(async (res) => {
          if (!res.ok) {
            const errorText = await res.text();
            console.error('Task trend response not OK:', errorText);
            throw new Error(`Failed to fetch task trend: ${res.status} ${res.statusText}`);
          }
          const data = await res.json();
          console.log('Task trend response:', data); // Debug log
          return data as TaskTrendResponse;
        }),
      ]);

      // Transform task trend data into the expected format
      const taskTrend = {
        labels: [] as string[],
        created: [] as number[],
        completed: [] as number[]
      };

      if (taskTrendResponse && Array.isArray(taskTrendResponse.created_tasks) && Array.isArray(taskTrendResponse.completed_tasks)) {
        // Get all unique dates from both created and completed tasks
        const allDates = new Set([
          ...taskTrendResponse.created_tasks.map(t => t.date),
          ...taskTrendResponse.completed_tasks.map(t => t.date)
        ]);

        // Sort dates chronologically
        taskTrend.labels = Array.from(allDates).sort();

        // Map the counts for each date
        taskTrend.created = taskTrend.labels.map(date => 
          taskTrendResponse.created_tasks.find(t => t.date === date)?.count || 0
        );
        taskTrend.completed = taskTrend.labels.map(date => 
          taskTrendResponse.completed_tasks.find(t => t.date === date)?.count || 0
        );
      } else {
        console.warn('Invalid task trend response format:', taskTrendResponse);
      }

      // Use default values for AI insights since those endpoints don't exist yet
      const safeAiInsights = {
        riskLevel: 'Low',
        suggestions: ['System is still gathering data for AI insights'],
        predictedDelays: 0,
        taskPriorities: defaultMetrics.aiInsights.taskPriorities,
        resourceUtilization: defaultMetrics.aiInsights.resourceUtilization,
        performanceMetrics: defaultMetrics.aiInsights.performanceMetrics,
        milestoneRisk: defaultMetrics.aiInsights.milestoneRisk
      };

      const updatedMetrics = {
        ...defaultMetrics,
        totalTasks: taskMetrics?.total_tasks || 0,
        completedTasks: taskMetrics?.tasks_by_status?.done || 0,
        averageCompletionTime: taskMetrics?.avg_completion_time_hours || 0,
        tasksByState: taskMetrics?.tasks_by_status || defaultMetrics.tasksByState,
        taskTrend,
        aiInsights: safeAiInsights,
        productivityScore: taskMetrics?.productivity_score || 0,
      };

      set({
        metrics: updatedMetrics,
        loading: false,
      });
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch metrics', 
        loading: false,
        metrics: defaultMetrics,
      });
    }
  },
  setMetrics: (metrics: Partial<DashboardMetrics>) => 
    set((state) => ({ 
      metrics: { 
        ...state.metrics, 
        ...metrics,
        aiInsights: {
          ...state.metrics.aiInsights,
          ...(metrics.aiInsights || {}),
        },
      } 
    })),
  updateAIInsights: (insights: Partial<DashboardMetrics['aiInsights']>) =>
    set((state) => ({
      metrics: {
        ...state.metrics,
        aiInsights: {
          ...state.metrics.aiInsights,
          ...insights,
        },
      },
    })),
  clearMetrics: () => set({ metrics: defaultMetrics }),
})); 