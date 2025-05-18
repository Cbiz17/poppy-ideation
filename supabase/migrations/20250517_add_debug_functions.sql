-- Create function to get table information
CREATE OR REPLACE FUNCTION get_table_info(table_name TEXT)
RETURNS TABLE (
    table_exists BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = $1
    );
END;
$$ LANGUAGE plpgsql;

-- Create function to get column information
CREATE OR REPLACE FUNCTION get_columns(table_name TEXT)
RETURNS TABLE (
    column_name TEXT,
    data_type TEXT,
    is_nullable BOOLEAN,
    is_primary_key BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.column_name::TEXT,
        c.udt_name::TEXT,
        c.is_nullable = 'YES',
        EXISTS(
            SELECT 1
            FROM information_schema.key_column_usage kcu
            WHERE kcu.table_name = $1
            AND kcu.column_name = c.column_name
            AND kcu.constraint_name IN (
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = $1
                AND constraint_type = 'PRIMARY KEY'
            )
        )
    FROM information_schema.columns c
    WHERE c.table_name = $1
    AND c.table_schema = 'public';
END;
$$ LANGUAGE plpgsql;

-- Create function to get foreign key information
CREATE OR REPLACE FUNCTION get_foreign_keys(table_name TEXT)
RETURNS TABLE (
    constraint_name TEXT,
    column_name TEXT,
    foreign_table_name TEXT,
    foreign_column_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tc.constraint_name::TEXT,
        kcu.column_name::TEXT,
        ccu.table_name::TEXT,
        ccu.column_name::TEXT
    FROM information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu 
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu 
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = $1
    AND tc.table_schema = 'public';
END;
$$ LANGUAGE plpgsql;
