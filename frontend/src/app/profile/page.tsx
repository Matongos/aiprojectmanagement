'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import Image from 'next/image';
import { toast } from 'react-hot-toast';

// Form validation schema
const profileSchema = z.object({
  email: z.string().email().optional(),
  username: z.string().min(3).optional(),
  full_name: z.string().min(2).optional(),
  password: z.string().min(8).optional(),
  current_password: z.string().min(8).optional(),
  profile_image_url: z.string().url().optional(),
  job_title: z.string().optional(),
  bio: z.string().optional(),
  is_active: z.boolean().optional(),
  is_superuser: z.boolean().optional(),
}).refine((data) => {
  if (data.password && !data.current_password) {
    return false;
  }
  return true;
}, {
  message: "Current password is required when changing password",
  path: ["current_password"]
});

type ProfileFormData = z.infer<typeof profileSchema>;

export default function ProfilePage() {
  const router = useRouter();
  const { user, updateProfile, isLoading, error } = useAuthStore();
  const [showNotification, setShowNotification] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState('');
  const [notificationType, setNotificationType] = useState<'success' | 'error'>('success');
  
  // Initialize form with current user data
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      email: user?.email,
      username: user?.username,
      full_name: user?.full_name,
      profile_image_url: user?.profile_image_url || '',
      job_title: user?.job_title || '',
      bio: user?.bio || '',
      is_active: user?.is_active,
      is_superuser: user?.is_superuser,
    },
  });

  // Update form when user data changes
  useEffect(() => {
    if (user) {
      reset({
        email: user.email,
        username: user.username,
        full_name: user.full_name,
        profile_image_url: user.profile_image_url || '',
        job_title: user.job_title || '',
        bio: user.bio || '',
        is_active: user.is_active,
        is_superuser: user.is_superuser,
      });
    }
  }, [user, reset]);

  useEffect(() => {
    if (error) {
      setNotificationMessage(error);
      setNotificationType('error');
      setShowNotification(true);
      setTimeout(() => setShowNotification(false), 3000);
    }
  }, [error]);

  // Handle form submission
  const onSubmit = async (data: ProfileFormData) => {
    try {
      // Remove empty string values
      const profileData: Partial<ProfileFormData> = Object.fromEntries(
        Object.entries(data).filter(([, value]) => 
          value !== undefined && value !== '' && value !== null
        )
      );
      
      // If password is being changed, ensure current_password is provided
      if (profileData.password) {
        if (!profileData.current_password) {
          setNotificationMessage("Current password is required to change password");
          setNotificationType('error');
          setShowNotification(true);
          setTimeout(() => setShowNotification(false), 3000);
          return;
        }
        // Rename password to new_password for the API
        const updatedProfileData = {
          ...profileData,
          new_password: profileData.password
        };
        delete updatedProfileData.password;
        await updateProfile(updatedProfileData);
      } else {
        // Remove password fields if not changing password
        delete profileData.password;
        delete profileData.current_password;
        await updateProfile(profileData);
      }
      
      setNotificationMessage('Profile updated successfully!');
      setNotificationType('success');
      setShowNotification(true);
      setTimeout(() => setShowNotification(false), 3000);
      
      // Clear password fields after successful update
      reset({
        ...data,
        password: '',
        current_password: '',
      });
    } catch (error) {
      console.error('Profile update error:', error);
      setNotificationMessage('Failed to update profile. Please try again.');
      setNotificationType('error');
      setShowNotification(true);
      setTimeout(() => setShowNotification(false), 3000);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Please log in to view your profile</h1>
          <button
            onClick={() => router.push('/auth/login')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      {showNotification && (
        <div className={`fixed top-4 right-4 p-4 rounded-md shadow-lg ${
          notificationType === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white`}>
          {notificationMessage}
        </div>
      )}
      
      <div className="max-w-3xl mx-auto">
        {/* Current Profile Information */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Current Profile Information</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {user.profile_image_url && (
              <div className="col-span-2">
                <div className="relative h-32 w-32 mx-auto">
                  <Image
                    src={user.profile_image_url}
                    alt={`${user.full_name}'s profile`}
                    fill
                    className="rounded-full object-cover"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = '/default-avatar.png'; // Make sure to add a default avatar image
                    }}
                  />
                </div>
              </div>
            )}
            <div>
              <p className="text-sm font-medium text-gray-500">Full Name</p>
              <p className="mt-1 text-sm text-gray-900">{user.full_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Username</p>
              <p className="mt-1 text-sm text-gray-900">{user.username}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Email</p>
              <p className="mt-1 text-sm text-gray-900">{user.email}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Job Title</p>
              <p className="mt-1 text-sm text-gray-900">{user.job_title && user.job_title.trim() ? user.job_title : 'Not set'}</p>
            </div>
            <div className="col-span-2">
              <p className="text-sm font-medium text-gray-500">Bio</p>
              <p className="mt-1 text-sm text-gray-900">{user.bio && user.bio.trim() ? user.bio : 'Not set'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Account Status</p>
              <p className={`mt-1 text-sm ${
                user.is_active ? 'text-green-600' : 'text-red-600'
              }`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Role</p>
              <p className={`mt-1 text-sm ${
                user.is_superuser ? 'text-purple-600' : 'text-blue-600'
              }`}>
                {user.is_superuser ? 'Administrator' : 'User'}
              </p>
            </div>
          </div>
        </div>

        {/* Edit Profile Form */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Edit Profile</h2>
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email
                </label>
                <input
                  type="email"
                  id="email"
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  {...register('email')}
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
                )}
              </div>
              
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                  Username
                </label>
                <input
                  type="text"
                  id="username"
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  {...register('username')}
                />
                {errors.username && (
                  <p className="mt-1 text-sm text-red-600">{errors.username.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                  Full Name
                </label>
                <input
                  type="text"
                  id="full_name"
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  {...register('full_name')}
                />
                {errors.full_name && (
                  <p className="mt-1 text-sm text-red-600">{errors.full_name.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="job_title" className="block text-sm font-medium text-gray-700">
                  Job Title
                </label>
                <input
                  type="text"
                  id="job_title"
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  {...register('job_title')}
                />
                {errors.job_title && (
                  <p className="mt-1 text-sm text-red-600">{errors.job_title.message}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="profile_image_url" className="block text-sm font-medium text-gray-700">
                Profile Image URL
              </label>
              <input
                type="url"
                id="profile_image_url"
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                {...register('profile_image_url')}
              />
              {errors.profile_image_url && (
                <p className="mt-1 text-sm text-red-600">{errors.profile_image_url.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="bio" className="block text-sm font-medium text-gray-700">
                Bio
              </label>
              <textarea
                id="bio"
                rows={3}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                {...register('bio')}
              />
              {errors.bio && (
                <p className="mt-1 text-sm text-red-600">{errors.bio.message}</p>
              )}
            </div>

            <div className="border-t border-gray-200 pt-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Change Password</h3>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label htmlFor="current_password" className="block text-sm font-medium text-gray-700">
                    Current Password
                  </label>
                  <input
                    type="password"
                    id="current_password"
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    {...register('current_password')}
                  />
                  {errors.current_password && (
                    <p className="mt-1 text-sm text-red-600">{errors.current_password.message}</p>
                  )}
                </div>
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    New Password
                  </label>
                  <input
                    type="password"
                    id="password"
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    {...register('password')}
                  />
                  {errors.password && (
                    <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
                  )}
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                disabled={isLoading}
              >
                {isLoading ? 'Updating...' : 'Update Profile'}
              </button>
            </div>
          </form>
        </div>

        {/* Delete Account Section */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h2 className="text-xl font-bold text-red-600 mb-4">Delete Account</h2>
          <p className="text-gray-600 mb-4">
            Warning: This action cannot be undone. All your data will be permanently deleted.
          </p>
          <button
            onClick={() => {
              if (window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
                // Call the delete account function from auth store
                fetch('http://localhost:8003/users/me', {
                  method: 'DELETE',
                  headers: {
                    'Authorization': `Bearer ${user?.access_token}`
                  }
                })
                .then(response => {
                  if (response.ok) {
                    toast.success('Account deleted successfully');
                    router.push('/auth/login');
                  } else {
                    toast.error('Failed to delete account');
                  }
                })
                .catch(error => {
                  console.error('Error deleting account:', error);
                  toast.error('Failed to delete account');
                });
              }
            }}
            className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Delete Account
          </button>
        </div>

        {/* Admin Section - Only visible to superusers */}
        {user?.is_superuser && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Admin Actions</h2>
            <p className="text-gray-600 mb-4">
              As an administrator, you can manage other users through the admin dashboard.
            </p>
            <button
              onClick={() => router.push('/admin/users')}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              Manage Users
            </button>
          </div>
        )}
      </div>
    </div>
  );
} 