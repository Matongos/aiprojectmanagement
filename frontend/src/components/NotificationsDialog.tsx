import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { API_BASE_URL } from '@/lib/constants';
import { useAuthStore } from '@/store/authStore';
import { formatDistanceToNow } from 'date-fns';
import { Check } from 'lucide-react';

interface Notification {
  id: number;
  title: string;
  content: string | null;
  type: string;
  is_read: boolean;
  reference_type: string | null;
  reference_id: number | null;
  created_at: string;
  updated_at: string;
}

interface NotificationsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onNotificationsRead: () => void;
}

export const NotificationsDialog = ({ open, onOpenChange, onNotificationsRead }: NotificationsDialogProps) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { token } = useAuthStore();
  const router = useRouter();

  const fetchNotifications = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/notifications`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch notifications');
      }

      const data = await response.json();
      setNotifications(data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const markAllAsRead = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/notifications/mark-all-read`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to mark notifications as read');
      }

      await fetchNotifications();
      onNotificationsRead();
    } catch (error) {
      console.error('Error marking notifications as read:', error);
    }
  };

  const markAsRead = async (notificationId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/notifications/${notificationId}/read`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to mark notification as read');
      }

      await fetchNotifications();
      onNotificationsRead();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      markAsRead(notification.id);
    }

    if (notification.reference_type && notification.reference_id) {
      switch (notification.reference_type) {
        case 'task':
          if (notification.type === 'task_assignment') {
            fetch(`${API_BASE_URL}/tasks/${notification.reference_id}`, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            })
            .then(response => response.json())
            .then(task => {
              router.push(`/dashboard/projects/${task.project_id}/tasks/${notification.reference_id}`);
            })
            .catch(error => {
              console.error('Error fetching task details:', error);
              router.push(`/dashboard/tasks/${notification.reference_id}`);
            });
          } else {
            router.push(`/dashboard/tasks/${notification.reference_id}`);
          }
          break;
        case 'project':
          router.push(`/dashboard/projects/${notification.reference_id}`);
          break;
      }
      onOpenChange(false);
    }
  };

  // Helper function to get notification style based on type
  const getNotificationStyle = (notification: Notification) => {
    switch (notification.type) {
      case 'task_assignment':
        return 'bg-blue-50 hover:bg-blue-100';
      case 'task_update':
        return 'bg-purple-50 hover:bg-purple-100';
      case 'comment':
        return 'bg-green-50 hover:bg-green-100';
      default:
        return notification.is_read ? 'bg-gray-50 hover:bg-gray-100' : 'bg-blue-50 hover:bg-blue-100';
    }
  };

  useEffect(() => {
    if (open) {
      fetchNotifications();
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex justify-between items-center">
            <span>Notifications</span>
            <Button variant="ghost" size="sm" onClick={markAllAsRead}>
              Mark all as read
            </Button>
          </DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[400px] pr-4">
          {notifications.length === 0 ? (
            <div className="text-center text-gray-500 py-4">
              No notifications
            </div>
          ) : (
            <div className="space-y-2">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${getNotificationStyle(notification)}`}
                  onClick={() => handleNotificationClick(notification)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-medium text-sm">{notification.title}</h4>
                      <p className="text-sm text-gray-600">{notification.content}</p>
                      <span className="text-xs text-gray-400">
                        {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                      </span>
                    </div>
                    {notification.is_read && (
                      <Check className="h-4 w-4 text-green-500" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}; 