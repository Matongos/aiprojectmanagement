# Odoo Project Management Reporting Technical Guide

## Table of Contents
1. [Overview](#overview)
2. [Data Sources](#data-sources)
3. [Report Types](#report-types)
4. [Implementation Guide](#implementation-guide)
5. [UI/UX Best Practices](#uiux-best-practices)
6. [Responsive Design](#responsive-design)
7. [Customization](#customization)
8. [Performance Optimization](#performance-optimization)

## Overview

Odoo's project management reporting system provides comprehensive analytics and insights through various visualization methods. This guide explains the technical implementation and best practices.

## Data Sources

### 1. Core Models
```python
# Main reporting models
- report.project.task.user    # Task analysis
- timesheets.analysis.report  # Timesheet analysis
- project.task               # Task data
- project.project           # Project data
```

### 2. Data Collection Methods
```python
# Example of data aggregation
class ProjectTaskUser(models.Model):
    _name = "report.project.task.user"
    _auto = False  # This is a database view
    
    # Key metrics
    working_hours_open = fields.Float("Working Hours to Assign")
    working_hours_close = fields.Float("Working Hours to Close")
    nbr = fields.Integer('# of Tasks', readonly=True)
    rating_avg = fields.Float("Average Rating")
```

## Report Types

### 1. Task Analysis
```xml
<record id="view_task_project_user_pivot" model="ir.ui.view">
    <field name="model">report.project.task.user</field>
    <field name="arch" type="xml">
        <pivot string="Tasks Analysis" display_quantity="1">
            <field name="project_id" type="row"/>
            <field name="stage_id" type="col"/>
            <field name="nbr" type="measure"/>
        </pivot>
    </field>
</record>
```

### 2. Timesheet Analysis
```xml
<record id="timesheets_analysis_report_pivot" model="ir.ui.view">
    <field name="model">timesheets.analysis.report</field>
    <field name="arch" type="xml">
        <pivot string="Timesheets Analysis">
            <field name="employee_id" type="row"/>
            <field name="date" interval="month" type="col"/>
            <field name="unit_amount" type="measure"/>
        </pivot>
    </field>
</record>
```

## Implementation Guide

### 1. Creating Custom Reports

```python
class CustomProjectReport(models.Model):
    _name = 'custom.project.report'
    _auto = False
    _description = 'Custom Project Report'

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT
                    t.id,
                    t.name,
                    t.project_id,
                    t.user_id,
                    t.stage_id,
                    t.working_hours_open,
                    t.working_hours_close
                FROM project_task t
            )
        """ % self._table)
```

### 2. Adding Visualization Views

```xml
<!-- Pivot View -->
<record id="custom_project_report_pivot" model="ir.ui.view">
    <field name="name">custom.project.report.pivot</field>
    <field name="model">custom.project.report</field>
    <field name="arch" type="xml">
        <pivot string="Project Analysis">
            <field name="project_id" type="row"/>
            <field name="working_hours_open" type="measure"/>
        </pivot>
    </field>
</record>

<!-- Graph View -->
<record id="custom_project_report_graph" model="ir.ui.view">
    <field name="name">custom.project.report.graph</field>
    <field name="model">custom.project.report</field>
    <field name="arch" type="xml">
        <graph string="Project Analysis">
            <field name="project_id"/>
            <field name="working_hours_open" type="measure"/>
        </graph>
    </field>
</record>
```

## UI/UX Best Practices

### 1. CSS Framework
```scss
// Project reporting specific styles
.o_project_report {
    // Container styles
    .report_container {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 1.5rem;
        
        @media (min-width: 768px) {
            flex-direction: row;
        }
    }

    // Chart styles
    .chart_container {
        flex: 1;
        min-height: 300px;
        background: #fff;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        
        &:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
    }

    // Responsive table styles
    .report_table {
        width: 100%;
        overflow-x: auto;
        
        table {
            min-width: 600px;
            border-collapse: collapse;
            
            th, td {
                padding: 0.75rem;
                border-bottom: 1px solid #eee;
            }
        }
    }
}
```

### 2. JavaScript Enhancements
```javascript
odoo.define('custom.project.reporting', function (require) {
    "use strict";

    var core = require('web.core');
    var GraphView = require('web.GraphView');

    var CustomProjectGraph = GraphView.extend({
        configure_chart: function () {
            // Custom chart configuration
            var options = {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            };
            return options;
        }
    });
});
```

## Responsive Design

### 1. Grid System
```scss
.o_project_dashboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    padding: 1rem;

    .dashboard_card {
        background: #fff;
        border-radius: 8px;
        padding: 1rem;
        
        @media (max-width: 767px) {
            grid-column: 1 / -1;
        }
    }
}
```

### 2. Breakpoints
```scss
// Define breakpoints
$breakpoints: (
    'sm': 576px,
    'md': 768px,
    'lg': 992px,
    'xl': 1200px
);

// Mixins for responsive design
@mixin respond-to($breakpoint) {
    @if map-has-key($breakpoints, $breakpoint) {
        @media (min-width: map-get($breakpoints, $breakpoint)) {
            @content;
        }
    }
}
```

## Customization

### 1. Adding Custom Measures
```python
class CustomProjectReport(models.Model):
    _inherit = 'report.project.task.user'

    custom_metric = fields.Float(
        string='Custom Metric',
        compute='_compute_custom_metric',
        store=True
    )

    @api.depends('working_hours_open', 'working_hours_close')
    def _compute_custom_metric(self):
        for record in self:
            record.custom_metric = record.working_hours_close - record.working_hours_open
```

### 2. Custom Filters
```xml
<record id="custom_project_report_search" model="ir.ui.view">
    <field name="name">custom.project.report.search</field>
    <field name="model">custom.project.report</field>
    <field name="arch" type="xml">
        <search>
            <field name="project_id"/>
            <field name="user_id"/>
            <filter string="My Projects" 
                    name="my_projects" 
                    domain="[('user_id', '=', uid)]"/>
            <group expand="0" string="Group By">
                <filter string="Project" 
                        name="group_project" 
                        context="{'group_by': 'project_id'}"/>
            </group>
        </search>
    </field>
</record>
```

## Performance Optimization

### 1. Query Optimization
```python
def init(self):
    tools.drop_view_if_exists(self.env.cr, self._table)
    self.env.cr.execute("""
        CREATE or REPLACE VIEW %s as (
            SELECT
                t.id,
                t.name,
                t.project_id,
                -- Use indexes
                COALESCE(t.user_id, 0) as user_id,
                -- Optimize date calculations
                date_trunc('day', t.create_date) as date
            FROM project_task t
            -- Use JOIN instead of subqueries
            INNER JOIN project_project p ON t.project_id = p.id
            WHERE t.active = true
        )
    """ % self._table)
```

### 2. Caching
```python
class CustomProjectReport(models.Model):
    _name = 'custom.project.report'
    
    @api.model
    @tools.ormcache('user_id', 'date_from', 'date_to')
    def get_report_data(self, user_id, date_from, date_to):
        # Cache report data for better performance
        return self.search_read([
            ('user_id', '=', user_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
```

### 3. Lazy Loading
```javascript
odoo.define('custom.project.reporting', function (require) {
    "use strict";

    var CustomDashboard = require('web.AbstractAction').extend({
        start: function () {
            return Promise.all([
                this._super.apply(this, arguments),
                this._loadInitialData()
            ]);
        },

        _loadInitialData: function () {
            // Load only essential data initially
            return this._rpc({
                model: 'custom.project.report',
                method: 'get_summary_data',
            }).then(function (result) {
                // Handle initial data
            });
        },

        _loadDetailedData: function () {
            // Load detailed data on demand
            return this._rpc({
                model: 'custom.project.report',
                method: 'get_detailed_data',
            });
        }
    });
});
``` 