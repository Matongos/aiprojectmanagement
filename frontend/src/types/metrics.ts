export interface DashboardMetrics {
    totalTasks: number;
    completedTasks: number;
    averageCompletionTime: number;
    completionTimeTrend: number;
    productivityScore: number;
    insights: string[];
    taskTrend?: {
        labels: string[];
        created: number[];
        completed: number[];
    };
    tasksByState?: Record<string, number>;
    aiInsights?: {
        suggestions: string[];
        riskLevel: string;
        predictedDelays: number;
    };
} 