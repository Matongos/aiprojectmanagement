# Database Schema Design

## Entity Relationship Diagram (ERD)

```
+------------------+       +-------------------+       +------------------+
|      User        |       |     Project       |       |       Task       |
+------------------+       +-------------------+       +------------------+
| id               |       | id                |       | id               |
| email            |       | name              |       | title            |
| username         |       | description       |       | description      |
| full_name        |       | key               |       | project_id       |
| hashed_password  |       | status            |       | stage_id         |
| is_active        |       | privacy_level     |       | status           |
| is_superuser     |       | start_date        |       | priority         |
| profile_image_url|       | end_date          |       | parent_task_id   |
| job_title        |       | created_by        |       | created_by       |
| bio              |       | color             |       | estimated_hours  |
| created_at       |       | is_template       |       | start_date       |
| updated_at       |<----->| metadata          |<----->| due_date         |
+------------------+       | created_at        |       | completed_at     |
        ^                  | updated_at        |       | milestone_id     |
        |                  | is_active         |       | tags             |
        |                  +-------------------+       | metadata         |
        |                           ^                  | created_at       |
        |                           |                  | updated_at       |
        |                           |                  +------------------+
        |                           |                          ^
+------------------+       +-------------------+               |
|      Role        |       | ProjectStage      |               |
+------------------+       +-------------------+               |
| id               |       | id                |               |
| name             |       | project_id        |               |
| description      |       | name              |               |
+------------------+       | description       |               |
        ^                  | sequence_order    |               |
        |                  | created_at        |               |
        |                  | updated_at        |<--------------+
        |                  +-------------------+
        |
+------------------+
| RolePermission   |
+------------------+
| id               |
| role_id          |
| permission_id    |
+------------------+
        |
        v
+------------------+       +-------------------+       +------------------+
|   Permission     |       |    Milestone      |       |  TimeEntry       |
+------------------+       +-------------------+       +------------------+
| id               |       | id                |       | id               |
| name             |       | name              |       | task_id          |
| description      |       | description       |       | user_id          |
+------------------+       | project_id        |       | duration         |
                           | due_date          |       | description      |
                           | completed_date    |       | started_at       |
                           | is_completed      |       | ended_at         |
                           | created_by        |       | is_billable      |
                           | created_at        |       | created_at       |
                           | updated_at        |       | updated_at       |
                           +-------------------+       +------------------+
```

## Table Relationships

1. **User to Project** - Many-to-Many through ProjectMember
   - A user can be a member of multiple projects
   - A project can have multiple users as members

2. **Project to Task** - One-to-Many
   - A project has many tasks
   - A task belongs to exactly one project

3. **Project to ProjectStage** - One-to-Many
   - A project has multiple stages
   - A stage belongs to exactly one project

4. **ProjectStage to Task** - One-to-Many
   - A stage can have multiple tasks
   - A task belongs to at most one stage

5. **User to Role** - Many-to-Many through user_role
   - A user can have multiple roles
   - A role can be assigned to multiple users

6. **Role to Permission** - Many-to-Many through RolePermission
   - A role can have multiple permissions
   - A permission can be assigned to multiple roles

7. **Task to Task** - Hierarchical (Self-referential)
   - A task can have multiple subtasks
   - A subtask has at most one parent task

8. **Task to Task** - Dependency relationship
   - A task can depend on multiple tasks
   - A task can block multiple tasks

9. **User to Task** - Assignment relationship through TaskAssignment
   - A user can be assigned to multiple tasks
   - A task can be assigned to multiple users

10. **Milestone to Task** - One-to-Many
    - A milestone can have multiple tasks
    - A task belongs to at most one milestone

11. **User to TimeEntry** - One-to-Many
    - A user can have multiple time entries
    - A time entry belongs to exactly one user

12. **Task to TimeEntry** - One-to-Many
    - A task can have multiple time entries
    - A time entry belongs to exactly one task

## Key Design Decisions

1. **Extensibility**
   - Used JSONB for metadata fields to allow for custom attributes without schema changes
   - Created a comprehensive permission system for fine-grained access control

2. **Task Hierarchy**
   - Implemented both parent-child and dependency relationships for tasks
   - Provided status tracking and milestone associations

3. **Time Tracking**
   - Detailed time tracking system with billable hours
   - Duration stored in seconds for precision

4. **Project Organization**
   - Custom stages per project
   - Milestone tracking for important deliverables

5. **Collaboration Features**
   - Comment system with threading and mentions
   - Notification system for various events

This database schema provides a solid foundation for building the AI-enhanced project management system, with all the essential data structures in place to support the advanced features described in the roadmap. 