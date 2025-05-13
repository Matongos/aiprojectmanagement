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

interface Tag {
  id: number;
  name: string;
  color: number;
  active: boolean;
}

export interface TaskProps {
  id: number;
  title: string;
  description?: string;
  state: TaskState;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date?: string;
  estimated_hours?: number;
  actual_hours?: number;
  tags?: Tag[];
  project_id: number;
  onClick?: () => void;
}

// Helper function to get tag color class
const getTagColorClass = (colorIndex: number) => {
  const colors = {
    1: 'bg-blue-50 text-blue-700',
    2: 'bg-purple-50 text-purple-700',
    3: 'bg-green-50 text-green-700',
    4: 'bg-orange-50 text-orange-700',
    5: 'bg-pink-50 text-pink-700',
    6: 'bg-cyan-50 text-cyan-700',
    7: 'bg-lime-50 text-lime-700',
    8: 'bg-amber-50 text-amber-700',
    9: 'bg-stone-50 text-stone-700',
    10: 'bg-indigo-50 text-indigo-700',
    11: 'bg-red-50 text-red-700',
  };
  return colors[colorIndex as keyof typeof colors] || colors[1];
};

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
      
      <CardContent className="space-y-4">
        {description && (
          <p className="text-sm text-gray-500 line-clamp-2">{description}</p>
        )}
        
        {tags && tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span
                key={tag.id}
                className={`px-3 py-1 rounded-full text-sm ${getTagColorClass(tag.color)}`}
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}

        <div>
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
          <div className="flex items-center justify-between text-xs text-gray-500">
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
      </CardFooter>
    </Card>
  );
};

export default TaskProgressCard; 