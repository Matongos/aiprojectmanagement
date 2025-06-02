"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "react-hot-toast";
import React from "react";
import { fetchApi, putApi } from "@/lib/api-helper";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

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

export default function EditUserPage({ params }: { params: Promise<{ userId: string }> }) {
  // Unwrap params using React.use()
  const resolvedParams = React.use(params);
  const userId = resolvedParams.userId;
  
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
  const { user: currentUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!currentUser?.is_superuser) {
      router.push("/");
      return;
    }
    fetchUser();
  }, [currentUser, router, userId]);

  const fetchUser = async () => {
    if (!userId) {
      setError("User ID is required");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchApi<User>(`/users/${userId}`);
      setUser(data);
      setFormData(prev => ({
        ...prev,
        username: data.username,
        email: data.email,
        full_name: data.full_name,
        job_title: data.job_title || "",
        bio: data.bio || "",
        profession: data.profession || "",
        expertise: data.expertise || [],
        skills: data.skills || [],
        experience_level: data.experience_level || "",
        notes: data.notes || "",
        certifications: data.certifications || [],
        preferred_working_hours: data.preferred_working_hours || "",
        specializations: data.specializations || [],
        email_notifications_enabled: data.email_notifications_enabled || true,
      }));
    } catch (error) {
      console.error("Error fetching user:", error);
      setError(error instanceof Error ? error.message : "Failed to load user");
      toast.error("Failed to load user");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleArrayChange = (name: string, value: string[]) => {
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSelectChange = (name: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Prepare the update data
      const updateData: Record<string, any> = {
        username: formData.username,
        email: formData.email,
        full_name: formData.full_name,
        job_title: formData.job_title,
        bio: formData.bio,
        profession: formData.profession,
        expertise: formData.expertise,
        skills: formData.skills,
        experience_level: formData.experience_level,
        notes: formData.notes,
        certifications: formData.certifications,
        preferred_working_hours: formData.preferred_working_hours,
        specializations: formData.specializations,
        email_notifications_enabled: formData.email_notifications_enabled,
      };

      // If password fields are shown and filled, include password change
      if (showPasswordFields && formData.new_password) {
        if (formData.new_password !== formData.confirm_password) {
          throw new Error("New passwords do not match");
        }
        updateData.password = formData.new_password;
      }

      await putApi<User>(`/users/${userId}`, updateData);
      
      toast.success("User updated successfully");
      router.push("/admin/users");
    } catch (error) {
      console.error("Error updating user:", error);
      toast.error(error instanceof Error ? error.message : "Failed to update user");
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading user data...</div>;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <Button onClick={fetchUser}>Retry</Button>
      </div>
    );
  }

  if (!user) {
    return <div className="flex items-center justify-center h-screen">User not found</div>;
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
                    src={user.profile_image_url || '/placeholder-profile.svg'}
                    alt={`${user.full_name}'s profile`}
                  />
                  <AvatarFallback>{user.full_name.charAt(0).toUpperCase()}</AvatarFallback>
                </Avatar>
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-3xl font-bold">{user.full_name}</h1>
                  <Badge variant={user.is_active ? "default" : "destructive"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Badge variant="outline">
                    {user.is_superuser ? "Admin" : "User"}
                  </Badge>
                </div>
                <p className="text-muted-foreground mt-1">{user.email}</p>
                <p className="text-muted-foreground">{user.job_title || "No job title set"}</p>
              </div>
            </div>
            <Button variant="outline" onClick={() => router.push("/admin/users")}>
              Back to Users
            </Button>
          </div>
        </div>
        <Separator />
      </div>

      {/* Main Content */}
      <ScrollArea className="container h-[calc(100vh-12rem)]">
        <Tabs defaultValue="basic" className="space-y-6">
          <TabsList className="bg-background sticky top-0 z-10">
            <TabsTrigger value="basic">Basic Info</TabsTrigger>
            <TabsTrigger value="professional">Professional</TabsTrigger>
            <TabsTrigger value="skills">Skills & Expertise</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Basic Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
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
                  <div className="col-span-2">
            <Label htmlFor="full_name">Full Name</Label>
            <Input
              id="full_name"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              required
            />
          </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="professional" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Professional Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
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
                      onValueChange={(value) => handleSelectChange('experience_level', value)}
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
          <div>
                    <Label htmlFor="preferred_working_hours">Working Hours</Label>
                    <Input
                      id="preferred_working_hours"
                      name="preferred_working_hours"
                      value={formData.preferred_working_hours}
                      onChange={handleChange}
                      placeholder="e.g., 9 AM - 5 PM EST"
                    />
                  </div>
                  <div className="col-span-2">
            <Label htmlFor="bio">Bio</Label>
            <Input
              id="bio"
              name="bio"
              value={formData.bio}
              onChange={handleChange}
            />
          </div>
                  <div className="col-span-2">
                    <Label htmlFor="notes">Notes</Label>
                    <Input
                      id="notes"
                      name="notes"
                      value={formData.notes}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="skills" className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Skills & Expertise</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <ArrayInput
                    label="Skills"
                    value={formData.skills}
                    onChange={(newValue) => handleArrayChange('skills', newValue)}
                    placeholder="Add a skill"
                  />
                  <ArrayInput
                    label="Areas of Expertise"
                    value={formData.expertise}
                    onChange={(newValue) => handleArrayChange('expertise', newValue)}
                    placeholder="Add an area of expertise"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Certifications & Specializations</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <ArrayInput
                    label="Certifications"
                    value={formData.certifications}
                    onChange={(newValue) => handleArrayChange('certifications', newValue)}
                    placeholder="Add a certification"
                  />
                  <ArrayInput
                    label="Specializations"
                    value={formData.specializations}
                    onChange={(newValue) => handleArrayChange('specializations', newValue)}
                    placeholder="Add a specialization"
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="security" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Security Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">Password Management</h4>
                      <p className="text-sm text-muted-foreground">
                        Update the user's password
                      </p>
                    </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowPasswordFields(!showPasswordFields)}
              >
                      {showPasswordFields ? "Cancel" : "Change Password"}
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

                  <Separator className="my-6" />

                  <div className="space-y-4">
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
                  </div>
          </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Save Changes Button */}
        <div className="sticky bottom-0 bg-background py-6 border-t mt-6">
          <div className="container flex justify-end gap-4">
            <Button variant="outline" onClick={() => router.push("/admin/users")}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              Save Changes
            </Button>
          </div>
      </div>
      </ScrollArea>
    </div>
  );
} 