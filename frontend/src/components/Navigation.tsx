'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Bell, MessageSquare, User, LogOut } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useRouter } from 'next/navigation';
import { useEffect, useState, ReactNode } from 'react';
import Image from 'next/image';

// Custom Link component that renders consistently between server and client
interface LinkComponentProps {
  href: string;
  className: string;
  children: ReactNode;
}

const LinkComponent = ({ href, className, children }: LinkComponentProps) => {
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
};

export default function Navigation() {
  const { user, isAuthenticated, logout } = useAuthStore();
  const pathname = usePathname();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  
  const isAdmin = user?.is_superuser === true;

  // Only run on client to prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/auth/login');
  };

  // If not mounted yet, render a skeleton version that matches server output
  if (!mounted) {
    return (
      <nav className="bg-black text-white shadow-lg">
        <div className="max-w-full mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <div className="relative h-8 w-8 mr-2">
                <Image 
                  src="/logo.png" 
                  alt="ZINGSA Logo" 
                  width={32} 
                  height={32} 
                  className="w-full h-full object-contain" 
                  priority 
                />
              </div>
              <Link href="/" className="text-xl font-semibold text-white hover:text-gray-200">
                ZINGSA PROJECT MANAGEMENT
              </Link>
            </div>
            <div className="hidden md:flex items-center space-x-6">
              {/* Empty space for nav links */}
            </div>
            <div className="md:hidden flex items-center space-x-2">
              {/* Empty space for mobile menu */}
            </div>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="bg-black text-white shadow-lg">
      <div className="max-w-full mx-auto px-4">
        <div className="flex justify-between h-16">
          {/* Left side - Logo/Brand */}
          <div className="flex items-center">
            <div className="relative h-8 w-8 mr-2">
              <Image 
                src="/logo.png" 
                alt="ZINGSA Logo" 
                width={32} 
                height={32} 
                className="w-full h-full object-contain" 
                priority 
              />
            </div>
            <Link href="/" className="text-xl font-semibold text-white hover:text-gray-200">
              ZINGSA PROJECT MANAGEMENT
            </Link>
          </div>
          
          {/* Center - Main navigation links */}
          {isAuthenticated && (
            <div className="hidden md:flex items-center space-x-6">
              <LinkComponent
                href="/dashboard"
                className={`px-3 py-2 text-sm font-medium ${
                  pathname === '/dashboard' 
                    ? 'border-b-2 border-white text-white' 
                    : 'text-gray-300 hover:text-white hover:border-b-2 hover:border-white'
                }`}
              >
                Dashboard
              </LinkComponent>
              
              <LinkComponent
                href="/dashboard/projects"
                className={`px-3 py-2 text-sm font-medium ${
                  pathname?.startsWith('/dashboard/projects') 
                    ? 'border-b-2 border-white text-white' 
                    : 'text-gray-300 hover:text-white hover:border-b-2 hover:border-white'
                }`}
              >
                Projects
              </LinkComponent>
              
              <LinkComponent
                href="/dashboard/tasks"
                className={`px-3 py-2 text-sm font-medium ${
                  pathname?.startsWith('/dashboard/tasks') 
                    ? 'border-b-2 border-white text-white' 
                    : 'text-gray-300 hover:text-white hover:border-b-2 hover:border-white'
                }`}
              >
                Tasks
              </LinkComponent>
              
              {/* Temporarily disabled until reporting is implemented */}
              <span
                className={`px-3 py-2 text-sm font-medium text-gray-500 cursor-not-allowed`}
                title="Coming soon"
              >
                Reporting (Coming Soon)
              </span>
              
              {/* Admin link only for admins */}
              {isAdmin && (
                <LinkComponent
                  href="/admin/users"
                  className={`px-3 py-2 text-sm font-medium ${
                    pathname?.startsWith('/admin') 
                      ? 'border-b-2 border-white text-white' 
                      : 'text-gray-300 hover:text-white hover:border-b-2 hover:border-white'
                  }`}
                >
                  Admin
                </LinkComponent>
              )}
            </div>
          )}
          
          {/* Right side - User info and actions */}
          <div className="hidden md:flex items-center space-x-6">
            {isAuthenticated ? (
              <>
                {/* Notification Icon */}
                <button className="text-gray-300 hover:text-white">
                  <Bell className="h-5 w-5" />
                </button>
                
                {/* Messages Icon */}
                <button className="text-gray-300 hover:text-white">
                  <MessageSquare className="h-5 w-5" />
                </button>
                
                {/* User Profile Dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger className="focus:outline-none">
                    <div className="flex items-center hover:text-white">
                      <div className="h-8 w-8 rounded-full bg-gray-700 flex items-center justify-center mr-2">
                        {user?.full_name ? user.full_name[0].toUpperCase() : "U"}
                      </div>
                      <div className="text-sm">
                        <div className="font-medium">{user?.full_name || "User"}</div>
                        <div className="text-xs text-gray-400">My Company</div>
                      </div>
                    </div>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="mt-2 bg-gray-800 text-gray-100 border border-gray-700">
                    <DropdownMenuItem onClick={() => router.push('/profile')} className="cursor-pointer hover:bg-gray-700">
                      <User className="h-4 w-4 mr-2 text-gray-300" />
                      <span>Profile</span>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-gray-700" />
                    <DropdownMenuItem onClick={handleLogout} className="cursor-pointer hover:bg-gray-700 text-gray-300">
                      <LogOut className="h-4 w-4 mr-2" />
                      <span>Logout</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  href="/auth/login"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  Login
                </Link>
              </div>
            )}
          </div>
          
          {/* Mobile menu section */}
          <div className="md:hidden flex items-center space-x-2">
            {isAuthenticated ? (
              <DropdownMenu>
                <DropdownMenuTrigger className="focus:outline-none">
                  <div className="h-8 w-8 rounded-full bg-gray-700 flex items-center justify-center">
                    {user?.full_name ? user.full_name[0].toUpperCase() : "U"}
                  </div>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="mt-2 bg-gray-800 text-gray-100 border border-gray-700">
                  <DropdownMenuItem onClick={() => router.push('/profile')} className="cursor-pointer hover:bg-gray-700">
                    <User className="h-4 w-4 mr-2 text-gray-300" />
                    <span>Profile</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => router.push('/dashboard')} className="cursor-pointer hover:bg-gray-700">
                    <span>Dashboard</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => router.push('/dashboard/projects')} className="cursor-pointer hover:bg-gray-700">
                    <span>Projects</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => router.push('/dashboard/tasks')} className="cursor-pointer hover:bg-gray-700">
                    <span>Tasks</span>
                  </DropdownMenuItem>
                  {isAdmin && (
                    <DropdownMenuItem onClick={() => router.push('/admin/users')} className="cursor-pointer hover:bg-gray-700">
                      <span>Admin</span>
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator className="bg-gray-700" />
                  <DropdownMenuItem onClick={handleLogout} className="cursor-pointer hover:bg-gray-700 text-gray-300">
                    <LogOut className="h-4 w-4 mr-2" />
                    <span>Logout</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Link
                href="/auth/login"
                className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
              >
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
} 