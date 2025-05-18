-- Add rank column to ideas table
ALTER TABLE poppy_ideas_v2
ADD COLUMN rank INTEGER DEFAULT 0;

-- Add index for better performance
CREATE INDEX idx_poppy_ideas_v2_rank ON poppy_ideas_v2(rank);
