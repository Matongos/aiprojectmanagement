# Odoo Project Management Module: Technical Implementation Guide

## Database Structure and Architecture

### Core Models

1. **project.project**
   - Main project configuration model
   - Stores project metadata, settings, and configuration
   - Fields:
     - `name`: Project name
     - `active`: Boolean for active status
     - `user_id`: Project manager (res.users)
     - `partner_id`: Customer/client (res.partner)
     - `date_start`: Project start date
     - `date`: Project end date
     - `privacy_visibility`: Security level (portal/followers/employees)
     - `task_ids`: One2many relation to project.task
     - `stage_ids`: Many2many relation to project.task.type

2. **project.task**
   - Task management model
   - Stores individual task data and relationships
   - Fields:
     - `name`: Task title
     - `description`: Task description
     - `priority`: Task priority (0=Low, 1=Normal, 2=High)
     - `stage_id`: Current stage (Many2one to project.task.type)
     - `user_id`: Assigned user
     - `partner_id`: Related partner
     - `project_id`: Parent project
     - `date_start`: Start date
     - `date_deadline`: Deadline date
     - `planned_hours`: Estimated hours
     - `remaining_hours`: Hours left
     - `effective_hours`: Hours spent
     - `progress`: Percentage complete
     - `state`: Current state
     - `parent_id`: Parent task (for subtasks)
     - `child_ids`: Child tasks (subtasks)
     - `depend_on_ids`: Tasks this task depends on
     - `dependent_ids`: Tasks depending on this task

3. **project.task.type**
   - Stage definition model
   - Defines workflow stages for tasks
   - Fields:
     - `name`: Stage name
     - `sequence`: Order in workflow
     - `fold`: Whether folded in Kanban view
     - `project_ids`: Projects using this stage
     - `mail_template_id`: Email template for notifications
     - `is_closed`: Whether this is a closing stage
     - `auto_progress_percentage`: Default progress percentage

4. **project.tags**
   - Categorization tags for projects and tasks
   - Fields:
     - `name`: Tag name
     - `color`: Color index (for UI)

### Key Relationships

1. **Project-Task Relationship**
   - One project contains multiple tasks (one-to-many)
   - Tasks must belong to exactly one project (many-to-one)
   - Database constraint: Foreign key from `project_task.project_id` to `project_project.id`

2. **Task-Stage Relationship**
   - Tasks are assigned to one stage at a time
   - Stages can contain multiple tasks
   - Database constraint: Foreign key from `project_task.stage_id` to `project_task_type.id`

3. **Project-Stage Relationship**
   - Projects define which stages are available for their tasks
   - Many-to-many relationship
   - Junction table: `project_task_type_rel` with `project_id` and `type_id` fields

4. **Task Dependencies**
   - Tasks can depend on other tasks (blocking relationship)
   - Many-to-many self-referential relationship
   - Junction table: `task_dependencies_rel` with `task_id` and `depends_on_id` fields

5. **Task Hierarchy**
   - Tasks can have subtasks (parent-child relationship)
   - Recursive relationship within project.task model
   - Fields: `parent_id` and `child_ids`

## Task Workflow Management

### Stage Management

1. **Stage Definitions**
   - Stages define the workflow for tasks
   - Can be global or project-specific
   - Have sequence for ordering
   - Can be marked as "folded" for UI display

2. **Stage Transition Logic**
   ```python
   def move_to_next_stage(self):
       current_sequence = self.stage_id.sequence
       next_stage = self.env['project.task.type'].search([
           ('sequence', '>', current_sequence),
           ('project_ids', 'in', self.project_id.id)
       ], order='sequence', limit=1)
       if next_stage:
           self.stage_id = next_stage
   ```

3. **Stage Transition Effects**
   - Updates `date_last_stage_update` timestamp
   - Triggers email notifications if configured
   - May update task progress automatically
   - Logs the change in the chatter

### Task Status Management

1. **Task States**
   ```python
   TASK_STATES = {
       '01_in_progress': {
           'name': 'In Progress',
           'sequence': 10,
           'can_transition_to': ['02_changes_requested', '03_approved', '04_waiting_normal']
       },
       '02_changes_requested': {
           'name': 'Changes Requested',
           'sequence': 20,
           'can_transition_to': ['01_in_progress', '03_approved']
       },
       '03_approved': {
           'name': 'Approved',
           'sequence': 30,
           'can_transition_to': ['1_done']
       },
       '1_done': {
           'name': 'Done',
           'sequence': 40,
           'can_transition_to': []
       },
       '1_canceled': {
           'name': 'Canceled',
           'sequence': 50,
           'can_transition_to': ['01_in_progress']
       },
       '04_waiting_normal': {
           'name': 'Waiting',
           'sequence': 15,
           'can_transition_to': ['01_in_progress', '1_canceled']
       }
   }
   ```

2. **Kanban States**
   - Normal: Task is proceeding normally
   - Blocked: Task is blocked by external factors
   - Done: Task is ready for next stage

3. **Status Change Triggers**
   - Manual user action
   - Automated based on conditions
   - Timeline events (deadlines)
   - Dependency resolution

## Progress Tracking and Calculation

### Task Progress Calculation

1. **Based on timesheet entries**
   ```python
   def _compute_progress_hours(self):
       for task in self:
           if task.planned_hours > 0:
               task.progress = round(100.0 * task.effective_hours / task.planned_hours, 2)
           else:
               task.progress = 0.0
   ```

2. **Based on subtask completion**
   ```python
   def _compute_progress_from_subtasks(self):
       for task in self:
           if not task.child_ids:
               continue
           
           subtasks_count = len(task.child_ids)
           completed_subtasks = len(task.child_ids.filtered(lambda t: t.stage_id.is_closed))
           
           if subtasks_count:
               task.progress = (completed_subtasks / subtasks_count) * 100
   ```

3. **Stage-based automatic progress**
   - Stages can define default progress values
   - When task enters that stage, progress is updated

### Project Progress Calculation

1. **Aggregation of task progress**
   ```python
   def _compute_project_progress(self):
       for project in self:
           if not project.task_ids:
               project.progress = 0.0
               continue
               
           total_progress = sum(task.progress for task in project.task_ids)
           project.progress = total_progress / len(project.task_ids)
   ```

2. **Weighted by task priority/complexity**
   ```python
   def _compute_weighted_progress(self):
       for project in self:
           if not project.task_ids:
               project.weighted_progress = 0.0
               continue
               
           total_planned = sum(task.planned_hours for task in project.task_ids)
           
           if total_planned:
               weighted_progress = sum((task.progress * task.planned_hours) for task in project.task_ids)
               project.weighted_progress = weighted_progress / total_planned
           else:
               project.weighted_progress = 0.0
   ```

### Stage Completion Tracking

1. **Task counts by stage**
   ```python
   def _compute_task_count(self):
       for stage in self:
           stage.task_count = self.env['project.task'].search_count([
               ('stage_id', '=', stage.id)
           ])
   ```

2. **Stage transition times**
   ```python
   def calculate_avg_time_in_stage(self):
       tasks = self.task_ids.filtered(lambda t: t.date_last_stage_update)
       if not tasks:
           return 0.0
       
       now = fields.Datetime.now()
       total_time = sum((now - task.date_last_stage_update).total_seconds() for task in tasks)
       return total_time / len(tasks) / 3600  # Convert to hours
   ```

## How Moving Tasks Between Stages Works

### Task Movement Process

1. **User Interface Interaction**
   - Drag and drop in Kanban view
   - Selection change in form view
   - Automated stage transitions
   - API calls

2. **Stage Change Handling**
   ```python
   def write(self, vals):
       # Track if stage is changing
       if 'stage_id' in vals:
           for task in self:
               # Record old stage
               old_stage_id = task.stage_id.id
               # Call super to update the record
               result = super(Task, task).write(vals)
               # Handle post-stage change actions
               task._handle_stage_change(old_stage_id)
               return result
       return super(Task, self).write(vals)
   
   def _handle_stage_change(self, old_stage_id):
       # Update last stage change date
       self.date_last_stage_update = fields.Datetime.now()
       
       # Check if moving to a closed stage
       if self.stage_id.is_closed:
           self.date_end = fields.Datetime.now()
       
       # Update automatic progress if configured
       if self.stage_id.auto_progress_percentage:
           self.progress = self.stage_id.auto_progress_percentage
       
       # Send notifications if configured
       if self.stage_id.mail_template_id:
           self.stage_id.mail_template_id.send_mail(self.id)
   ```

3. **Stage Change Validation**
   ```python
   def _check_stage_transition(self, target_stage):
       # Check dependencies
       if target_stage.is_closed and self.depend_on_ids:
           uncompleted_deps = self.depend_on_ids.filtered(lambda t: not t.stage_id.is_closed)
           if uncompleted_deps:
               raise ValidationError(_("Cannot close task with uncompleted dependencies"))
       
       # Check required fields
       if target_stage.required_field_ids:
           for field in target_stage.required_field_ids:
               if not self[field.name]:
                   raise ValidationError(_("Field %s is required to move to this stage") % field.field_description)
       
       return True
   ```

### Project Stage Progress Bars

1. **Progress Bar Calculation**
   - Based on tasks in each stage
   - Percentage of total tasks
   - Color-coded for visibility
   - Real-time updates

2. **Implementation**
   ```python
   def _compute_stage_progress(self):
       for project in self:
           tasks_count = len(project.task_ids)
           if not tasks_count:
               continue
               
           for stage in project.stage_ids:
               stage_tasks = len(project.task_ids.filtered(lambda t: t.stage_id.id == stage.id))
               stage.progress_percentage = (stage_tasks / tasks_count) * 100
   ```

3. **UI Representation**
   ```xml
   <kanban class="o_kanban_project_stages">
       <field name="name"/>
       <field name="progress_percentage"/>
       <templates>
           <t t-name="kanban-box">
               <div class="o_project_stage_kanban">
                   <div class="o_kanban_card_header">
                       <field name="name"/>
                   </div>
                   <div class="o_kanban_card_content">
                       <div class="o_progress">
                           <div class="o_progressbar" t-attf-style="width: {{record.progress_percentage.value}}%"/>
                       </div>
                       <div class="o_tasks_count">
                           <t t-esc="record.task_count.value"/> Tasks
                       </div>
                   </div>
               </div>
           </t>
       </templates>
   </kanban>
   ```

## Technical Implementation of Key Features

### Task Dependencies

1. **Database Structure**
   ```sql
   CREATE TABLE task_dependencies_rel (
       task_id INTEGER REFERENCES project_task(id) ON DELETE CASCADE,
       depends_on_id INTEGER REFERENCES project_task(id) ON DELETE CASCADE,
       PRIMARY KEY (task_id, depends_on_id)
   );
   ```

2. **Field Definition**
   ```python
   depend_on_ids = fields.Many2many(
       'project.task',
       relation="task_dependencies_rel",
       column1="task_id",
       column2="depends_on_id",
       string="Blocked By"
   )
   dependent_ids = fields.Many2many(
       'project.task',
       relation="task_dependencies_rel",
       column1="depends_on_id",
       column2="task_id",
       string="Block"
   )
   ```

3. **Dependency Validation**
   ```python
   def _check_dependency_recursion(self):
       if not self:
           return True
       self.ensure_one()
       visited = self.browse()
       todo = self.browse() + self
       while todo:
           current = todo - visited
           visited = visited + current
           todo = current.mapped('depend_on_ids')
           if current & todo:
               raise ValidationError(_("Circular task dependency detected"))
       return True
   ```

### Task Status Management

1. **Status Field Definition**
   ```python
   state = fields.Selection([
       ('01_in_progress', 'In Progress'),
       ('02_changes_requested', 'Changes Requested'),
       ('03_approved', 'Approved'),
       ('1_done', 'Done'),
       ('1_canceled', 'Canceled'),
       ('04_waiting_normal', 'Waiting')
   ], default='01_in_progress', tracking=True)
   ```

2. **Status Change Method**
   ```python
   def change_state(self, new_state):
       self.ensure_one()
       valid_transitions = TASK_STATES[self.state]['can_transition_to']
       if new_state not in valid_transitions:
           raise ValidationError(_("Cannot transition from %s to %s") % 
                                (TASK_STATES[self.state]['name'], TASK_STATES[new_state]['name']))
       self.state = new_state
       
       # Perform state-specific actions
       if new_state == '1_done':
           self.date_end = fields.Datetime.now()
       elif new_state == '01_in_progress' and self.date_end:
           self.date_end = False
   ```

### Automatic Progress Calculation

1. **Based on Time Tracking**
   ```python
   @api.depends('effective_hours', 'planned_hours')
   def _compute_progress_hours(self):
       for task in self:
           if task.planned_hours > 0:
               task.progress = (task.effective_hours / task.planned_hours) * 100
           else:
               task.progress = 0.0
   ```

2. **Based on Subtasks**
   ```python
   @api.depends('child_ids.stage_id', 'child_ids.stage_id.is_closed')
   def _compute_subtask_progress(self):
       for task in self:
           if not task.child_ids:
               continue
           
           total_subtasks = len(task.child_ids)
           completed_subtasks = len(task.child_ids.filtered(lambda t: t.stage_id.is_closed))
           
           task.subtask_progress = (completed_subtasks / total_subtasks) * 100 if total_subtasks else 0.0
   ```

## Best Practices for Development

### 1. Database Design

- Follow Odoo's naming conventions (snake_case for fields, dot.notation for models)
- Use appropriate field types (Many2one, One2many, Many2many for relationships)
- Add indexes for frequently queried fields
- Set up proper constraints to maintain data integrity
- Define clear dependencies between modules

### 2. Business Logic Implementation

- Separate concerns into model methods
- Use computed fields for derived data
- Employ decorators like `@api.depends` to trigger recomputation
- Implement proper validation using constraints
- Use Odoo's ORM methods instead of raw SQL when possible

### 3. User Interface Considerations

- Design intuitive Kanban views for task management
- Implement progress bars for visual tracking
- Use color coding for status and priority
- Provide filtering and grouping options
- Consider mobile usability

### 4. Security Implementation

- Define proper access rights at model and record levels
- Implement record rules for fine-grained control
- Consider multi-company scenarios
- Validate input data to prevent security issues
- Handle sensitive data appropriately

### 5. Performance Optimization

- Index frequently searched fields
- Use prefetching for related records
- Batch process records when possible
- Implement pagination for large record sets
- Use `sudo()` judiciously

## Building a Similar System with Other Technologies

### 1. Core Components to Implement

- Project management model
- Task tracking system
- Stage/workflow management
- User assignment and notifications
- Progress tracking and reporting
- Time tracking integration
- File attachment system

### 2. Database Schema Design

- Project table with metadata
- Task table with relationship to projects
- Stage/status tables for workflow
- Join tables for many-to-many relationships
- Tracking tables for history and analytics

### 3. Key Backend Features

- RESTful API for CRUD operations
- Business logic for stage transitions
- Validation rules for task dependencies
- Progress calculation algorithms
- Notification system for updates
- Authentication and authorization

### 4. Frontend Requirements

- Kanban board for visual task management
- Project overview dashboards
- Drag-and-drop functionality
- Progress visualization
- Filtering and sorting capabilities
- Responsive design for multi-device use

### 5. Integration Considerations

- Calendar synchronization
- Email integration
- Document management
- Time tracking systems
- Reporting and analytics tools
- Authentication systems

### 6. Deployment and Scaling

- Database optimization
- Caching strategies
- Background processing for notifications
- Load balancing for high usage
- Backup and recovery procedures

By understanding Odoo's project management implementation, developers can create similar systems using different technology stacks while maintaining the core functionality and user experience that makes project management effective. 