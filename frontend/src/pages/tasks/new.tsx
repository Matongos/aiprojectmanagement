import { useState } from "react";
import { useRouter } from "next/router";
import { NewTaskForm } from "@/components/NewTaskForm";
import Layout from "@/components/Layout";

export default function NewTaskPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const handleCreateTask = async (data: any) => {
    setIsLoading(true);

    try {
      // In a real app, we would make an API call here
      console.log("Creating task:", data);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Redirect to tasks list page
      router.push("/tasks");
    } catch (error) {
      console.error("Error creating task:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-3xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Create New Task</h1>
          <p className="text-muted-foreground">
            Fill in the details to create a new task
          </p>
        </div>
        
        <NewTaskForm onSubmit={handleCreateTask} isLoading={isLoading} />
      </div>
    </Layout>
  );
} 