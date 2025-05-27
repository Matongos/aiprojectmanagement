import axios from 'axios';
import { API_BASE_URL } from '../config';

export interface ProjectMetrics {
    schedule_variance: number;
    milestone_completion_rate: number;
    budget_utilization: number;
    cost_variance: number;
    defect_density: number;
    rework_rate: number;
    velocity: number;
    throughput: number;
    resource_utilization: number;
    team_load: number;
}

export interface TaskMetrics {
    actual_duration: number;
    time_estimate_accuracy: number;
    idle_time: number;
    review_iterations: number;
    bug_count: number;
    rework_hours: number;
    complexity_score: number;
    dependency_count: number;
    handover_count: number;
    comment_count: number;
    state_changes: any[];
    blocked_time: number;
}

export interface ResourceMetrics {
    billable_hours: number;
    availability_rate: number;
    overtime_hours: number;
    task_completion_rate: number;
    average_task_duration: number;
    productivity_score: number;
    skill_utilization: Record<string, number>;
    learning_curve: number;
    collaboration_score: number;
    response_time: number;
}

export interface ProjectMetricsSummary {
    project_metrics: ProjectMetrics;
    summary: {
        total_tasks: number;
        completed_tasks: number;
        completion_rate: number;
        total_time_spent: number;
        average_task_duration: number;
    };
    task_metrics: TaskMetrics[];
    resource_metrics: ResourceMetrics[];
}

class MetricsService {
    async getProjectMetrics(projectId: number): Promise<ProjectMetrics> {
        const response = await axios.get(`${API_BASE_URL}/metrics/project/${projectId}`);
        return response.data;
    }

    async getTaskMetrics(taskId: number): Promise<TaskMetrics> {
        const response = await axios.get(`${API_BASE_URL}/metrics/task/${taskId}`);
        return response.data;
    }

    async getProjectResourceMetrics(projectId: number): Promise<ResourceMetrics[]> {
        const response = await axios.get(`${API_BASE_URL}/metrics/project/${projectId}/resources`);
        return response.data;
    }

    async getProjectMetricsSummary(projectId: number): Promise<ProjectMetricsSummary> {
        const response = await axios.get(`${API_BASE_URL}/metrics/project/${projectId}/summary`);
        return response.data;
    }

    async triggerMetricsUpdate(): Promise<void> {
        await axios.post(`${API_BASE_URL}/metrics/update-all`);
    }
}

export const metricsService = new MetricsService(); 