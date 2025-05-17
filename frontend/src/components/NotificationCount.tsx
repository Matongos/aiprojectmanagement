import { useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { API_BASE_URL } from '@/lib/constants';
import { useAuthStore } from '@/store/authStore';
import { NotificationsDialog } from '@/components/NotificationsDialog';

export const NotificationCount = () => {
  const [count, setCount] = useState(0);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { token } = useAuthStore();

  const fetchNotificationCount = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/notifications/unread-count`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch notification count');
      }

      const data = await response.json();
      setCount(data.count);
    } catch (error) {
      console.error('Error fetching notification count:', error);
    }
  };

  useEffect(() => {
    fetchNotificationCount();

    // Set up polling for notification count
    const interval = setInterval(fetchNotificationCount, 30000); // Poll every 30 seconds

    return () => clearInterval(interval);
  }, [token]);

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setIsDialogOpen(true)}
      >
        <Bell className="h-5 w-5" />
        {count > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full min-w-[18px] h-[18px] flex items-center justify-center">
            {count > 99 ? '99+' : count}
          </span>
        )}
      </Button>

      <NotificationsDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        onNotificationsRead={fetchNotificationCount}
      />
    </>
  );
}; 