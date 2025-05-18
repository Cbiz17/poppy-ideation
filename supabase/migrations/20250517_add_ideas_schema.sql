-- Enable pgcrypto so we can use gen_random_uuid()
create extension if not exists "pgcrypto";
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create statuses table
CREATE TABLE statuses (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER NOT NULL,  -- Renamed from "order" to "display_order"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create priorities table
CREATE TABLE priorities (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER NOT NULL,  -- Renamed from "order" to "display_order"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create categories table
CREATE TABLE categories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    parent_id UUID REFERENCES categories(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create tags table
CREATE TABLE tags (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create main ideas table
CREATE TABLE poppy_ideas_v2 (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category_id UUID REFERENCES categories(id),
    status_id UUID REFERENCES statuses(id),
    priority_id UUID REFERENCES priorities(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    creator_id UUID REFERENCES auth.users(id),
    source TEXT,
    context TEXT,
    metadata JSONB
);

-- Create idea-tags relationship table
CREATE TABLE idea_tags (
    idea_id UUID REFERENCES poppy_ideas_v2(id),
    tag_id UUID REFERENCES tags(id),
    PRIMARY KEY (idea_id, tag_id)
);

-- Create comments table
CREATE TABLE comments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    idea_id UUID REFERENCES poppy_ideas_v2(id),
    parent_id UUID REFERENCES comments(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    creator_id UUID REFERENCES auth.users(id)
);

-- Create related ideas table
CREATE TABLE related_ideas (
    idea1_id UUID REFERENCES poppy_ideas_v2(id),
    idea2_id UUID REFERENCES poppy_ideas_v2(id),
    relationship_type TEXT,
    description TEXT,
    PRIMARY KEY (idea1_id, idea2_id)
);

-- Insert default statuses
INSERT INTO statuses (name, description, display_order) VALUES
('New', 'Freshly created idea', 1),
('In Progress', 'Being worked on', 2),
('Blocked', 'Waiting for something', 3),
('Completed', 'Successfully implemented', 4),
('Archived', 'No longer active', 5);

-- Insert default priorities
INSERT INTO priorities (name, description, display_order) VALUES
('Low', 'Low priority', 1),
('Medium', 'Medium priority', 2),
('High', 'High priority', 3),
('Urgent', 'Needs immediate attention', 4);

-- Insert default categories
INSERT INTO categories (name, description) VALUES
('Product', 'Product-related ideas'),
('Marketing', 'Marketing and growth ideas'),
('Engineering', 'Technical improvements'),
('Operations', 'Operational improvements');

-- Create RLS policies
ALTER TABLE poppy_ideas_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE related_ideas ENABLE ROW LEVEL SECURITY;

-- Ideas policies
CREATE POLICY "Users can view their own ideas" ON poppy_ideas_v2
    FOR SELECT
    USING (auth.uid() = creator_id);

CREATE POLICY "Users can create ideas" ON poppy_ideas_v2
    FOR INSERT
    WITH CHECK (auth.uid() = creator_id);

CREATE POLICY "Users can update their own ideas" ON poppy_ideas_v2
    FOR UPDATE
    USING (auth.uid() = creator_id);

-- Comments policies
CREATE POLICY "Users can view comments on their ideas" ON comments
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM poppy_ideas_v2 WHERE poppy_ideas_v2.id = comments.idea_id AND poppy_ideas_v2.creator_id = auth.uid()
    ));

CREATE POLICY "Users can create comments on their ideas" ON comments
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM poppy_ideas_v2 WHERE poppy_ideas_v2.id = comments.idea_id AND poppy_ideas_v2.creator_id = auth.uid()
    ));

-- Related ideas policies
CREATE POLICY "Users can view related ideas for their ideas" ON related_ideas
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM poppy_ideas_v2 WHERE poppy_ideas_v2.id = related_ideas.idea1_id AND poppy_ideas_v2.creator_id = auth.uid()
    ));

CREATE POLICY "Users can create related ideas for their ideas" ON related_ideas
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM poppy_ideas_v2 WHERE poppy_ideas_v2.id = related_ideas.idea1_id AND poppy_ideas_v2.creator_id = auth.uid()
    ));