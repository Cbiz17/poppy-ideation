-- Create statuses table
CREATE TABLE IF NOT EXISTS statuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default statuses
INSERT INTO statuses (name) VALUES
    ('New'),
    ('In Progress'),
    ('Completed'),
    ('Archived')
ON CONFLICT (name) DO NOTHING;

-- Enable RLS
ALTER TABLE statuses ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Public statuses view" ON statuses
    FOR SELECT
    USING (true);

CREATE POLICY "Public statuses insert" ON statuses
    FOR INSERT
    WITH CHECK (true);
