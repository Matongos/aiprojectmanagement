'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Bell, MessageSquare, User, LogOut, Settings, Menu, X, ChevronRight, ChevronDown } from 'lucide-react';
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
import { cn } from "@/lib/utils";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
  NavigationMenuContent,
} from "@/components/ui/navigation-menu";
import { NotificationCount } from '@/components/NotificationCount';

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

interface NavigationItem {
  href: string;
  label: string;
  disabled?: boolean;
}

export default function Navigation() {
  const { user, isAuthenticated, logout } = useAuthStore();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  
  const isAdmin = user?.is_superuser === true;

  // Only run on client to prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/auth/login');
  };

  const navigationItems: NavigationItem[] = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/dashboard/projects', label: 'Projects' },
    { href: '/dashboard/tasks', label: 'Tasks' },
  ];

  const configurationItems: NavigationItem[] = [
    { href: '/settings', label: 'Settings' },
    { href: '/configuration/projects', label: 'Projects' },
    { href: '/configuration/tags', label: 'Tags' },
    { href: '/configuration/activity-types', label: 'Activity Types' },
    { href: '/configuration/activity-plans', label: 'Activity Plans' },
  ];

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
    <>
      <nav className="bg-white text-gray-800 shadow-sm border-b border-gray-200">
        <div className="max-w-full mx-auto px-4">
          <div className="flex h-14 items-center justify-between">
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
              <Link href="/" className="text-lg font-medium text-gray-900 hover:text-gray-700">
                PROJECT MANAGER
              </Link>
            </div>

            {/* Desktop Navigation */}
            {isAuthenticated && (
              <div className="hidden md:flex items-center space-x-1 flex-1 ml-8">
                <NavigationMenu>
                  <NavigationMenuList>
                    {navigationItems.map((item) => (
                      <NavigationMenuItem key={item.href}>
                        <NavigationMenuLink asChild>
                          <Link 
                            href={item.href}
                            className={cn(
                              "px-4 py-2 hover:bg-accent hover:text-accent-foreground",
                              pathname === item.href && "bg-accent text-accent-foreground"
                            )}
                          >
                            {item.label}
                          </Link>
                        </NavigationMenuLink>
                      </NavigationMenuItem>
                    ))}

                    <NavigationMenuItem>
                      <NavigationMenuTrigger>Reports</NavigationMenuTrigger>
                      <NavigationMenuContent>
                        <div className="w-[200px] p-2">
                          <NavigationMenuLink asChild>
                            <Link 
                              href="/dashboard/reports?type=projects"
                              className={cn(
                                "block px-4 py-2 hover:bg-accent hover:text-accent-foreground rounded-md",
                                pathname === "/dashboard/reports" && searchParams?.get("type") === "projects" && "bg-accent text-accent-foreground"
                              )}
                              onClick={() => {
                                router.push('/dashboard/reports?type=projects', { scroll: false });
                              }}
                            >
                              Project Reports
                            </Link>
                          </NavigationMenuLink>
                          <NavigationMenuLink asChild>
                            <Link 
                              href="/dashboard/reports?type=tasks"
                              className={cn(
                                "block px-4 py-2 hover:bg-accent hover:text-accent-foreground rounded-md",
                                pathname === "/dashboard/reports" && searchParams?.get("type") === "tasks" && "bg-accent text-accent-foreground"
                              )}
                              onClick={() => {
                                router.push('/dashboard/reports?type=tasks', { scroll: false });
                              }}
                            >
                              Task Reports
                            </Link>
                          </NavigationMenuLink>
                        </div>
                      </NavigationMenuContent>
                    </NavigationMenuItem>
                  </NavigationMenuList>
                </NavigationMenu>
              </div>
            )}

            {/* Right side - User info and actions */}
            <div className="flex items-center space-x-2">
              {isAuthenticated ? (
                <>
                  {/* Desktop Profile */}
                  <div className="hidden md:flex items-center space-x-4">
                    <NotificationCount />
                    
                    <button className="text-gray-600 hover:text-gray-900 p-1 rounded-sm hover:bg-gray-100">
                      <MessageSquare className="h-5 w-5" />
                    </button>

                    <DropdownMenu>
                      <DropdownMenuTrigger className="focus:outline-none">
                        <div className="flex items-center space-x-2 hover:opacity-90">
                          <div className="h-8 w-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center">
                            {user?.full_name ? user.full_name[0].toUpperCase() : "U"}
                          </div>
                          <ChevronDown className="h-4 w-4 text-gray-500" />
                        </div>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="mt-1 bg-white text-gray-900 border border-gray-200 shadow-lg rounded-md">
                        <div className="px-3 py-2 text-sm font-medium text-gray-900 border-b border-gray-100">
                          {user?.full_name || "User"}
                        </div>
                        <DropdownMenuItem onClick={() => router.push('/profile')} className="cursor-pointer hover:bg-gray-50 text-sm">
                          <User className="h-4 w-4 mr-2 text-gray-500" />
                          <span>Profile</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator className="bg-gray-200" />
                        <DropdownMenuItem onClick={handleLogout} className="cursor-pointer hover:bg-gray-50 text-sm text-red-600 hover:text-red-700">
                          <LogOut className="h-4 w-4 mr-2" />
                          <span>Logout</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  {/* Mobile Menu Button */}
                  <button
                    onClick={() => setIsSidebarOpen(true)}
                    className="md:hidden inline-flex items-center justify-center p-2"
                  >
                    <div className="flex items-center space-x-2">
                      <div className="h-8 w-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center">
                        {user?.full_name ? user.full_name[0].toUpperCase() : "U"}
                      </div>
                    </div>
                  </button>
                </>
              ) : (
                <Link
                  href="/auth/login"
                  className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Login
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile Sidebar */}
      {isSidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-gray-600 bg-opacity-50 transition-opacity md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />

          {/* Sidebar */}
          <div className="fixed inset-y-0 right-0 flex flex-col w-64 bg-white shadow-xl transform transition-transform md:hidden">
            <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200">
              <div className="flex items-center space-x-2">
                <div className="h-8 w-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center">
                  {user?.full_name ? user.full_name[0].toUpperCase() : "U"}
                </div>
                <span className="text-sm font-medium text-gray-900">{user?.full_name || "User"}</span>
              </div>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="px-2 py-4 space-y-1">
                {/* Profile Section */}
                <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Account
                </div>
                <Link
                  href="/profile"
                  className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-sm"
                  onClick={() => setIsSidebarOpen(false)}
                >
                  <User className="h-4 w-4 mr-2" />
                  Profile
                </Link>

                {/* Navigation Items */}
                <div className="mt-4">
                  <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Navigation
                  </div>
                  {navigationItems.map((item) => !item.disabled && item.href ? (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center px-3 py-2 text-sm font-medium rounded-sm ${
                        pathname === item.href || pathname?.startsWith(item.href + '/') 
                          ? 'bg-blue-50 text-blue-700' 
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                      onClick={() => setIsSidebarOpen(false)}
                    >
                      {item.label}
                    </Link>
                  ) : (
                    <span
                      key={item.label}
                      className="flex items-center px-3 py-2 text-sm font-medium text-gray-400 cursor-not-allowed"
                    >
                      {item.label}
                    </span>
                  ))}
                </div>

                {/* Configuration Section */}
                <div className="mt-4">
                  <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Configuration
                  </div>
                  {configurationItems.map((item) => item.href && (
                    <Link
                      key={item.label}
                      href={item.href}
                      className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-sm"
                      onClick={() => setIsSidebarOpen(false)}
                    >
                      <ChevronRight className="h-4 w-4 mr-2" />
                      {item.label}
                    </Link>
                  ))}
                </div>

                {/* Logout Button */}
                <div className="mt-4 px-3">
                  <button
                    onClick={() => {
                      setIsSidebarOpen(false);
                      handleLogout();
                    }}
                    className="flex items-center w-full px-3 py-2 text-sm font-medium text-red-600 hover:bg-gray-100 rounded-sm"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Log out
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
} 