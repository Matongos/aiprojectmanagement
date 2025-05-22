import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Input } from '@/components/ui/input';
import { Search, UserPlus, X } from 'lucide-react';
import { API_BASE_URL } from '@/lib/constants';
import { useAuthStore } from '@/store/authStore';
import { toast } from 'react-hot-toast';

interface User {
  id: number;
  name: string;
  email: string;
  profile_image_url: string | null;
}

interface FollowersDialogProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: number;
}

export default function FollowersDialog({ isOpen, onClose, projectId }: FollowersDialogProps) {
  const [followers, setFollowers] = useState<User[]>([]);
  const [nonFollowers, setNonFollowers] = useState<User[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const { token } = useAuthStore();

  const fetchFollowers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/followers`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch followers');
      }

      const data = await response.json();
      setFollowers(data);
    } catch (error) {
      console.error('Error fetching followers:', error);
      toast.error('Failed to load followers');
    }
  };

  const fetchAllUsers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }

      const allUsers = await response.json();
      // Filter out users who are already followers
      const nonFollowersList = allUsers.filter(
        (user: User) => !followers.some(follower => follower.id === user.id)
      );
      setNonFollowers(nonFollowersList);
    } catch (error) {
      console.error('Error fetching non-followers:', error);
      toast.error('Failed to load users');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      // First fetch followers, then fetch all users
      fetchFollowers().then(() => fetchAllUsers());
    }
  }, [isOpen, projectId]);

  const handleAddFollower = async (userId: number) => {
    try {
      console.log('Adding follower:', { projectId, userId, token: token ? 'present' : 'missing' });
      console.log('API URL:', `${API_BASE_URL}/projects/${projectId}/followers/${userId}`);
      
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/followers/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        console.error('Failed to add follower:', {
          status: response.status,
          statusText: response.statusText,
          errorData,
          url: response.url
        });
        throw new Error(errorData?.detail || `Failed to add follower: ${response.status} ${response.statusText}`);
      }

      // Update the lists
      const userToAdd = nonFollowers.find(user => user.id === userId);
      if (userToAdd) {
        // Add to followers list
        setFollowers(prev => [...prev, userToAdd]);
        // Remove from non-followers list
        setNonFollowers(prev => prev.filter(user => user.id !== userId));
      }
      toast.success('Follower added successfully');
    } catch (error) {
      console.error('Error adding follower:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to add follower');
    }
  };

  const handleRemoveFollower = async (userId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/followers/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to remove follower');
      }

      // Update the lists
      const userToRemove = followers.find(user => user.id === userId);
      if (userToRemove) {
        // Remove from followers list
        setFollowers(prev => prev.filter(user => user.id !== userId));
        // Add to non-followers list
        setNonFollowers(prev => [...prev, userToRemove]);
      }
      toast.success('Follower removed successfully');
    } catch (error) {
      console.error('Error removing follower:', error);
      toast.error('Failed to remove follower');
    }
  };

  const filteredFollowers = followers.filter(user =>
    (user.name?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
    (user.email?.toLowerCase() || '').includes(searchQuery.toLowerCase())
  );

  const filteredNonFollowers = nonFollowers.filter(user =>
    (user.name?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
    (user.email?.toLowerCase() || '').includes(searchQuery.toLowerCase())
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Project Followers</DialogTitle>
        </DialogHeader>
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            type="text"
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <div className="space-y-6">
          {/* Current Followers Section */}
          <div>
            <h3 className="text-sm font-medium mb-2">Current Followers ({followers.length})</h3>
            <div className="space-y-2">
              {isLoading ? (
                <div className="space-y-2">
                  <div className="h-12 bg-gray-100 animate-pulse rounded-lg" />
                  <div className="h-12 bg-gray-100 animate-pulse rounded-lg" />
                </div>
              ) : filteredFollowers.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-2">No followers found</p>
              ) : (
                filteredFollowers.map((follower) => (
                  <div
                    key={follower.id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        <AvatarImage src={follower.profile_image_url || '/default-avatar.png'} />
                        <AvatarFallback>{follower.name?.[0] || '?'}</AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="text-sm font-medium">{follower.name || 'Unknown User'}</p>
                        <p className="text-xs text-gray-500">{follower.email || 'No email'}</p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveFollower(follower.id)}
                    >
                      <X className="h-4 w-4 text-gray-500" />
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Non-Followers Section */}
          <div>
            <h3 className="text-sm font-medium mb-2">Add New Followers</h3>
            <div className="space-y-2">
              {isLoading ? (
                <div className="space-y-2">
                  <div className="h-12 bg-gray-100 animate-pulse rounded-lg" />
                  <div className="h-12 bg-gray-100 animate-pulse rounded-lg" />
                </div>
              ) : filteredNonFollowers.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-2">No users available to add</p>
              ) : (
                filteredNonFollowers.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        <AvatarImage src={user.profile_image_url || '/default-avatar.png'} />
                        <AvatarFallback>{user.name?.[0] || '?'}</AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="text-sm font-medium">{user.name || 'Unknown User'}</p>
                        <p className="text-xs text-gray-500">{user.email || 'No email'}</p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleAddFollower(user.id)}
                    >
                      <UserPlus className="h-4 w-4 text-gray-500" />
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
} 