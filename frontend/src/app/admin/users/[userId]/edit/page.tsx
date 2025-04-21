"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "react-hot-toast";

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

export default function EditUserPage({ params }: { params: { userId: string } }) {
  const userId = params.userId;
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
  const { token, user: currentUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!currentUser?.is_superuser) {
      router.push("/");
      return;
    }
    fetchUser();
  }, [currentUser, router, userId]);

  const fetchUser = async () => {
    try {
      setLoading(true);
      setError(null);
      
      if (!token) {
        throw new Error("No authentication token found");
      }

      const response = await fetch(`http://192.168.56.1:8003/users/${userId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch user: ${response.status}`);
      }

      const data = await response.json();
      setUser(data);
      setFormData(prev => ({
        ...prev,
        username: data.username,
        email: data.email,
        full_name: data.full_name,
        job_title: data.job_title || "",
        bio: data.bio || "",
      }));
    } catch (error) {
      console.error("Error fetching user:", error);
      setError(error instanceof Error ? error.message : "Failed to load user");
      toast.error("Failed to load user");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (!token) {
        throw new Error("No authentication token found");
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

      const response = await fetch(`http://192.168.56.1:8003/users/${userId}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update user");
      }

      toast.success("User updated successfully");
      router.push("/admin/users");
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

  if (loading) {
    return <div className="p-4">Loading...</div>;
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
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Edit User Profile</h1>
        
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
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/admin/users")}
            >
              Cancel
            </Button>
            <Button type="submit">Save Changes</Button>
          </div>
        </form>
      </div>
    </div>
  );
} 