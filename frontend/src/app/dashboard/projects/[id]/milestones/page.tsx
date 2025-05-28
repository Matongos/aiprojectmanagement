"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { API_BASE_URL } from "@/lib/constants";
import { toast } from "react-hot-toast";
import { cn } from "@/lib/utils";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

interface Milestone {
  id: number;
  name: string;
  description?: string;
  due_date: string;
  is_completed: boolean;
  is_active: boolean;
}

export default function ProjectMilestonesPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params?.id as string;
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuthStore();

  useEffect(() => {
    if (!projectId || !token) return;
    
    const fetchMilestones = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE_URL}/milestones/project/${projectId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          if (response.status === 403) {
            throw new Error("Milestones are not enabled for this project");
          }
          throw new Error("Failed to fetch milestones");
        }

        const data = await response.json();
        setMilestones(Array.isArray(data) ? data : []);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load milestones";
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchMilestones();
  }, [projectId, token]);

  // Filtering
  const filteredMilestones = milestones.filter(m => m.name.toLowerCase().includes(search.toLowerCase()));
  // Pagination
  const totalPages = Math.ceil(filteredMilestones.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentMilestones = filteredMilestones.slice(startIndex, endIndex);

  // Bulk selection
  const allSelected = selected.length === currentMilestones.length && currentMilestones.length > 0;
  const toggleSelectAll = () => {
    if (allSelected) setSelected([]);
    else setSelected(currentMilestones.map(m => m.id));
  };
  const toggleSelect = (id: number) => {
    setSelected(sel => sel.includes(id) ? sel.filter(sid => sid !== id) : [...sel, id]);
  };

  return (
    <div className="p-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="default" className="mr-2">Save</Button>
        <Button variant="secondary">Discard</Button>
        <span className="ml-4 text-lg font-semibold">Projects</span>
        <span className="text-gray-500">Office Design&apos;s Milestones</span>
        {/* Settings icon placeholder */}
        <div className="ml-2 w-5 h-5 bg-gray-200 rounded-full flex items-center justify-center">⚙️</div>
        <div className="flex-1" />
        <div className="relative">
          <Input
            placeholder="Search..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-8 w-64"
          />
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
        </div>
      </div>
      <div className="border rounded-lg overflow-x-auto bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox checked={allSelected} onCheckedChange={toggleSelectAll} />
              </TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Deadline</TableHead>
              <TableHead>Reached</TableHead>
              <TableHead className="text-right"> </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8">Loading...</TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-red-500">{error}</TableCell>
              </TableRow>
            ) : currentMilestones.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8">No milestones found.</TableCell>
              </TableRow>
            ) : currentMilestones.map(milestone => (
              <TableRow key={milestone.id} className={cn(selected.includes(milestone.id) && "bg-gray-50")}
                onClick={() => toggleSelect(milestone.id)}
                style={{ cursor: "pointer" }}
              >
                <TableCell>
                  <Checkbox checked={selected.includes(milestone.id)} onCheckedChange={() => toggleSelect(milestone.id)} />
                </TableCell>
                <TableCell>{milestone.name}</TableCell>
                <TableCell>{milestone.due_date ? new Date(milestone.due_date).toLocaleDateString() : "-"}</TableCell>
                <TableCell>
                  <Checkbox checked={milestone.is_completed} disabled />
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="link" onClick={e => { e.stopPropagation(); router.push(`/dashboard/projects/${projectId}/milestones/${milestone.id}/tasks`); }}>View Tasks</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {/* Pagination */}
      <div className="flex items-center justify-end gap-2 mt-2">
        <span className="text-sm text-gray-500">{startIndex + 1}-{Math.min(endIndex, filteredMilestones.length)} / {filteredMilestones.length}</span>
        <Button variant="ghost" size="icon" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      {/* Placeholders for progress tracking, filtering, sorting, bulk actions, analytics, and Gantt chart */}
      <div className="mt-8">
        {/* TODO: Progress tracking, analytics, Gantt chart, etc. */}
      </div>
    </div>
  );
} 