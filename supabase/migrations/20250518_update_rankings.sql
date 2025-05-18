-- Update rankings based on creation date (newer ideas get higher ranks)
WITH ranked_ideas AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY created_at DESC) as rank
    FROM poppy_ideas_v2
)
UPDATE poppy_ideas_v2
SET rank = ranked_ideas.rank
FROM ranked_ideas
WHERE poppy_ideas_v2.id = ranked_ideas.id;
