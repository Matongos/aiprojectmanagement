import { API_BASE_URL } from '@/lib/constants';

type MessageHandler = (data: any) => void;
type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

class WebSocketService {
    private socket: WebSocket | null = null;
    private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectTimeout = 1000; // Start with 1 second
    private projectId: string | null = null;
    private token: string | null = null;
    private status: WebSocketStatus = 'disconnected';
    private statusListeners: Set<(status: WebSocketStatus) => void> = new Set();

    connect(projectId: string, token: string) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            return;
        }

        this.projectId = projectId;
        this.token = token;
        this.updateStatus('connecting');

        const wsUrl = API_BASE_URL.replace('http', 'ws');
        this.socket = new WebSocket(`${wsUrl}/ws/project/${projectId}`);

        this.socket.onopen = () => {
            this.reconnectAttempts = 0;
            this.reconnectTimeout = 1000;
            this.updateStatus('connected');
            
            // Set up authentication
            if (this.socket && this.token) {
                this.socket.send(JSON.stringify({
                    type: 'authentication',
                    token: this.token
                }));
            }
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const handlers = this.messageHandlers.get(data.type);
                if (handlers) {
                    handlers.forEach(handler => handler(data));
                }
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };

        this.socket.onclose = () => {
            this.updateStatus('disconnected');
            this.reconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('error');
            this.socket?.close();
        };
    }

    private reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }

        setTimeout(() => {
            if (this.projectId && this.token) {
                this.reconnectAttempts++;
                this.reconnectTimeout *= 2; // Exponential backoff
                this.connect(this.projectId, this.token);
            }
        }, this.reconnectTimeout);
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
            this.updateStatus('disconnected');
        }
    }

    subscribe(messageType: string, handler: MessageHandler) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, new Set());
        }
        this.messageHandlers.get(messageType)?.add(handler);
    }

    unsubscribe(messageType: string, handler: MessageHandler) {
        this.messageHandlers.get(messageType)?.delete(handler);
    }

    send(message: any) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    onStatusChange(listener: (status: WebSocketStatus) => void) {
        this.statusListeners.add(listener);
        return () => this.statusListeners.delete(listener);
    }

    private updateStatus(status: WebSocketStatus) {
        this.status = status;
        this.statusListeners.forEach(listener => listener(status));
    }

    getStatus(): WebSocketStatus {
        return this.status;
    }
}

// Create a singleton instance
export const websocketService = new WebSocketService(); 