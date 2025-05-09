import React, { useState } from 'react';
import TaskProgressCard, { TaskProps } from './TaskProgressCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface TaskListProps {
  tasks: TaskProps[];
  onTaskClick?: (taskId: number) => void;
}

const TaskList: React.FC<TaskListProps> = ({ tasks, onTaskClick }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all_status');
  const [priorityFilter, setPriorityFilter] = useState<string>('all_priority');

  // Filter tasks based on search term and filters
  const filteredTasks = tasks.filter((task) => {
    // Search term filter
    const matchesSearch = 
      task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (task.description && task.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (task.tags && task.tags.toLowerCase().includes(searchTerm.toLowerCase()));

    // Status filter
    const matchesStatus = statusFilter === 'all_status' || task.status === statusFilter;

    // Priority filter
    const matchesPriority = priorityFilter === 'all_priority' || task.priority === priorityFilter;

    return matchesSearch && matchesStatus && matchesPriority;
  });

  // Sort tasks: first by priority (urgent to low), then by due date (closest first)
  const sortedTasks = [...filteredTasks].sort((a, b) => {
    const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 };
    
    // First sort by priority
    const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
    if (priorityDiff !== 0) return priorityDiff;
    
    // Then sort by due date if available
    if (a.due_date && b.due_date) {
      return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
    } else if (a.due_date) {
      return -1; // a has due date, b doesn't
    } else if (b.due_date) {
      return 1; // b has due date, a doesn't
    }
    
    return 0; // both have no due date
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-2">
        <Input
          placeholder="Search tasks..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-grow"
        />
        
        <div className="flex space-x-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all_status">All Status</SelectItem>
              <SelectItem value="todo">To Do</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="review">Review</SelectItem>
              <SelectItem value="done">Done</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all_priority">All Priority</SelectItem>
              <SelectItem value="urgent">Urgent</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
          
          {(searchTerm || statusFilter !== 'all_status' || priorityFilter !== 'all_priority') && (
            <Button 
              variant="outline" 
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all_status');
                setPriorityFilter('all_priority');
              }}
            >
              Clear
            </Button>
          )}
        </div>
      </div>
      
      {sortedTasks.length === 0 ? (
        <div className="text-center py-10 text-gray-500">
          No tasks found matching your criteria
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedTasks.map((task) => (
            <TaskProgressCard
              key={task.id}
              {...task}
              onClick={() => onTaskClick && onTaskClick(task.id)}
            />
          ))}
        </div>
      )}
      
      <div className="text-sm text-gray-500 mt-2">
        Showing {sortedTasks.length} of {tasks.length} tasks
      </div>
    </div>
  );
};

export default TaskList; 