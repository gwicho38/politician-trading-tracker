-- Fix missing user_id columns
-- Run this FIRST, then run the main migration

-- Check and add user_id to notifications if missing
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id UUID;

-- Check and add user_id to trading_orders if missing
ALTER TABLE trading_orders ADD COLUMN IF NOT EXISTS user_id UUID;

-- Recreate user_roles with correct schema
DROP TABLE IF EXISTS user_roles CASCADE;
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role)
);

SELECT 'user_id columns fixed!' as status;
