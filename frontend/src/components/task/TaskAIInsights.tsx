import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { AlertCircle, Brain, Clock, TrendingUp } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { Skeleton } from "../ui/skeleton";

interface TaskAnalysis {
    complexity: number;
    risk_factors: string[];
    time_accuracy: number;
    suggestions: string[];
    patterns: {
        type: string;
        common_issues: string[];
        success_factors: string[];
    }
}

interface TimeEstimate {
    estimated_hours: number;
}

interface PrioritySuggestion {
    priority: string;
}

interface TaskAIInsightsProps {
    taskId: number;
    token: string;
}

export function TaskAIInsights({ taskId, token }: TaskAIInsightsProps) {
    // Fetch task analysis
    const { data: analysis, isLoading: analysisLoading } = useQuery<TaskAnalysis>({
        queryKey: ["task-analysis", taskId],
        queryFn: async () => {
            const response = await fetch(`${API_BASE_URL}/ai/tasks/${taskId}/analyze`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!response.ok) throw new Error("Failed to fetch task analysis");
            return response.json();
        },
    });

    // Fetch time estimate
    const { data: timeEstimate, isLoading: timeLoading } = useQuery<TimeEstimate>({
        queryKey: ["task-time-estimate", taskId],
        queryFn: async () => {
            const response = await fetch(`${API_BASE_URL}/ai/tasks/${taskId}/estimate-time`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!response.ok) throw new Error("Failed to fetch time estimate");
            return response.json();
        },
    });

    // Fetch priority suggestion
    const { data: prioritySuggestion, isLoading: priorityLoading } = useQuery<PrioritySuggestion>({
        queryKey: ["task-priority", taskId],
        queryFn: async () => {
            const response = await fetch(`${API_BASE_URL}/ai/tasks/${taskId}/suggest-priority`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!response.ok) throw new Error("Failed to fetch priority suggestion");
            return response.json();
        },
    });

    if (analysisLoading || timeLoading || priorityLoading) {
        return <Skeleton className="w-full h-[300px]" />;
    }

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Brain className="w-5 h-5" />
                        AI Task Insights
                    </CardTitle>
                    <CardDescription>
                        AI-powered analysis and recommendations
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-6">
                        {/* Complexity and Time Accuracy */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <h4 className="text-sm font-medium mb-2">Task Complexity</h4>
                                <div className="flex items-center gap-2">
                                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                                        <div 
                                            className="bg-blue-600 h-2.5 rounded-full" 
                                            style={{ width: `${(analysis?.complexity || 0) * 10}%` }}
                                        />
                                    </div>
                                    <span className="text-sm">{analysis?.complexity}/10</span>
                                </div>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium mb-2">Time Accuracy</h4>
                                <div className="flex items-center gap-2">
                                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                                        <div 
                                            className="bg-green-600 h-2.5 rounded-full" 
                                            style={{ width: `${(analysis?.time_accuracy || 0) * 100}%` }}
                                        />
                                    </div>
                                    <span className="text-sm">{Math.round((analysis?.time_accuracy || 0) * 100)}%</span>
                                </div>
                            </div>
                        </div>

                        {/* Time Estimate */}
                        <div>
                            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Clock className="w-4 h-4" />
                                Estimated Time
                            </h4>
                            <p className="text-2xl font-bold">
                                {timeEstimate?.estimated_hours.toFixed(1)} hours
                            </p>
                        </div>

                        {/* Suggested Priority */}
                        <div>
                            <h4 className="text-sm font-medium mb-2">Suggested Priority</h4>
                            <Badge 
                                variant={
                                    prioritySuggestion?.priority === 'high' ? 'destructive' :
                                    prioritySuggestion?.priority === 'medium' ? 'default' :
                                    'secondary'
                                }
                            >
                                {prioritySuggestion?.priority.toUpperCase()}
                            </Badge>
                        </div>

                        {/* Risk Factors */}
                        {analysis?.risk_factors.length > 0 && (
                            <div>
                                <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                    <AlertCircle className="w-4 h-4" />
                                    Risk Factors
                                </h4>
                                <ul className="list-disc list-inside space-y-1">
                                    {analysis.risk_factors.map((factor, index) => (
                                        <li key={index} className="text-sm text-gray-600">
                                            {factor}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Suggestions */}
                        {analysis?.suggestions.length > 0 && (
                            <div>
                                <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                    <TrendingUp className="w-4 h-4" />
                                    Suggestions
                                </h4>
                                <ul className="list-disc list-inside space-y-1">
                                    {analysis.suggestions.map((suggestion, index) => (
                                        <li key={index} className="text-sm text-gray-600">
                                            {suggestion}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
} 