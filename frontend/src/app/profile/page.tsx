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
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

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
  profession?: string;
  expertise?: string[];
  skills?: string[];
  experience_level?: string;
  notes?: string;
  certifications?: string[];
  preferred_working_hours?: string;
  specializations?: string[];
  created_at: string;
  updated_at?: string;
  email_notifications_enabled?: boolean;
}

interface ArrayInputProps {
  label: string;
  value: string[];
  onChange: (newValue: string[]) => void;
  placeholder?: string;
}

function ArrayInput({ label, value, onChange, placeholder }: ArrayInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleAdd = () => {
    if (inputValue.trim()) {
      onChange([...value, inputValue.trim()]);
      setInputValue("");
    }
  };

  const handleRemove = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={placeholder}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAdd();
            }
          }}
        />
        <Button type="button" onClick={handleAdd}>Add</Button>
      </div>
      <div className="flex flex-wrap gap-2 mt-2">
        {value.map((item, index) => (
          <Badge
            key={index}
            variant="secondary"
            className="cursor-pointer"
            onClick={() => handleRemove(index)}
          >
            {item} ×
          </Badge>
        ))}
      </div>
    </div>
  );
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
    profession: "",
    expertise: [] as string[],
    skills: [] as string[],
    experience_level: "",
    notes: "",
    certifications: [] as string[],
    preferred_working_hours: "",
    specializations: [] as string[],
    email_notifications_enabled: true,
  });
  const [showPasswordFields, setShowPasswordFields] = useState(false);
  const router = useRouter();
  const { token, user: authUser } = useAuthStore();

  // Add this type assertion after getting authUser
  const typedAuthUser = authUser as unknown as User;

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
      
      // Then update the authUser references to use typedAuthUser:
      if (authUser) {
        console.log("Using user from auth store:", authUser);
        // Initialize with data from auth store while we fetch the full profile
        setUser(typedAuthUser);
        setFormData(prev => ({
          ...prev,
          username: typedAuthUser.username || "",
          email: typedAuthUser.email || "",
          full_name: typedAuthUser.full_name || "",
          job_title: typedAuthUser.job_title || "",
          bio: typedAuthUser.bio || "",
          profession: typedAuthUser.profession || "",
          expertise: typedAuthUser.expertise || [],
          skills: typedAuthUser.skills || [],
          experience_level: typedAuthUser.experience_level || "",
          notes: typedAuthUser.notes || "",
          certifications: typedAuthUser.certifications || [],
          preferred_working_hours: typedAuthUser.preferred_working_hours || "",
          specializations: typedAuthUser.specializations || [],
          email_notifications_enabled: typedAuthUser.email_notifications_enabled || true,
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
        profession: userData.profession || "",
        expertise: userData.expertise || [],
        skills: userData.skills || [],
        experience_level: userData.experience_level || "",
        notes: userData.notes || "",
        certifications: userData.certifications || [],
        preferred_working_hours: userData.preferred_working_hours || "",
        specializations: userData.specializations || [],
        email_notifications_enabled: userData.email_notifications_enabled || true,
      }));
    } catch (error) {
      console.error("Error fetching user:", error);
      setError(error instanceof Error ? error.message : "Failed to load user");
      toast.error("Failed to load user profile data");
      
      // Set mock data if API fails
      if (!user && authUser) {
        const mockUser = {
          id: typeof authUser.id === 'string' ? parseInt(authUser.id, 10) : (authUser.id || 1),
          username: typedAuthUser.username || "user",
          email: typedAuthUser.email || "user@example.com",
          full_name: typedAuthUser.full_name || "User Name",
          is_active: true,
          is_superuser: typedAuthUser.is_superuser || false,
          profile_image_url: typedAuthUser.profile_image_url,
          job_title: typedAuthUser.job_title || "Developer",
          bio: typedAuthUser.bio || "No bio available",
          profession: typedAuthUser.profession || "",
          expertise: typedAuthUser.expertise || [],
          skills: typedAuthUser.skills || [],
          experience_level: typedAuthUser.experience_level || "",
          notes: typedAuthUser.notes || "",
          certifications: typedAuthUser.certifications || [],
          preferred_working_hours: typedAuthUser.preferred_working_hours || "",
          specializations: typedAuthUser.specializations || [],
          email_notifications_enabled: typedAuthUser.email_notifications_enabled || true,
          created_at: new Date().toISOString(),
        };
        setUser(mockUser);
        setFormData(prev => ({
          ...prev,
          username: mockUser.username,
          email: mockUser.email,
          full_name: mockUser.full_name,
          job_title: mockUser.job_title || "",
          bio: mockUser.bio || "",
          profession: mockUser.profession || "",
          expertise: mockUser.expertise || [],
          skills: mockUser.skills || [],
          experience_level: mockUser.experience_level || "",
          notes: mockUser.notes || "",
          certifications: mockUser.certifications || [],
          preferred_working_hours: mockUser.preferred_working_hours || "",
          specializations: mockUser.specializations || [],
          email_notifications_enabled: mockUser.email_notifications_enabled || true,
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
        profession: formData.profession,
        experience_level: formData.experience_level,
        notes: formData.notes,
        email_notifications_enabled: formData.email_notifications_enabled ? "true" : "false",
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
    <div className="h-full space-y-8 overflow-hidden">
      {/* Header Section */}
      <div className="bg-background sticky top-0 z-10">
        <div className="container py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
            <div className="relative">
                <Avatar className="h-24 w-24">
                <AvatarImage 
                  src={user.profile_image_url ? (
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
                  className="absolute bottom-0 right-0 bg-primary text-primary-foreground rounded-full p-2 cursor-pointer hover:bg-primary/90 shadow-md transition-colors"
              >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
                <h1 className="text-3xl font-bold">{user.full_name}</h1>
                <p className="text-muted-foreground">{user.job_title || "No job title set"}</p>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant={user.is_active ? "default" : "destructive"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Badge variant="outline">
                    {user.is_superuser ? "Admin" : "User"}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
        <Separator />
      </div>

      {/* Main Content */}
      <ScrollArea className="container h-[calc(100vh-12rem)]">
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList>
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="expertise">Expertise</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
            <TabsTrigger value="account">Account</TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Basic Information */}
          <Card>
            <CardHeader>
                  <CardTitle>Basic Information</CardTitle>
            </CardHeader>
                <CardContent className="space-y-4">
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
                </CardContent>
              </Card>

              {/* Professional Information */}
              <Card>
                <CardHeader>
                  <CardTitle>Professional Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
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
                    <Label htmlFor="profession">Profession</Label>
                    <Input
                      id="profession"
                      name="profession"
                      value={formData.profession}
                      onChange={handleChange}
                    />
                  </div>
                  <div>
                    <Label htmlFor="experience_level">Experience Level</Label>
                    <Select
                      value={formData.experience_level}
                      onValueChange={(value) => setFormData(prev => ({ ...prev, experience_level: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select experience level" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="junior">Junior</SelectItem>
                        <SelectItem value="mid">Mid-Level</SelectItem>
                        <SelectItem value="senior">Senior</SelectItem>
                        <SelectItem value="expert">Expert</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="expertise" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Skills and Expertise */}
              <Card>
                <CardHeader>
                  <CardTitle>Skills & Expertise</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <ArrayInput
                    label="Skills"
                    value={formData.skills}
                    onChange={(newValue) => setFormData(prev => ({ ...prev, skills: newValue }))}
                    placeholder="Add a skill"
                  />
                  <ArrayInput
                    label="Areas of Expertise"
                    value={formData.expertise}
                    onChange={(newValue) => setFormData(prev => ({ ...prev, expertise: newValue }))}
                    placeholder="Add an area of expertise"
                  />
                </CardContent>
              </Card>

              {/* Certifications and Specializations */}
              <Card>
                <CardHeader>
                  <CardTitle>Certifications & Specializations</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <ArrayInput
                    label="Certifications"
                    value={formData.certifications}
                    onChange={(newValue) => setFormData(prev => ({ ...prev, certifications: newValue }))}
                    placeholder="Add a certification"
                  />
                  <ArrayInput
                    label="Specializations"
                    value={formData.specializations}
                    onChange={(newValue) => setFormData(prev => ({ ...prev, specializations: newValue }))}
                    placeholder="Add a specialization"
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="settings" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Additional Information */}
              <Card>
                <CardHeader>
                  <CardTitle>Additional Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="bio">Bio</Label>
                  <Input
                    id="bio"
                    name="bio"
                    value={formData.bio}
                    onChange={handleChange}
                  />
                </div>
                  <div>
                    <Label htmlFor="notes">Notes</Label>
                    <Input
                      id="notes"
                      name="notes"
                      value={formData.notes}
                      onChange={handleChange}
                    />
                  </div>
                  <div>
                    <Label htmlFor="preferred_working_hours">Preferred Working Hours</Label>
                    <Input
                      id="preferred_working_hours"
                      name="preferred_working_hours"
                      value={formData.preferred_working_hours}
                      onChange={handleChange}
                      placeholder="e.g., 9 AM - 5 PM EST"
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="email_notifications_enabled"
                      checked={formData.email_notifications_enabled}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        email_notifications_enabled: e.target.checked
                      }))}
                      className="h-4 w-4"
                    />
                    <Label htmlFor="email_notifications_enabled">Enable Email Notifications</Label>
                  </div>
                </CardContent>
              </Card>

              {/* Password Change */}
              <Card>
                <CardHeader>
                  <CardTitle>Password Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">Change Password</h4>
                      <p className="text-sm text-muted-foreground">
                        Update your password to keep your account secure
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowPasswordFields(!showPasswordFields)}
                    >
                      {showPasswordFields ? "Cancel" : "Change"}
                    </Button>
                  </div>

                  {showPasswordFields && (
                    <div className="space-y-4 pt-4">
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
            </CardContent>
          </Card>
            </div>
          </TabsContent>

          <TabsContent value="account" className="space-y-6">
          <Card>
            <CardHeader>
                <CardTitle>Account Management</CardTitle>
            </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
              <div>
                    <h4 className="text-sm font-medium mb-2">Account Status</h4>
                    <Badge variant={user.is_active ? "default" : "destructive"}>
                    {user.is_active ? "Active" : "Inactive"}
                    </Badge>
              </div>

              <div>
                    <h4 className="text-sm font-medium mb-2">Account Role</h4>
                    <Badge variant="outline">
                      {user.is_superuser ? "Administrator" : "Regular User"}
                    </Badge>
              </div>

              <div>
                    <h4 className="text-sm font-medium mb-2">Member Since</h4>
                    <p className="text-sm text-muted-foreground">
                      {new Date(user.created_at).toLocaleDateString()}
                    </p>
              </div>

                  <Separator className="my-6" />

                  <div className="space-y-4">
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
              </div>
            </CardContent>
          </Card>
          </TabsContent>
        </Tabs>

        {/* Save Changes Button */}
        <div className="sticky bottom-0 bg-background py-6 border-t mt-6">
          <div className="container flex justify-end">
            <Button type="submit" onClick={handleSubmit}>
              Save Changes
            </Button>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
} 