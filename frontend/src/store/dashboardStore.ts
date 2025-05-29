import { create } from 'zustand';
import { API_BASE_URL } from '@/lib/constants';

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
      const [taskMetrics, taskTrend, aiInsights, resourceMetrics] = await Promise.all([
        fetch(`${API_BASE_URL}/analytics/tasks/summary`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.json()),
        fetch(`${API_BASE_URL}/analytics/tasks/trend?days=30`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.json()),
        fetch(`${API_BASE_URL}/ai/projects/risks`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.json()),
        fetch(`${API_BASE_URL}/ai/resources/optimization`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.json()),
      ]);

      console.log('Task Metrics Response:', JSON.stringify(taskMetrics, null, 2));
      console.log('Task Trend Response:', JSON.stringify(taskTrend, null, 2));
      console.log('AI Insights Response:', JSON.stringify(aiInsights, null, 2));
      console.log('Resource Metrics Response:', JSON.stringify(resourceMetrics, null, 2));

      // Ensure aiInsights has all required properties with fallbacks
      const safeAiInsights = {
        riskLevel: aiInsights?.riskLevel || defaultMetrics.aiInsights.riskLevel,
        suggestions: Array.isArray(aiInsights?.suggestions) 
          ? aiInsights.suggestions 
          : defaultMetrics.aiInsights.suggestions,
        predictedDelays: typeof aiInsights?.predictedDelays === 'number'
          ? aiInsights.predictedDelays
          : defaultMetrics.aiInsights.predictedDelays,
        taskPriorities: {
          ...defaultMetrics.aiInsights.taskPriorities,
          ...aiInsights?.taskPriorities
        },
        resourceUtilization: {
          ...defaultMetrics.aiInsights.resourceUtilization,
          ...resourceMetrics
        },
        performanceMetrics: {
          ...defaultMetrics.aiInsights.performanceMetrics,
          ...aiInsights?.performanceMetrics
        },
        milestoneRisk: {
          ...defaultMetrics.aiInsights.milestoneRisk,
          ...aiInsights?.milestoneRisk
        }
      };

      const updatedMetrics = {
        ...defaultMetrics,
        totalTasks: taskMetrics?.total_tasks || 0,
        completedTasks: taskMetrics?.tasks_by_status?.done || 0,
        averageCompletionTime: taskMetrics?.avg_completion_time_hours || 0,
        tasksByState: taskMetrics?.tasks_by_status || defaultMetrics.tasksByState,
        taskTrend: {
          labels: Array.isArray(taskTrend) ? taskTrend.map((t: any) => t.date) : [],
          created: Array.isArray(taskTrend) ? taskTrend.map((t: any) => t.created) : [],
          completed: Array.isArray(taskTrend) ? taskTrend.map((t: any) => t.completed) : [],
        },
        aiInsights: safeAiInsights,
      };

      console.log('Updated Metrics:', updatedMetrics);

      set({
        metrics: updatedMetrics,
        loading: false,
      });
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      set({ 
        error: 'Failed to fetch metrics', 
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