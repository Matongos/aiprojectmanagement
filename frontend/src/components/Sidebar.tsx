'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { 
  Home, 
  Briefcase, 
  CheckSquare, 
  PieChart, 
  Users, 
  Settings, 
  Calendar,
  MessageSquare,
  HelpCircle
} from 'lucide-react';

export default function Sidebar() {
  const { user } = useAuthStore();
  const pathname = usePathname();
  
  const isAdmin = user?.is_superuser === true;

  const navItems = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: <Home className="h-5 w-5" />,
      exact: true
    },
    {
      name: 'Projects',
      href: '/dashboard/projects',
      icon: <Briefcase className="h-5 w-5" />,
      exact: false
    },
    {
      name: 'Tasks',
      href: '/dashboard/tasks',
      icon: <CheckSquare className="h-5 w-5" />,
      exact: false
    },
    {
      name: 'Calendar',
      href: '/dashboard/calendar',
      icon: <Calendar className="h-5 w-5" />,
      exact: false
    },
    {
      name: 'Reports',
      href: '/reporting',
      icon: <PieChart className="h-5 w-5" />,
      exact: false
    },
    {
      name: 'Messages',
      href: '/dashboard/messages',
      icon: <MessageSquare className="h-5 w-5" />,
      exact: false
    }
  ];

  const adminNavItems = [
    {
      name: 'Users',
      href: '/admin/users',
      icon: <Users className="h-5 w-5" />,
      exact: false
    },
    {
      name: 'Settings',
      href: '/admin/settings',
      icon: <Settings className="h-5 w-5" />,
      exact: false
    }
  ];

  const isActiveLink = (item: { href: string; exact: boolean }) => {
    if (item.exact) {
      return pathname === item.href;
    }
    return pathname.startsWith(item.href);
  };

  return (
    <aside className="bg-white border-r border-gray-200 w-64 h-screen fixed left-0 top-16 overflow-y-auto">
      <div className="px-4 py-5">
        <nav className="space-y-6">
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Main
            </h3>
            <ul className="space-y-1">
              {navItems.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className={`group flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                      isActiveLink(item)
                        ? 'bg-purple-50 text-purple-700'
                        : 'text-gray-700 hover:text-purple-700 hover:bg-gray-50'
                    }`}
                  >
                    <span className={`mr-3 ${isActiveLink(item) ? 'text-purple-700' : 'text-gray-500 group-hover:text-purple-700'}`}>
                      {item.icon}
                    </span>
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {isAdmin && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Admin
              </h3>
              <ul className="space-y-1">
                {adminNavItems.map((item) => (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={`group flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                        isActiveLink(item)
                          ? 'bg-purple-50 text-purple-700'
                          : 'text-gray-700 hover:text-purple-700 hover:bg-gray-50'
                      }`}
                    >
                      <span className={`mr-3 ${isActiveLink(item) ? 'text-purple-700' : 'text-gray-500 group-hover:text-purple-700'}`}>
                        {item.icon}
                      </span>
                      {item.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="pt-4 mt-4 border-t border-gray-200">
            <div className="px-3 py-3 rounded-md bg-purple-50">
              <div className="flex items-center">
                <HelpCircle className="h-5 w-5 text-purple-700 mr-3" />
                <div>
                  <h4 className="text-sm font-medium text-purple-700">Need help?</h4>
                  <p className="text-xs text-gray-600 mt-1">Check our documentation</p>
                </div>
              </div>
              <Link 
                href="/help" 
                className="mt-2 text-xs font-medium text-purple-700 hover:text-purple-800 flex justify-end"
              >
                View Documentation →
              </Link>
            </div>
          </div>
        </nav>
      </div>
    </aside>
  );
} 