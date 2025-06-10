-- Create task_risks table
CREATE TABLE IF NOT EXISTS task_risks (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    risk_score FLOAT NOT NULL,
    risk_level VARCHAR NOT NULL,
    time_sensitivity FLOAT NOT NULL,
    complexity FLOAT NOT NULL,
    priority FLOAT NOT NULL,
    risk_factors JSONB,
    recommendations JSONB,
    metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_task_risks_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_task_risks_task_id ON task_risks(task_id);
CREATE INDEX IF NOT EXISTS ix_task_risks_created_at ON task_risks(created_at); 