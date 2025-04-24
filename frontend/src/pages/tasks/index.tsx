import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';
import { CalendarDays, Filter, Plus, Search, SlidersHorizontal } from 'lucide-react';
import { format } from 'date-fns';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { 
  Sheet, 
  SheetContent, 
  SheetDescription, 
  SheetHeader, 
  SheetTitle, 
  SheetTrigger 
} from '@/components/ui/sheet';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

// Task status options
const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'not_started', label: 'Not Started' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'completed', label: 'Completed' },
];

// Task priority options
const PRIORITY_OPTIONS = [
  { value: 'all', label: 'All Priorities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
];

// Define mock project data
const MOCK_PROJECTS = [
  { id: '1', name: 'Website Redesign', key: 'WR' },
  { id: '2', name: 'Mobile App Development', key: 'MAD' },
  { id: '3', name: 'Customer Portal', key: 'CP' },
  { id: '4', name: 'Internal Tools', key: 'IT' },
];

// Define mock task data
interface Task {
  id: string;
  title: string;
  projectId: string;
  projectKey: string;
  status: string;
  priority: string;
  dueDate: Date | null;
  assignedTo: string[];
  createdAt: Date;
  updatedAt: Date;
}

// Generate mock tasks
const generateMockTasks = (): Task[] => {
  const statuses = ['not_started', 'in_progress', 'under_review', 'completed'];
  const priorities = ['low', 'medium', 'high', 'urgent'];
  
  return Array.from({ length: 30 }, (_, i) => {
    const projectIndex = i % MOCK_PROJECTS.length;
    const project = MOCK_PROJECTS[projectIndex];
    const taskNumber = i + 101;
    
    return {
      id: `task-${i + 1}`,
      title: `Task ${i + 1} for ${project.name}`,
      projectId: project.id,
      projectKey: project.key,
      status: statuses[Math.floor(Math.random() * statuses.length)],
      priority: priorities[Math.floor(Math.random() * priorities.length)],
      dueDate: Math.random() > 0.3 ? new Date(Date.now() + Math.random() * 30 * 24 * 60 * 60 * 1000) : null,
      assignedTo: Math.random() > 0.2 ? ['John Doe'] : [],
      createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000),
      updatedAt: new Date(Date.now() - Math.random() * 15 * 24 * 60 * 60 * 1000),
    };
  });
};

const TasksPage = () => {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filteredTasks, setFilteredTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Filtering and sorting state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState('updatedAt');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const tasksPerPage = 10;
  
  // Fetch tasks on component mount
  useEffect(() => {
    const fetchTasks = async () => {
      setIsLoading(true);
      try {
        // In a real app, fetch tasks from API
        // const response = await fetch('/api/tasks');
        // const data = await response.json();
        
        // For now, use mock data
        await new Promise(resolve => setTimeout(resolve, 800));
        const mockTasks = generateMockTasks();
        setTasks(mockTasks);
      } catch (error) {
        console.error('Error fetching tasks:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchTasks();
  }, []);
  
  // Apply filters and sorting
  useEffect(() => {
    let result = [...tasks];
    
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(task => 
        task.title.toLowerCase().includes(query) || 
        `${task.projectKey}-${task.id.split('-')[1]}`.toLowerCase().includes(query)
      );
    }
    
    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter(task => task.status === statusFilter);
    }
    
    // Apply priority filter
    if (priorityFilter !== 'all') {
      result = result.filter(task => task.priority === priorityFilter);
    }
    
    // Apply project filter
    if (projectFilter.length > 0) {
      result = result.filter(task => projectFilter.includes(task.projectId));
    }
    
    // Apply sorting
    result.sort((a, b) => {
      let valueA, valueB;
      
      switch (sortBy) {
        case 'dueDate':
          // Sort null due dates to the end
          if (!a.dueDate) return sortOrder === 'asc' ? 1 : -1;
          if (!b.dueDate) return sortOrder === 'asc' ? -1 : 1;
          valueA = a.dueDate.getTime();
          valueB = b.dueDate.getTime();
          break;
        case 'priority':
          const priorityOrder = { 'low': 1, 'medium': 2, 'high': 3, 'urgent': 4 };
          valueA = priorityOrder[a.priority as keyof typeof priorityOrder];
          valueB = priorityOrder[b.priority as keyof typeof priorityOrder];
          break;
        case 'title':
          valueA = a.title;
          valueB = b.title;
          break;
        case 'status':
          const statusOrder = { 'not_started': 1, 'in_progress': 2, 'under_review': 3, 'completed': 4 };
          valueA = statusOrder[a.status as keyof typeof statusOrder];
          valueB = statusOrder[b.status as keyof typeof statusOrder];
          break;
        case 'updatedAt':
        default:
          valueA = a.updatedAt.getTime();
          valueB = b.updatedAt.getTime();
      }
      
      if (sortOrder === 'asc') {
        return valueA > valueB ? 1 : -1;
      } else {
        return valueA < valueB ? 1 : -1;
      }
    });
    
    setFilteredTasks(result);
  }, [tasks, searchQuery, statusFilter, priorityFilter, projectFilter, sortBy, sortOrder]);
  
  // Calculate pagination
  const totalPages = Math.ceil(filteredTasks.length / tasksPerPage);
  const paginatedTasks = filteredTasks.slice(
    (currentPage - 1) * tasksPerPage,
    currentPage * tasksPerPage
  );
  
  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, statusFilter, priorityFilter, projectFilter]);
  
  // Function to toggle project filter
  const toggleProjectFilter = (projectId: string) => {
    if (projectFilter.includes(projectId)) {
      setProjectFilter(projectFilter.filter(id => id !== projectId));
    } else {
      setProjectFilter([...projectFilter, projectId]);
    }
  };
  
  // Function to clear all filters
  const clearFilters = () => {
    setSearchQuery('');
    setStatusFilter('all');
    setPriorityFilter('all');
    setProjectFilter([]);
  };
  
  // Helper function to get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'not_started':
        return 'bg-gray-200 text-gray-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'under_review':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Helper function to get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'low':
        return 'bg-gray-100 text-gray-800';
      case 'medium':
        return 'bg-blue-100 text-blue-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'urgent':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Helper function to get status label
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'not_started':
        return 'Not Started';
      case 'in_progress':
        return 'In Progress';
      case 'under_review':
        return 'Under Review';
      case 'completed':
        return 'Completed';
      default:
        return status;
    }
  };
  
  // Helper function to get priority label
  const getPriorityLabel = (priority: string) => {
    switch (priority) {
      case 'low':
        return 'Low';
      case 'medium':
        return 'Medium';
      case 'high':
        return 'High';
      case 'urgent':
        return 'Urgent';
      default:
        return priority;
    }
  };
  
  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Tasks</h1>
            <p className="text-muted-foreground">View and manage your tasks</p>
          </div>
          
          <div className="mt-4 md:mt-0">
            <Button asChild>
              <Link href="/tasks/create">
                <Plus className="mr-2 h-4 w-4" />
                New Task
              </Link>
            </Button>
          </div>
        </div>
        
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between">
              <div className="mb-4 md:mb-0 flex-1 md:mr-4">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search tasks..."
                    className="pl-8"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-2">
                <Select 
                  value={statusFilter} 
                  onValueChange={setStatusFilter}
                >
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Select 
                  value={priorityFilter} 
                  onValueChange={setPriorityFilter}
                >
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Filter by priority" />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Sheet>
                  <SheetTrigger asChild>
                    <Button variant="outline" className="flex items-center gap-2">
                      <Filter className="h-4 w-4" />
                      <span className="hidden sm:inline">More Filters</span>
                      {projectFilter.length > 0 && (
                        <Badge variant="secondary" className="ml-2">{projectFilter.length}</Badge>
                      )}
                    </Button>
                  </SheetTrigger>
                  <SheetContent>
                    <SheetHeader>
                      <SheetTitle>Filter Tasks</SheetTitle>
                      <SheetDescription>
                        Narrow down your task list using these filters
                      </SheetDescription>
                    </SheetHeader>
                    <div className="mt-6 space-y-6">
                      <div className="space-y-4">
                        <h4 className="font-medium">Project</h4>
                        <div className="space-y-2">
                          {MOCK_PROJECTS.map((project) => (
                            <div key={project.id} className="flex items-center space-x-2">
                              <Checkbox 
                                id={`project-${project.id}`} 
                                checked={projectFilter.includes(project.id)}
                                onCheckedChange={() => toggleProjectFilter(project.id)}
                              />
                              <Label htmlFor={`project-${project.id}`}>{project.key} - {project.name}</Label>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      <div className="pt-4 border-t">
                        <Button onClick={clearFilters} variant="outline" className="w-full">
                          Clear All Filters
                        </Button>
                      </div>
                    </div>
                  </SheetContent>
                </Sheet>
                
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="flex items-center gap-2">
                      <SlidersHorizontal className="h-4 w-4" />
                      <span className="hidden sm:inline">Sort</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      className={sortBy === 'updatedAt' ? 'font-bold' : ''}
                      onClick={() => {
                        setSortBy('updatedAt');
                        setSortOrder(sortBy === 'updatedAt' && sortOrder === 'desc' ? 'asc' : 'desc');
                      }}
                    >
                      {sortBy === 'updatedAt' && sortOrder === 'desc' ? '↓ ' : sortBy === 'updatedAt' && sortOrder === 'asc' ? '↑ ' : ''}
                      Last Updated
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className={sortBy === 'dueDate' ? 'font-bold' : ''}
                      onClick={() => {
                        setSortBy('dueDate');
                        setSortOrder(sortBy === 'dueDate' && sortOrder === 'desc' ? 'asc' : 'desc');
                      }}
                    >
                      {sortBy === 'dueDate' && sortOrder === 'desc' ? '↓ ' : sortBy === 'dueDate' && sortOrder === 'asc' ? '↑ ' : ''}
                      Due Date
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className={sortBy === 'priority' ? 'font-bold' : ''}
                      onClick={() => {
                        setSortBy('priority');
                        setSortOrder(sortBy === 'priority' && sortOrder === 'desc' ? 'asc' : 'desc');
                      }}
                    >
                      {sortBy === 'priority' && sortOrder === 'desc' ? '↓ ' : sortBy === 'priority' && sortOrder === 'asc' ? '↑ ' : ''}
                      Priority
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className={sortBy === 'title' ? 'font-bold' : ''}
                      onClick={() => {
                        setSortBy('title');
                        setSortOrder(sortBy === 'title' && sortOrder === 'desc' ? 'asc' : 'desc');
                      }}
                    >
                      {sortBy === 'title' && sortOrder === 'desc' ? '↓ ' : sortBy === 'title' && sortOrder === 'asc' ? '↑ ' : ''}
                      Title
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className={sortBy === 'status' ? 'font-bold' : ''}
                      onClick={() => {
                        setSortBy('status');
                        setSortOrder(sortBy === 'status' && sortOrder === 'desc' ? 'asc' : 'desc');
                      }}
                    >
                      {sortBy === 'status' && sortOrder === 'desc' ? '↓ ' : sortBy === 'status' && sortOrder === 'asc' ? '↑ ' : ''}
                      Status
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center items-center h-64">
                <p className="text-muted-foreground">Loading tasks...</p>
              </div>
            ) : paginatedTasks.length === 0 ? (
              <div className="flex flex-col justify-center items-center h-64 text-center">
                <p className="text-muted-foreground mb-4">No tasks found matching your filters</p>
                {(searchQuery || statusFilter !== 'all' || priorityFilter !== 'all' || projectFilter.length > 0) && (
                  <Button variant="outline" onClick={clearFilters}>
                    Clear All Filters
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[180px]">Task ID</TableHead>
                      <TableHead>Task Name</TableHead>
                      <TableHead className="hidden md:table-cell">Status</TableHead>
                      <TableHead className="hidden md:table-cell">Priority</TableHead>
                      <TableHead className="hidden lg:table-cell">Due Date</TableHead>
                      <TableHead className="text-right"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedTasks.map((task) => (
                      <TableRow 
                        key={task.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => router.push(`/tasks/${task.id}`)}
                      >
                        <TableCell className="font-medium">
                          {task.projectKey}-{task.id.split('-')[1]}
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{task.title}</div>
                            <div className="text-sm text-muted-foreground md:hidden flex items-center mt-1">
                              <Badge className={`mr-2 ${getStatusColor(task.status)}`}>
                                {getStatusLabel(task.status)}
                              </Badge>
                              <Badge className={getPriorityColor(task.priority)}>
                                {getPriorityLabel(task.priority)}
                              </Badge>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          <Badge className={getStatusColor(task.status)}>
                            {getStatusLabel(task.status)}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          <Badge className={getPriorityColor(task.priority)}>
                            {getPriorityLabel(task.priority)}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          {task.dueDate ? (
                            <div className="flex items-center">
                              <CalendarDays className="mr-2 h-4 w-4 text-muted-foreground" />
                              {format(task.dueDate, 'MMM dd, yyyy')}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">No due date</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="hidden md:inline-flex"
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/tasks/${task.id}`);
                            }}
                          >
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
          {!isLoading && filteredTasks.length > 0 && (
            <CardFooter className="flex justify-between items-center pb-4">
              <div className="text-sm text-muted-foreground">
                Showing {(currentPage - 1) * tasksPerPage + 1}-
                {Math.min(currentPage * tasksPerPage, filteredTasks.length)} of {filteredTasks.length} tasks
              </div>
              
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious 
                      href="#" 
                      onClick={(e) => {
                        e.preventDefault();
                        if (currentPage > 1) setCurrentPage(currentPage - 1);
                      }}
                      className={currentPage === 1 ? 'pointer-events-none opacity-50' : ''}
                    />
                  </PaginationItem>
                  
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNumber;
                    
                    // Logic to show correct page numbers based on current page
                    if (totalPages <= 5) {
                      pageNumber = i + 1;
                    } else if (currentPage <= 3) {
                      pageNumber = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNumber = totalPages - 4 + i;
                    } else {
                      pageNumber = currentPage - 2 + i;
                    }
                    
                    return (
                      <PaginationItem key={i}>
                        <PaginationLink 
                          href="#" 
                          onClick={(e) => {
                            e.preventDefault();
                            setCurrentPage(pageNumber);
                          }}
                          isActive={pageNumber === currentPage}
                        >
                          {pageNumber}
                        </PaginationLink>
                      </PaginationItem>
                    );
                  })}
                  
                  {totalPages > 5 && currentPage < totalPages - 2 && (
                    <PaginationItem>
                      <PaginationEllipsis />
                    </PaginationItem>
                  )}
                  
                  <PaginationItem>
                    <PaginationNext 
                      href="#" 
                      onClick={(e) => {
                        e.preventDefault();
                        if (currentPage < totalPages) setCurrentPage(currentPage + 1);
                      }}
                      className={currentPage === totalPages ? 'pointer-events-none opacity-50' : ''}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </CardFooter>
          )}
        </Card>
      </div>
    </Layout>
  );
};

export default TasksPage; 