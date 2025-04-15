-- Check if user exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'matongo' OR email = 'matongo@example.com') THEN
        -- Insert superuser with bcrypt hashed password
        INSERT INTO users (
            username,
            email,
            full_name,
            hashed_password,
            is_active,
            is_superuser,
            created_at,
            updated_at
        ) VALUES (
            'matongo',
            'matongo@example.com',
            'matongo matongo',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYpwBAHHKQS.pmS', -- This is the hash for 'matongo'
            true,
            true,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );
        RAISE NOTICE 'Superuser created successfully';
    ELSE
        RAISE NOTICE 'User already exists';
    END IF;
END $$; 