-- Ensure uuid-ossp extension is available (usually enabled by Supabase by default)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create sprints table
CREATE TABLE IF NOT EXISTS sprints (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL, -- e.g., 'planned', 'active', 'completed', 'cancelled'
    goal TEXT, -- Optional: A brief goal for the sprint
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create backlog_items table
CREATE TABLE IF NOT EXISTS backlog_items (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    status TEXT NOT NULL, -- e.g., 'backlog', 'ready', 'in_progress', 'done', 'blocked'
    priority TEXT NOT NULL, -- e.g., 'low', 'medium', 'high', 'urgent'
    points INTEGER DEFAULT 0,
    creator_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create backlog_item_tags table (for many-to-many relationship between backlog_items and tags)
CREATE TABLE IF NOT EXISTS backlog_item_tags (
    backlog_item_id UUID REFERENCES backlog_items(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (backlog_item_id, tag_id)
);

-- Create sprint_backlog table (junction table for sprints and backlog_items)
CREATE TABLE IF NOT EXISTS sprint_backlog (
    sprint_id UUID REFERENCES sprints(id) ON DELETE CASCADE,
    backlog_item_id UUID REFERENCES backlog_items(id) ON DELETE CASCADE,
    status TEXT, -- Status of the item within this specific sprint, can override backlog_item.status
    rank INTEGER, -- For ordering items within the sprint backlog
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sprint_id, backlog_item_id)
);

-- Basic RLS Policies (you may need to adjust these based on your app's security model)

-- Sprints
ALTER TABLE sprints ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access to authenticated users for sprints" ON sprints
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- Backlog Items
ALTER TABLE backlog_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can view all backlog items" ON backlog_items
    FOR SELECT
    USING (auth.role() = 'authenticated');
CREATE POLICY "Users can insert their own backlog items" ON backlog_items
    FOR INSERT
    WITH CHECK (auth.uid() = creator_id AND auth.role() = 'authenticated');
CREATE POLICY "Users can update their own backlog items" ON backlog_items
    FOR UPDATE
    USING (auth.uid() = creator_id AND auth.role() = 'authenticated');
CREATE POLICY "Users can delete their own backlog items" ON backlog_items
    FOR DELETE
    USING (auth.uid() = creator_id AND auth.role() = 'authenticated');


-- Backlog Item Tags
ALTER TABLE backlog_item_tags ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access to authenticated users for backlog_item_tags" ON backlog_item_tags
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');
-- More specific policies might be:
-- CREATE POLICY "Users can manage tags for their own backlog items" ON backlog_item_tags
--     FOR ALL
--     USING (EXISTS (
--         SELECT 1 FROM backlog_items bi WHERE bi.id = backlog_item_tags.backlog_item_id AND bi.creator_id = auth.uid()
--     ));


-- Sprint Backlog
ALTER TABLE sprint_backlog ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access to authenticated users for sprint_backlog" ON sprint_backlog
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');
-- More specific policies might be needed depending on how sprint assignments are managed.
-- For example, only allow users who are part of a "project" or "team" to modify sprint backlog.


-- Function to update 'updated_at' column
CREATE OR REPLACE FUNCTION public.trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger to tables that have 'updated_at'
-- (Assuming 'poppy_ideas_v2' and others from the initial schema also have updated_at)

CREATE TRIGGER set_sprints_updated_at
BEFORE UPDATE ON public.sprints
FOR EACH ROW EXECUTE FUNCTION public.trigger_set_timestamp();

CREATE TRIGGER set_backlog_items_updated_at
BEFORE UPDATE ON public.backlog_items
FOR EACH ROW EXECUTE FUNCTION public.trigger_set_timestamp();

COMMENT ON TABLE sprints IS 'Stores sprint details like name, duration, and status for project management.';
COMMENT ON TABLE backlog_items IS 'Stores product backlog items, including user stories, tasks, or bugs.';
COMMENT ON TABLE backlog_item_tags IS 'Associates tags with backlog items for categorization and filtering.';
COMMENT ON TABLE sprint_backlog IS 'Links backlog items to specific sprints, defines their order and status within the sprint.'; 