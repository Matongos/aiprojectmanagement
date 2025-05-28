import { useEffect, useCallback } from 'react';
import { websocketService } from '@/services/websocket';
import { useDashboardStore } from '@/store/dashboardStore';
import { useAuthStore } from '@/store/authStore';

export const useWebSocket = (projectId: string) => {
  const { token } = useAuthStore();
  const setMetrics = useDashboardStore((state) => state.setMetrics);

  const handleWebSocketMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'metrics_update':
        setMetrics(data.metrics);
        break;
      case 'task_update':
        // Trigger a metrics refresh when tasks are updated
        if (token) {
          useDashboardStore.getState().fetchMetrics(token);
        }
        break;
      case 'ai_insight':
        setMetrics({
          aiInsights: {
            riskLevel: data.riskLevel,
            suggestions: data.suggestions,
            predictedDelays: data.predictedDelays
          }
        });
        break;
      default:
        console.log('Unhandled WebSocket message type:', data.type);
    }
  }, [setMetrics, token]);

  useEffect(() => {
    if (!token || !projectId) return;

    // Connect to WebSocket
    websocketService.connect(projectId, token);

    // Subscribe to different message types
    websocketService.subscribe('metrics_update', handleWebSocketMessage);
    websocketService.subscribe('task_update', handleWebSocketMessage);
    websocketService.subscribe('ai_insight', handleWebSocketMessage);

    // Monitor connection status
    const unsubscribe = websocketService.onStatusChange((status) => {
      console.log('WebSocket status:', status);
    });

    return () => {
      // Cleanup subscriptions
      websocketService.unsubscribe('metrics_update', handleWebSocketMessage);
      websocketService.unsubscribe('task_update', handleWebSocketMessage);
      websocketService.unsubscribe('ai_insight', handleWebSocketMessage);
      unsubscribe();
      websocketService.disconnect();
    };
  }, [projectId, token, handleWebSocketMessage]);

  return websocketService.getStatus();
}; 