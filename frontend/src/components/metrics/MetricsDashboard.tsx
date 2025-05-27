import React, { useEffect, useState } from 'react';
import { Card, Grid, Typography, Box, CircularProgress } from '@mui/material';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    BarChart, Bar, ResponsiveContainer
} from 'recharts';
import { metricsService, ProjectMetricsSummary } from '../../services/metricsService';

interface MetricsDashboardProps {
    projectId: number;
}

export const MetricsDashboard: React.FC<MetricsDashboardProps> = ({ projectId }) => {
    const [metrics, setMetrics] = useState<ProjectMetricsSummary | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const data = await metricsService.getProjectMetricsSummary(projectId);
                setMetrics(data);
            } catch (error) {
                console.error('Error fetching metrics:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchMetrics();
        // Set up polling every 5 minutes
        const interval = setInterval(fetchMetrics, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [projectId]);

    if (loading) {
        return <CircularProgress />;
    }

    if (!metrics) {
        return <Typography>No metrics available</Typography>;
    }

    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>Project Metrics Dashboard</Typography>
            
            <Grid container spacing={3}>
                {/* Summary Cards */}
                <Grid item xs={12} md={3}>
                    <Card sx={{ p: 2 }}>
                        <Typography variant="h6">Completion Rate</Typography>
                        <Typography variant="h4">
                            {(metrics.summary.completion_rate * 100).toFixed(1)}%
                        </Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ p: 2 }}>
                        <Typography variant="h6">Resource Utilization</Typography>
                        <Typography variant="h4">
                            {(metrics.project_metrics.resource_utilization * 100).toFixed(1)}%
                        </Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ p: 2 }}>
                        <Typography variant="h6">Velocity</Typography>
                        <Typography variant="h4">
                            {metrics.project_metrics.velocity.toFixed(1)}
                        </Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ p: 2 }}>
                        <Typography variant="h6">Team Load</Typography>
                        <Typography variant="h4">
                            {metrics.project_metrics.team_load.toFixed(1)}h
                        </Typography>
                    </Card>
                </Grid>

                {/* Task Progress Chart */}
                <Grid item xs={12} md={6}>
                    <Card sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Task Completion Trend</Typography>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart
                                data={metrics.task_metrics.map((task, index) => ({
                                    name: `Task ${index + 1}`,
                                    duration: task.actual_duration,
                                    estimate: task.time_estimate_accuracy * task.actual_duration
                                }))}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="duration" stroke="#8884d8" name="Actual Duration" />
                                <Line type="monotone" dataKey="estimate" stroke="#82ca9d" name="Estimated Duration" />
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>
                </Grid>

                {/* Resource Utilization Chart */}
                <Grid item xs={12} md={6}>
                    <Card sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Resource Utilization</Typography>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart
                                data={metrics.resource_metrics.map((resource, index) => ({
                                    name: `Resource ${index + 1}`,
                                    utilization: resource.availability_rate * 100,
                                    productivity: resource.productivity_score * 100
                                }))}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="utilization" fill="#8884d8" name="Utilization %" />
                                <Bar dataKey="productivity" fill="#82ca9d" name="Productivity %" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Grid>

                {/* Quality Metrics */}
                <Grid item xs={12}>
                    <Card sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Quality Metrics</Typography>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart
                                data={[{
                                    name: 'Quality Metrics',
                                    defects: metrics.project_metrics.defect_density * 100,
                                    rework: metrics.project_metrics.rework_rate * 100,
                                    milestone: metrics.project_metrics.milestone_completion_rate * 100
                                }]}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="defects" fill="#ff8a80" name="Defect Density %" />
                                <Bar dataKey="rework" fill="#b388ff" name="Rework Rate %" />
                                <Bar dataKey="milestone" fill="#80cbc4" name="Milestone Completion %" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>
                </Grid>
            </Grid>
        </Box>
    );
}; 