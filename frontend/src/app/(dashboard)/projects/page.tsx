import { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function ProjectsPage() {
  const [projects, setProjects] = useState([
    { id: 1, name: "Website Redesign", progress: 75, dueDate: "2023-12-30" },
    { id: 2, name: "Mobile App Development", progress: 45, dueDate: "2024-01-15" },
    { id: 3, name: "Marketing Campaign", progress: 90, dueDate: "2023-12-10" },
    { id: 4, name: "Database Migration", progress: 30, dueDate: "2024-02-28" },
  ]);

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Projects</h1>
        <Button>Create Project</Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project) => (
          <Card key={project.id} className="overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle>{project.name}</CardTitle>
              <CardDescription>Due: {project.dueDate}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Progress</span>
                  <span className="text-sm font-medium">{project.progress}%</span>
                </div>
                <Progress value={project.progress} className="h-2" />
              </div>
            </CardContent>
            <CardFooter className="bg-muted/50 border-t">
              <div className="flex justify-end w-full">
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/projects/${project.id}`}>View details</Link>
                </Button>
              </div>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
} 