"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UserCircle, Users } from "lucide-react";
import AuthWrapper from "@/components/AuthWrapper";

function TaskSelectionContent() {
  const router = useRouter();

  return (
    <div className="container mx-auto py-8">
      <div className="grid md:grid-cols-2 gap-6">
        {/* My Tasks Card */}
        <Card 
          className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
          onClick={() => router.push("/dashboard/tasks/my-tasks")}
        >
          <div className="flex flex-col items-center text-center space-y-4">
            <UserCircle className="h-16 w-16 text-blue-500" />
            <h2 className="text-xl font-semibold">My Tasks</h2>
            <p className="text-gray-600">View and manage tasks assigned to you</p>
            <Button className="w-full">
              View My Tasks
            </Button>
          </div>
        </Card>

        {/* All Tasks Card */}
        <Card 
          className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
          onClick={() => router.push("/dashboard/tasks/all-tasks")}
        >
          <div className="flex flex-col items-center text-center space-y-4">
            <Users className="h-16 w-16 text-green-500" />
            <h2 className="text-xl font-semibold">All Tasks</h2>
            <p className="text-gray-600">View all tasks across all projects</p>
            <Button className="w-full">
              View All Tasks
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function TaskSelectionPage() {
  return (
    <AuthWrapper>
      <TaskSelectionContent />
    </AuthWrapper>
  );
} 