"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "react-hot-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { API_BASE_URL } from "@/lib/constants";
import AuthWrapper from "@/components/AuthWrapper";
import { fetchApi, patchApi, deleteApi } from "@/lib/api-helper";

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  profile_image_url?: string;
  job_title?: string;
  bio?: string;
}

export default function ProfilePage() {
  return (
    <AuthWrapper>
      <ProfileContent />
    </AuthWrapper>
  );
}

function ProfileContent() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    full_name: "",
    job_title: "",
    bio: "",
    new_password: "",
    confirm_password: "",
  });
  const [showPasswordFields, setShowPasswordFields] = useState(false);
  const router = useRouter();
  const { token, user: authUser } = useAuthStore();

  useEffect(() => {
    // Check if user is authenticated before making API calls
    if (!token) {
      console.log("No authentication token found, redirecting to login");
      router.push("/auth/login");
      return;
    }
    
    fetchUser();
  }, [token, router]);

  const fetchUser = async () => {
    if (!token) {
      console.error("Token not available, cannot fetch user data");
      router.push("/auth/login");
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // Use authUser from store if available
      if (authUser) {
        console.log("Using user from auth store:", authUser);
        // Initialize with data from auth store while we fetch the full profile
        setUser(authUser as unknown as User);
        setFormData(prev => ({
          ...prev,
          username: authUser.username || "",
          email: authUser.email || "",
          full_name: authUser.full_name || "",
          job_title: authUser.job_title || "",
          bio: authUser.bio || "",
        }));
      }
      
      // First get current user from /me endpoint
      const currentUser = await fetchApi<User>('/users/me', {}, false);
      console.log("Fetched current user:", currentUser);
      
      if (!currentUser || !currentUser.id) {
        throw new Error("Could not determine user ID");
      }
      
      console.log("Fetching user data for ID:", currentUser.id);
      
      // Then get detailed user information
      const userData = await fetchApi<User>(`/users/${currentUser.id}`, {}, false);
      console.log("User data received:", userData);
      
      setUser(userData);
      setFormData(prev => ({
        ...prev,
        username: userData.username,
        email: userData.email,
        full_name: userData.full_name,
        job_title: userData.job_title || "",
        bio: userData.bio || "",
      }));
    } catch (error) {
      console.error("Error fetching user:", error);
      setError(error instanceof Error ? error.message : "Failed to load user");
      toast.error("Failed to load user profile data");
      
      // Set mock data if API fails
      if (!user && authUser) {
        const mockUser = {
          id: typeof authUser.id === 'string' ? parseInt(authUser.id, 10) : (authUser.id || 1),
          username: authUser.username || "user",
          email: authUser.email || "user@example.com",
          full_name: authUser.full_name || "User Name",
          is_active: true,
          is_superuser: authUser.is_superuser || false,
          profile_image_url: authUser.profile_image_url,
          job_title: authUser.job_title || "Developer",
          bio: authUser.bio || "No bio available"
        };
        setUser(mockUser as User);
        setFormData(prev => ({
          ...prev,
          username: mockUser.username,
          email: mockUser.email,
          full_name: mockUser.full_name,
          job_title: mockUser.job_title || "",
          bio: mockUser.bio || "",
        }));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (!user?.id) {
        throw new Error("User ID not found");
      }

      // Prepare the update data
      const updateData: Record<string, string> = {
        username: formData.username,
        email: formData.email,
        full_name: formData.full_name,
        job_title: formData.job_title,
        bio: formData.bio,
      };

      // If password fields are shown and filled, include password change
      if (showPasswordFields && formData.new_password) {
        if (formData.new_password !== formData.confirm_password) {
          throw new Error("New passwords do not match");
        }
        updateData.password = formData.new_password;
      }

      console.log("Updating user profile with data:", updateData);

      await patchApi('/users/me/profile', updateData);
      
      toast.success("Profile updated successfully");
      fetchUser();
    } catch (error) {
      console.error("Error updating user:", error);
      toast.error(error instanceof Error ? error.message : "Failed to update user");
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
      return;
    }

    try {
      if (!user?.id) {
        throw new Error("User ID not found");
      }
      
      await deleteApi(`/users/${user.id}`);
      toast.success("Account deleted successfully");
      
      // Log out and redirect
      const { logout } = useAuthStore.getState();
      logout();
      router.push("/auth/login");
    } catch (error) {
      console.error("Error deleting account:", error);
      toast.error("Failed to delete account");
    }
  };

  const handleManageUsers = () => {
    router.push("/admin/users");
  };

  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      
      try {
        const formData = new FormData();
        formData.append('profile_image', file);

        const storedToken = localStorage.getItem('token');
        if (!storedToken) {
          throw new Error("No authentication token found");
        }

        // File upload requires a direct fetch with FormData
        const response = await fetch(`${API_BASE_URL}/users/me/profile-image`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
          body: formData,
        });

        if (!response.ok) {
          throw new Error('Failed to upload image');
        }

        toast.success('Profile image updated successfully');
        fetchUser(); // Refresh user data to get the new image URL
      } catch (error) {
        console.error('Error uploading image:', error);
        toast.error('Failed to upload image');
      }
    }
  };

  if (loading) {
    return <div className="p-4">Loading profile data...</div>;
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <Button onClick={fetchUser}>Retry</Button>
      </div>
    );
  }

  if (!user) {
    return <div className="p-4">User not found</div>;
  }

  return (
    <div className="container mx-auto py-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Avatar className="h-20 w-20">
                <AvatarImage 
                  src={user.profile_image_url ? (
                    // Check if it's a valid URL
                    user.profile_image_url.startsWith('http') || 
                    user.profile_image_url.startsWith('/') || 
                    user.profile_image_url.startsWith('data:') 
                      ? user.profile_image_url 
                      : '/placeholder-profile.svg'
                  ) : '/placeholder-profile.svg'}
                  alt={`${user.full_name}'s profile`}
                  onError={(e) => {
                    console.error("Error loading profile image, falling back to placeholder");
                    (e.target as HTMLImageElement).src = '/placeholder-profile.svg';
                  }}
                />
                <AvatarFallback>{user.full_name.charAt(0).toUpperCase()}</AvatarFallback>
              </Avatar>
              <label 
                htmlFor="profile-image" 
                className="absolute bottom-0 right-0 bg-blue-500 text-white rounded-full p-1 cursor-pointer hover:bg-blue-600"
                style={{ width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <input
                  id="profile-image"
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageChange}
                />
              </label>
            </div>
            <div>
              <h1 className="text-2xl font-bold">{user.full_name}</h1>
              <p className="text-gray-500">{user.job_title || "No job title"}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="job_title">Job Title</Label>
                  <Input
                    id="job_title"
                    name="job_title"
                    value={formData.job_title}
                    onChange={handleChange}
                  />
                </div>

                <div>
                  <Label htmlFor="bio">Bio</Label>
                  <Input
                    id="bio"
                    name="bio"
                    value={formData.bio}
                    onChange={handleChange}
                  />
                </div>

                <div className="pt-4 border-t">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Change Password</h2>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowPasswordFields(!showPasswordFields)}
                    >
                      {showPasswordFields ? "Cancel Password Change" : "Change Password"}
                    </Button>
                  </div>

                  {showPasswordFields && (
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="new_password">New Password</Label>
                        <Input
                          id="new_password"
                          name="new_password"
                          type="password"
                          value={formData.new_password}
                          onChange={handleChange}
                          required={showPasswordFields}
                        />
                      </div>

                      <div>
                        <Label htmlFor="confirm_password">Confirm New Password</Label>
                        <Input
                          id="confirm_password"
                          name="confirm_password"
                          type="password"
                          value={formData.confirm_password}
                          onChange={handleChange}
                          required={showPasswordFields}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex justify-end space-x-4">
                  <Button type="submit">Save Changes</Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Account Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Account Status</Label>
                <div className="mt-1">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    user.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                  }`}>
                    {user.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>

              <div>
                <Label>Role</Label>
                <div className="mt-1">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    user.is_superuser ? "bg-purple-100 text-purple-800" : "bg-gray-100 text-gray-800"
                  }`}>
                    {user.is_superuser ? "Admin" : "User"}
                  </span>
                </div>
              </div>

              <div>
                <Label>Member Since</Label>
                <div className="mt-1 text-sm text-gray-600">
                  {new Date().toLocaleDateString()}
                </div>
              </div>

              <div className="pt-4 space-y-2">
                {user.is_superuser && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={handleManageUsers}
                  >
                    Manage Users
                  </Button>
                )}
                <Button
                  variant="destructive"
                  className="w-full"
                  onClick={handleDeleteAccount}
                >
                  Delete Account
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
} 