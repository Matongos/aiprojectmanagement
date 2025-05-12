import React from 'react';
import * as Progress from '@radix-ui/react-progress';
import { format } from 'date-fns';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { useRouter } from 'next/navigation';
import { TaskState, statusConfig } from '@/types/task';

// Task priority colors
const priorityColors = {
  low: 'bg-blue-100 text-blue-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  urgent: 'bg-red-100 text-red-800',
};

// Progress percentage based on status
const getProgressPercentage = (state: TaskState): number => {
  switch (state) {
    case TaskState.IN_PROGRESS: return 50;
    case TaskState.CHANGES_REQUESTED: return 25;
    case TaskState.APPROVED: return 75;
    case TaskState.DONE: return 100;
    case TaskState.CANCELED: return 100;
    default: return 0;
  }
};

// Progress bar color based on status
const getProgressColor = (state: TaskState): string => {
  switch (state) {
    case TaskState.IN_PROGRESS: return 'bg-blue-500';
    case TaskState.CHANGES_REQUESTED: return 'bg-orange-500';
    case TaskState.APPROVED: return 'bg-green-500';
    case TaskState.DONE: return 'bg-purple-500';
    case TaskState.CANCELED: return 'bg-red-500';
    default: return 'bg-gray-500';
  }
};

export interface TaskProps {
  id: number;
  title: string;
  description?: string;
  state: TaskState;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date?: string;
  estimated_hours?: number;
  actual_hours?: number;
  tags?: string;
  project_id: number;
  onClick?: () => void;
}

export const TaskProgressCard: React.FC<TaskProps> = ({
  id,
  title,
  description,
  state,
  priority,
  due_date,
  estimated_hours,
  actual_hours,
  tags,
  project_id,
  onClick,
}) => {
  const router = useRouter();
  const progressPercentage = getProgressPercentage(state);
  const progressColor = getProgressColor(state);
  
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      router.push(`/dashboard/projects/${project_id}/tasks/${id}`);
    }
  };
  
  return (
    <Card 
      className="w-full hover:shadow-md transition-shadow duration-200 cursor-pointer" 
      onClick={handleClick}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <h3 className="font-medium text-lg line-clamp-1">{title}</h3>
        <div className="flex space-x-2">
          <Badge className={statusConfig[state].color}>
            {state.replace(/_/g, ' ').toLowerCase()}
          </Badge>
          <Badge className={priorityColors[priority]}>{priority}</Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        {description && (
          <p className="text-sm text-gray-500 line-clamp-2 mb-3">{description}</p>
        )}
        
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Progress</span>
            <span>{progressPercentage}%</span>
          </div>
          <Progress.Root 
            className="relative overflow-hidden bg-gray-200 rounded-full w-full h-2"
            value={progressPercentage}
          >
            <Progress.Indicator
              className={`h-full transition-transform duration-500 ease-in-out ${progressColor}`}
              style={{ width: `${progressPercentage}%` }}
            />
          </Progress.Root>
        </div>
        
        {(estimated_hours || actual_hours) && (
          <div className="flex items-center justify-between text-xs text-gray-500 mt-2">
            {estimated_hours && <span>Est: {estimated_hours}h</span>}
            {actual_hours && <span>Actual: {actual_hours}h</span>}
          </div>
        )}
      </CardContent>
      
      <CardFooter className="pt-0 flex justify-between items-center">
        {due_date && (
          <span className="text-xs text-gray-500">
            Due: {format(new Date(due_date), 'MMM d, yyyy')}
          </span>
        )}
        
        {tags && (
          <div className="flex flex-wrap gap-1">
            {tags.split(',').map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {tag.trim()}
              </Badge>
            ))}
          </div>
        )}
      </CardFooter>
    </Card>
  );
};

export default TaskProgressCard; 