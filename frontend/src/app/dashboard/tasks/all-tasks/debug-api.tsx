"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "react-hot-toast";
import { API_BASE_URL } from "@/lib/constants";
import axios from 'axios';
import { Button } from "@/components/ui/button";

interface ApiStatus {
  endpoint: string;
  status: 'success' | 'error' | 'pending';
  message: string;
}

export default function ApiDebugger() {
  const [apiStatus, setApiStatus] = useState<ApiStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const token = useAuthStore((state) => state.token);

  const endpoints = [
    `${API_BASE_URL}/tasks/`,
    `${API_BASE_URL}/task_stages/`,
  ];

  const testEndpoints = async () => {
    setIsLoading(true);
    setApiStatus([]);
    
    const newStatus: ApiStatus[] = [];
    
    for (const endpoint of endpoints) {
      try {
        newStatus.push({
          endpoint,
          status: 'pending',
          message: 'Testing...'
        });
        setApiStatus([...newStatus]);
        
        const response = await axios.get(endpoint, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        const lastIndex = newStatus.length - 1;
        newStatus[lastIndex] = {
          endpoint,
          status: 'success',
          message: `Success! Got ${response.data.length} items.`
        };
        setApiStatus([...newStatus]);
      } catch (error: any) {
        const lastIndex = newStatus.length - 1;
        newStatus[lastIndex] = {
          endpoint,
          status: 'error',
          message: error.response ? `Error: ${error.response.status} - ${error.response.statusText}` : error.message
        };
        setApiStatus([...newStatus]);
      }
    }
    
    setIsLoading(false);
  };

  return (
    <div className="p-6 bg-white rounded-lg border">
      <h2 className="text-xl font-semibold mb-4">API Debugger</h2>
      <p className="mb-4">Test your API endpoints required for drag-and-drop functionality</p>
      
      <Button 
        onClick={testEndpoints} 
        disabled={isLoading}
        className="mb-4"
      >
        {isLoading ? 'Testing...' : 'Test API Endpoints'}
      </Button>
      
      <div className="space-y-3 mt-4">
        {apiStatus.map((status, index) => (
          <div 
            key={index} 
            className={`p-3 rounded-md ${
              status.status === 'success' ? 'bg-green-50 border border-green-200' : 
              status.status === 'error' ? 'bg-red-50 border border-red-200' : 
              'bg-yellow-50 border border-yellow-200'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm">{status.endpoint}</span>
              <span className={`text-xs px-2 py-1 rounded ${
                status.status === 'success' ? 'bg-green-200 text-green-800' : 
                status.status === 'error' ? 'bg-red-200 text-red-800' : 
                'bg-yellow-200 text-yellow-800'
              }`}>
                {status.status.toUpperCase()}
              </span>
            </div>
            <p className="text-sm mt-1">{status.message}</p>
          </div>
        ))}
      </div>
      
      {apiStatus.length > 0 && apiStatus.some(s => s.status === 'error') && (
        <div className="mt-4 p-3 bg-gray-50 rounded-md">
          <h3 className="text-md font-medium mb-2">Troubleshooting Tips:</h3>
          <ul className="list-disc pl-5 space-y-1 text-sm">
            <li>Make sure your backend server is running</li>
            <li>Check if your API routes are correctly defined in backend</li>
            <li>Verify your authentication token is valid</li>
            <li>Ensure you have /tasks/ and /task_stages/ endpoints</li>
            <li>Check for any CORS issues in the console</li>
          </ul>
        </div>
      )}
    </div>
  );
} 