# Tags System Implementation Roadmap

## 1. Database Structure

### 1.1 Core Tables

```sql
-- Main tags table
CREATE TABLE project_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    color INTEGER,
    active BOOLEAN DEFAULT true,
    create_uid INTEGER REFERENCES res_users(id),
    create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    write_uid INTEGER REFERENCES res_users(id),
    write_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project-Tags relation table
CREATE TABLE project_project_tags_rel (
    project_id INTEGER REFERENCES project_project(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES project_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, tag_id)
);

-- Task-Tags relation table
CREATE TABLE project_task_tags_rel (
    task_id INTEGER REFERENCES project_task(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES project_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, tag_id)
);
```

### 1.2 Indexes for Performance

```sql
-- Indexes for faster lookups
CREATE INDEX project_tags_name_index ON project_tags(name);
CREATE INDEX project_tags_active_index ON project_tags(active);
CREATE INDEX project_project_tags_rel_project_id_index ON project_project_tags_rel(project_id);
CREATE INDEX project_project_tags_rel_tag_id_index ON project_project_tags_rel(tag_id);
CREATE INDEX project_task_tags_rel_task_id_index ON project_task_tags_rel(task_id);
CREATE INDEX project_task_tags_rel_tag_id_index ON project_task_tags_rel(tag_id);
```

## 2. Python Models

### 2.1 Tag Model

```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProjectTags(models.Model):
    _name = 'project.tags'
    _description = 'Project Tags'
    _order = 'name'

    name = fields.Char(
        string='Tag Name',
        required=True,
        translate=True,
        index=True
    )
    color = fields.Integer(
        string='Color Index',
        default=lambda self: randint(1, 11)
    )
    active = fields.Boolean(
        default=True,
        help="If the active field is set to False, it will allow you to hide"
             "the tag without removing it."
    )
    project_ids = fields.Many2many(
        'project.project',
        'project_project_tags_rel',
        'tag_id',
        'project_id',
        string='Projects'
    )
    task_ids = fields.Many2many(
        'project.task',
        'project_task_tags_rel',
        'tag_id',
        'task_id',
        string='Tasks'
    )
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if not record.name:
                raise ValidationError('Tag name cannot be empty')
            if len(record.name) > 50:
                raise ValidationError('Tag name cannot exceed 50 characters')

    def unlink(self):
        """Archive tags instead of deleting if they are being used"""
        tags_in_use = self.filtered(lambda tag: tag.project_ids or tag.task_ids)
        if tags_in_use:
            tags_in_use.write({'active': False})
            return (self - tags_in_use).unlink()
        return super(ProjectTags, self).unlink()
```

### 2.2 Project Model Extension

```python
class Project(models.Model):
    _inherit = 'project.project'

    tag_ids = fields.Many2many(
        'project.tags',
        'project_project_tags_rel',
        'project_id',
        'tag_id',
        string='Tags'
    )

    def write(self, vals):
        """Override to handle tag updates"""
        if 'tag_ids' in vals:
            self._handle_tag_changes(vals['tag_ids'])
        return super(Project, self).write(vals)

    def _handle_tag_changes(self, tag_commands):
        """Handle tag changes and trigger necessary updates"""
        for command in tag_commands:
            if command[0] == 4:  # Add tag
                self._on_tag_added(command[1])
            elif command[0] == 3:  # Remove tag
                self._on_tag_removed(command[1])

    def _on_tag_added(self, tag_id):
        """Hook for tag addition"""
        pass

    def _on_tag_removed(self, tag_id):
        """Hook for tag removal"""
        pass
```

### 2.3 Task Model Extension

```python
class ProjectTask(models.Model):
    _inherit = 'project.task'

    tag_ids = fields.Many2many(
        'project.tags',
        'project_task_tags_rel',
        'task_id',
        'tag_id',
        string='Tags'
    )

    def write(self, vals):
        """Override to handle tag updates"""
        if 'tag_ids' in vals:
            self._handle_tag_changes(vals['tag_ids'])
        return super(ProjectTask, self).write(vals)

    def _handle_tag_changes(self, tag_commands):
        """Handle tag changes and trigger necessary updates"""
        for command in tag_commands:
            if command[0] == 4:  # Add tag
                self._on_tag_added(command[1])
            elif command[0] == 3:  # Remove tag
                self._on_tag_removed(command[1])

    def _on_tag_added(self, tag_id):
        """Hook for tag addition"""
        pass

    def _on_tag_removed(self, tag_id):
        """Hook for tag removal"""
        pass
```

## 3. Views

### 3.1 Tag Form View

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="project_tags_form_view" model="ir.ui.view">
        <field name="name">project.tags.form</field>
        <field name="model">project.tags</field>
        <field name="arch" type="xml">
            <form string="Project Tag">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="color" widget="color_picker"/>
                        <field name="active"/>
                    </group>
                    <notebook>
                        <page string="Projects">
                            <field name="project_ids"/>
                        </page>
                        <page string="Tasks">
                            <field name="task_ids"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>
</odoo>
```

### 3.2 Tag Tree View

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="project_tags_tree_view" model="ir.ui.view">
        <field name="name">project.tags.tree</field>
        <field name="model">project.tags</field>
        <field name="arch" type="xml">
            <tree string="Project Tags">
                <field name="name"/>
                <field name="color" widget="color_picker"/>
                <field name="project_ids" widget="many2many_tags"/>
                <field name="task_ids" widget="many2many_tags"/>
            </tree>
        </field>
    </record>
</odoo>
```

### 3.3 Tag Search View

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="project_tags_search_view" model="ir.ui.view">
        <field name="name">project.tags.search</field>
        <field name="model">project.tags</field>
        <field name="arch" type="xml">
            <search string="Search Tags">
                <field name="name"/>
                <filter string="Archived" name="inactive" domain="[('active', '=', False)]"/>
                <group expand="0" string="Group By">
                    <filter string="Color" name="color" context="{'group_by': 'color'}"/>
                </group>
            </search>
        </field>
    </record>
</odoo>
```

## 4. Security

### 4.1 Access Rights

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="project_tags_rule_global" model="ir.rule">
        <field name="name">Project Tags: Global</field>
        <field name="model_id" ref="model_project_tags"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <record id="access_project_tags_user" model="ir.model.access">
        <field name="name">project.tags.user</field>
        <field name="model_id" ref="model_project_tags"/>
        <field name="group_id" ref="project.group_project_user"/>
        <field name="perm_read" eval="1"/>
        <field name="perm_write" eval="1"/>
        <field name="perm_create" eval="1"/>
        <field name="perm_unlink" eval="1"/>
    </record>
</odoo>
```

## 5. CRUD Operations Guide

### 5.1 Creating Tags

```python
def create_tag(self, name, color=None):
    """Create a new project tag"""
    return self.env['project.tags'].create({
        'name': name,
        'color': color or random.randint(1, 11)
    })

# Usage example
new_tag = create_tag('High Priority', 1)  # Red color
```

### 5.2 Reading Tags

```python
def get_tags(self, domain=None):
    """Get tags based on domain"""
    if domain is None:
        domain = [('active', '=', True)]
    return self.env['project.tags'].search(domain)

# Usage examples
all_active_tags = get_tags()
specific_tag = get_tags([('name', '=', 'High Priority')])
```

### 5.3 Updating Tags

```python
def update_tag(self, tag_id, values):
    """Update existing tag"""
    tag = self.env['project.tags'].browse(tag_id)
    return tag.write(values)

# Usage example
update_tag(tag_id, {'name': 'Very High Priority', 'color': 2})
```

### 5.4 Deleting Tags

```python
def delete_tag(self, tag_id):
    """Delete/Archive tag"""
    tag = self.env['project.tags'].browse(tag_id)
    return tag.unlink()  # Will archive if in use

# Usage example
delete_tag(tag_id)
```

### 5.5 Assigning Tags

```python
def assign_tag_to_project(self, project_id, tag_id):
    """Assign tag to project"""
    project = self.env['project.project'].browse(project_id)
    return project.write({
        'tag_ids': [(4, tag_id)]
    })

def assign_tag_to_task(self, task_id, tag_id):
    """Assign tag to task"""
    task = self.env['project.task'].browse(task_id)
    return task.write({
        'tag_ids': [(4, tag_id)]
    })

# Usage examples
assign_tag_to_project(project_id, tag_id)
assign_tag_to_task(task_id, tag_id)
```

## 6. Implementation Steps

1. Create database tables using SQL scripts from Section 1
2. Implement Python models from Section 2
3. Create views from Section 3
4. Set up security rules from Section 4
5. Test CRUD operations using examples from Section 5

## 7. Best Practices

1. Always validate tag names before creation
2. Use color indices 1-11 for consistency with Odoo
3. Archive tags instead of deleting when in use
4. Use proper indexes for performance
5. Implement proper security measures
6. Handle tag changes through proper hooks
7. Use translation capabilities for multi-language support

## 8. Performance Considerations

1. Use appropriate indexes
2. Implement lazy loading for tag relations
3. Cache frequently used tags
4. Use proper search domains
5. Implement batch operations for multiple tags

## 9. Maintenance

1. Regularly clean up unused tags
2. Monitor tag usage patterns
3. Update color schemes as needed
4. Maintain proper documentation
5. Regular security audits

## 10. Testing

1. Unit tests for CRUD operations
2. Integration tests for tag assignments
3. Performance tests for large datasets
4. Security tests for access controls
5. UI tests for tag management interface 