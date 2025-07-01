# AI Project Timeline Optimization: Step-by-Step Implementation Guide

This guide explains how the endpoint `GET /ai/projects/{project_id}/optimize-timeline` was implemented, how it analyzes project tasks, suggests new due dates using AI, and how the frontend displays and allows users to apply these AI-suggested dates (with a save button).

---

## 1. Backend: Endpoint & AI Logic

### 1.1. FastAPI Endpoint

**File:** `backend/routers/ai_router.py`

```python
@router.get("/projects/{project_id}/optimize-timeline")
async def optimize_project_timeline(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Suggest an optimized timeline for all tasks in a project.
    Returns a list of task IDs and their suggested new due dates.
    """
    try:
        ai_service = get_ai_service(db)
        result = await ai_service.optimize_project_timeline(project_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error optimizing project timeline: {str(e)}"
        )
```

### 1.2. AI Timeline Optimization Logic

**File:** `backend/services/ai_service.py`

```python
class AIService:
    ...
    async def optimize_project_timeline(self, project_id: int) -> dict:
        """
        AI-driven timeline optimization using Ollama LLM to suggest new due dates.
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            return {"suggested_schedule": []}

        # Prepare task data for the AI
        task_data = []
        for task in tasks:
            if task.state in [TaskState.DONE, TaskState.CANCELED]:
                continue
            task_data.append({
                "id": task.id,
                "name": task.name,
                "state": task.state,
                "progress": task.progress,
                "priority": task.priority,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "planned_hours": task.planned_hours,
                "assigned_to": task.assigned_to,
                "depends_on": [dep.id for dep in task.depends_on]
            })

        # Build a prompt for the LLM
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = (
            f"You are an expert project manager AI. Today's date is {current_date}. "
            "Analyze the following tasks and suggest new due dates for any tasks that are overdue, blocked, or at risk. "
            "IMPORTANT: All suggested due dates must be in the future (after today). "
            "For each task that needs rescheduling, respond with: "
            "Task ID: [task_id]\nNew Due Date: [YYYY-MM-DD]\n\n"
            "If no tasks need rescheduling, respond with: No rescheduling needed\n\n"
            f"Tasks to analyze:\n{json.dumps(task_data, default=str)}"
        )

        # Call Ollama LLM
        try:
            from services.ollama_client import get_ollama_client
            client = get_ollama_client()
            response = await client.generate(
                model="mistral",
                prompt=prompt,
                max_tokens=512,
                temperature=0.2
            )
            ai_response = response.text.strip() if response and hasattr(response, 'text') else ""
            # Parse the AI response
            suggestions = []
            if ai_response:
                import re
                task_matches = re.findall(r"Task ID:\s*(\d+).*?New Due Date:\s*(\d{4}-\d{2}-\d{2})", ai_response, re.IGNORECASE | re.DOTALL)
                for task_id, new_due_date in task_matches:
                    suggestions.append({
                        "task_id": int(task_id),
                        "new_due_date": new_due_date
                    })
        except Exception as e:
            suggestions = []

        # Store results in Redis for caching and history
        try:
            timestamp = datetime.now().isoformat()
            result_data = {
                "project_id": project_id,
                "suggested_schedule": suggestions,
                "generated_at": timestamp,
                "task_count": len(task_data),
                "suggestions_count": len(suggestions)
            }
            latest_key = f"timeline_optimization:{project_id}:latest"
            redis_client.set(latest_key, json.dumps(result_data, default=str))
            history_key = f"timeline_optimization:{project_id}:{timestamp}"
            redis_client.set(history_key, json.dumps(result_data, default=str))
            # Keep only last 10 history entries
            pattern = f"timeline_optimization:{project_id}:*"
            keys = [k for k in redis_client.keys(pattern) if not k.endswith(":latest")]
            if len(keys) > 10:
                keys.sort()
                for old_key in keys[:-10]:
                    redis_client.delete(old_key)
        except Exception as e:
            pass
        return {"suggested_schedule": suggestions}
```

### 1.3. Fetching Latest Suggestions (for Frontend)

**File:** `backend/routers/ai_router.py`

```python
@router.get("/projects/{project_id}/optimize-timeline/latest")
async def get_latest_timeline_optimization(
    project_id: int,
    db: Session = Depends(get_db)
):
    ...
    # Fetch from Redis, filter out suggestions already applied
    # Returns: { "suggested_schedule": [ { "task_id": int, "new_due_date": str }, ... ] }
```

---

## 2. Frontend: Fetching & Displaying AI Suggestions

### 2.1. Fetching AI Suggestions for a Task

**File:** `frontend/src/app/dashboard/projects/[id]/tasks/[taskId]/page.tsx`

```tsx
useEffect(() => {
  const fetchAiSuggestion = async () => {
    if (!token || !id || !task) return;
    try {
      const response = await fetch(`${API_BASE_URL}/ai/projects/${id}/optimize-timeline/latest`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        if (data && data.suggested_schedule && Array.isArray(data.suggested_schedule)) {
          const suggestion = data.suggested_schedule.find(
            (s: { task_id: number }) => s.task_id === Number(taskId)
          );
          if (suggestion && suggestion.new_due_date) {
            const suggestedDate = new Date(suggestion.new_due_date);
            const formattedDate = `${suggestedDate.getFullYear()}-${String(suggestedDate.getMonth() + 1).padStart(2, '0')}-${String(suggestedDate.getDate()).padStart(2, '0')}T${String(suggestedDate.getHours()).padStart(2, '0')}:${String(suggestedDate.getMinutes()).padStart(2, '0')}`;
            const currentDeadline = task.deadline ? new Date(task.deadline).toISOString().slice(0, 16) : null;
            if (formattedDate !== currentDeadline) {
              setAiSuggestedDate(formattedDate);
              setShowAiSuggestion(true);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error fetching AI suggestion:", error);
    }
  };
  fetchAiSuggestion();
}, [id, taskId, token, task]);
```

### 2.2. Displaying the AI Suggested Date (with Icon)

```tsx
{showAiSuggestion && aiSuggestedDate && (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">AI Suggested Due Date</label>
    <div 
      className="mt-1 p-2 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-md cursor-pointer hover:border-blue-400 transition-all"
      onClick={handleApplyAiSuggestion}
      title="Click to apply this date"
    >
      <div className="flex items-center space-x-2">
        <div className="flex items-center justify-center w-5 h-5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full">
          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-blue-900">{aiSuggestedDate.replace('T', ' ')}</div>
        </div>
        <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          AI
        </span>
      </div>
    </div>
  </div>
)}
```

### 2.3. Applying the AI Suggested Date (User Click)

```tsx
const handleApplyAiSuggestion = () => {
  if (aiSuggestedDate) {
    setDeadline(aiSuggestedDate); // Set the deadline input to the AI date
    const taskDeadline = task?.deadline ? new Date(task.deadline).toISOString().slice(0, 16) : null;
    setIsDeadlineChanged(aiSuggestedDate !== taskDeadline); // Mark as changed
    setShowAiSuggestion(false); // Hide the suggestion
  }
};
```

### 2.4. Showing the Save Button

The save button appears when there are unsaved changes (e.g., after applying the AI suggestion):

```tsx
{hasUnsavedChanges && (
  <Button
    variant="default"
    size="sm"
    className="bg-blue-800 text-white hover:bg-blue-900"
    onClick={handleSaveChanges}
  >
    Save Changes
  </Button>
)}
```

---

## 3. Summary of the Flow

1. **User triggers optimization** (or it runs automatically):
    - Backend endpoint `/ai/projects/{project_id}/optimize-timeline` analyzes tasks and stores suggestions in Redis.
2. **Frontend fetches latest suggestions** for the project and task.
3. **If a suggestion exists and is different from the current deadline:**
    - An "AI Suggested Due Date" box with an icon appears.
4. **User clicks the suggestion:**
    - The deadline input is updated.
    - The "Save Changes" button appears.
5. **User clicks Save:**
    - The new deadline is saved to the backend (via the normal task update endpoint).

---

## 4. Adapting to Another System

- **Backend:**
  - Implement an endpoint that analyzes tasks and suggests new dates (using AI or rules).
  - Store results in a cache (e.g., Redis) for quick frontend access.
- **Frontend:**
  - Fetch suggestions and compare with current values.
  - Show a clickable suggestion box with an icon if a suggestion exists.
  - On click, update the input and show a save button.
  - Save changes via your normal update endpoint.

---

**This pattern can be adapted to any system where AI or logic suggests field changes, and the user can review and apply them.** 