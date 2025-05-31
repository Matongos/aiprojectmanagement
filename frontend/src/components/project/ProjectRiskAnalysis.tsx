import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { AlertTriangle, Shield, Timer, Users } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { Skeleton } from "../ui/skeleton";

interface ProjectRiskAnalysis {
    risk_level: number;
    risk_factors: string[];
    mitigations: string[];
    timeline_status: string;
    resource_recommendations: string[];
}

interface ProjectRiskAnalysisProps {
    projectId: number;
    token: string;
}

export function ProjectRiskAnalysis({ projectId, token }: ProjectRiskAnalysisProps) {
    const { data: analysis, isLoading } = useQuery<ProjectRiskAnalysis>({
        queryKey: ["project-risks", projectId],
        queryFn: async () => {
            const response = await fetch(`${API_BASE_URL}/ai/projects/${projectId}/risks`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!response.ok) throw new Error("Failed to fetch project risk analysis");
            return response.json();
        },
    });

    if (isLoading) {
        return <Skeleton className="w-full h-[400px]" />;
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5" />
                    Project Risk Analysis
                </CardTitle>
                <CardDescription>
                    AI-powered risk assessment and recommendations
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-6">
                    {/* Risk Level Indicator */}
                    <div>
                        <h4 className="text-sm font-medium mb-2">Risk Level</h4>
                        <div className="flex items-center gap-2">
                            <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div 
                                    className={`h-2.5 rounded-full ${
                                        analysis?.risk_level <= 3 ? 'bg-green-500' :
                                        analysis?.risk_level <= 7 ? 'bg-yellow-500' :
                                        'bg-red-500'
                                    }`}
                                    style={{ width: `${(analysis?.risk_level || 0) * 10}%` }}
                                />
                            </div>
                            <span className="text-sm font-medium">
                                {analysis?.risk_level}/10
                            </span>
                        </div>
                    </div>

                    {/* Timeline Status */}
                    <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                            <Timer className="w-4 h-4" />
                            Timeline Status
                        </h4>
                        <p className="text-sm text-gray-600">
                            {analysis?.timeline_status}
                        </p>
                    </div>

                    {/* Risk Factors */}
                    {analysis?.risk_factors.length > 0 && (
                        <div>
                            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4" />
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

                    {/* Mitigations */}
                    {analysis?.mitigations.length > 0 && (
                        <div>
                            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Shield className="w-4 h-4" />
                                Recommended Mitigations
                            </h4>
                            <ul className="list-disc list-inside space-y-1">
                                {analysis.mitigations.map((mitigation, index) => (
                                    <li key={index} className="text-sm text-gray-600">
                                        {mitigation}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Resource Recommendations */}
                    {analysis?.resource_recommendations.length > 0 && (
                        <div>
                            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Users className="w-4 h-4" />
                                Resource Recommendations
                            </h4>
                            <ul className="list-disc list-inside space-y-1">
                                {analysis.resource_recommendations.map((recommendation, index) => (
                                    <li key={index} className="text-sm text-gray-600">
                                        {recommendation}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
} 