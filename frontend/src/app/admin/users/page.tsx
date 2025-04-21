"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import { toast } from "react-hot-toast";
import { useRouter } from "next/navigation";

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

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token, user: currentUser } = useAuthStore();
  const router = useRouter();

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      console.log("Fetching users...");
      console.log("Current token:", token);
      console.log("Current user:", currentUser);
      
      if (!token) {
        throw new Error("No authentication token found");
      }

      if (!currentUser?.is_superuser) {
        throw new Error("User does not have admin privileges");
      }

      const response = await fetch("http://192.168.56.1:8003/users/", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      console.log("Response status:", response.status);
      console.log("Response headers:", Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Error response:", errorText);
        throw new Error(`Failed to fetch users: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log("Raw response data:", data);

      // Handle direct array response
      if (Array.isArray(data)) {
        const validatedUsers = data.map(user => {
          console.log("Processing user:", user);
          if (!user.id || !user.username || !user.email || !user.full_name) {
            console.error("Invalid user object:", user);
            throw new Error(`Invalid user data received. Missing required fields: ${JSON.stringify(user)}`);
          }
          return user;
        });

        console.log("Validated users:", validatedUsers);
        setUsers(validatedUsers);
      } else if (data.users && Array.isArray(data.users)) {
        // Handle paginated response
        const validatedUsers = data.users.map((user: User) => {
          console.log("Processing user:", user);
          if (!user.id || !user.username || !user.email || !user.full_name) {
            console.error("Invalid user object:", user);
            throw new Error(`Invalid user data received. Missing required fields: ${JSON.stringify(user)}`);
          }
          return user;
        });

        console.log("Validated users:", validatedUsers);
        setUsers(validatedUsers);
      } else {
        throw new Error("Invalid response format: expected users array in response");
      }
    } catch (error) {
      console.error("Error fetching users:", error);
      setError(error instanceof Error ? error.message : "Failed to load users");
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [token, currentUser]);

  useEffect(() => {
    if (!currentUser?.is_superuser) {
      router.push("/");
      return;
    }
    fetchUsers();
  }, [currentUser, router, fetchUsers]);

  const handleActivateUser = async (userId: number) => {
    try {
      const response = await fetch(`http://192.168.56.1:8003/users/${userId}/activate`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to activate user");
      }

      toast.success("User activated successfully");
      fetchUsers();
    } catch (error) {
      console.error("Error activating user:", error);
      toast.error("Failed to activate user");
    }
  };

  const handleDeactivateUser = async (userId: number) => {
    try {
      const response = await fetch(`http://192.168.56.1:8003/users/${userId}/deactivate`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to deactivate user");
      }

      toast.success("User deactivated successfully");
      fetchUsers();
    } catch (error) {
      console.error("Error deactivating user:", error);
      toast.error("Failed to deactivate user");
    }
  };

  const handleMakeAdmin = async (userId: number) => {
    try {
      const response = await fetch(`http://192.168.56.1:8003/users/${userId}/make-admin`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to make user admin");
      }

      toast.success("User granted admin privileges");
      fetchUsers();
    } catch (error) {
      console.error("Error making user admin:", error);
      toast.error("Failed to make user admin");
    }
  };

  const handleRemoveAdmin = async (userId: number) => {
    try {
      const response = await fetch(`http://192.168.56.1:8003/users/${userId}/remove-admin`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to remove admin privileges");
      }

      toast.success("Admin privileges removed");
      fetchUsers();
    } catch (error) {
      console.error("Error removing admin privileges:", error);
      toast.error("Failed to remove admin privileges");
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!window.confirm("Are you sure you want to delete this user?")) {
      return;
    }

    try {
      const response = await fetch(`http://192.168.56.1:8003/users/${userId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to delete user");
      }

      toast.success("User deleted successfully");
      fetchUsers();
    } catch (error) {
      console.error("Error deleting user:", error);
      toast.error("Failed to delete user");
    }
  };

  const handleEditUser = (userId: number) => {
    router.push(`/admin/users/${userId}/edit`);
  };

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <Button onClick={fetchUsers}>Retry</Button>
      </div>
    );
  }

  if (!users.length) {
    return (
      <div className="p-4">
        <div className="text-gray-500 mb-4">No users found</div>
        <Button onClick={fetchUsers}>Refresh</Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">User Management</h1>
        <Button onClick={() => router.push("/admin/users/create")}>
          Create New User
        </Button>
      </div>

      <div className="bg-white rounded-lg shadow">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Username</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Full Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell>{user.username}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>{user.full_name}</TableCell>
                <TableCell>
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${
                      user.is_active
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {user.is_active ? "Active" : "Inactive"}
                  </span>
                </TableCell>
                <TableCell>
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${
                      user.is_superuser
                        ? "bg-purple-100 text-purple-800"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {user.is_superuser ? "Admin" : "User"}
                  </span>
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="h-8 w-8 p-0">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => handleEditUser(user.id)}
                      >
                        Edit Profile
                      </DropdownMenuItem>
                      {!user.is_active && (
                        <DropdownMenuItem
                          onClick={() => handleActivateUser(user.id)}
                        >
                          Activate
                        </DropdownMenuItem>
                      )}
                      {user.is_active && (
                        <DropdownMenuItem
                          onClick={() => handleDeactivateUser(user.id)}
                        >
                          Deactivate
                        </DropdownMenuItem>
                      )}
                      {!user.is_superuser && (
                        <DropdownMenuItem
                          onClick={() => handleMakeAdmin(user.id)}
                        >
                          Make Admin
                        </DropdownMenuItem>
                      )}
                      {user.is_superuser && user.id !== currentUser?.id && (
                        <DropdownMenuItem
                          onClick={() => handleRemoveAdmin(user.id)}
                        >
                          Remove Admin
                        </DropdownMenuItem>
                      )}
                      {user.id !== currentUser?.id && (
                        <DropdownMenuItem
                          onClick={() => handleDeleteUser(user.id)}
                          className="text-red-600"
                        >
                          Delete
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
} 