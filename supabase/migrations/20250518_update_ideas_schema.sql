-- Add due_date column and remove rank
ALTER TABLE poppy_ideas_v2
ADD COLUMN due_date DATE,
DROP COLUMN rank;

-- Add index for due_date
CREATE INDEX idx_poppy_ideas_v2_due_date ON poppy_ideas_v2(due_date);
