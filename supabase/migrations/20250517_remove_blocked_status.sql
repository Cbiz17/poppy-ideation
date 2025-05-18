-- Remove blocked status
DELETE FROM statuses WHERE name = 'Blocked';

-- Verify deletion
SELECT name FROM statuses;
