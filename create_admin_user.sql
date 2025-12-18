-- Create admin user for luis@lefv.io
-- This script assumes the user has already signed up in Supabase Auth

-- First, get the user ID from auth.users for luis@lefv.io
-- You'll need to replace 'USER_ID_HERE' with the actual UUID from Supabase Auth

-- Insert admin role for the user
INSERT INTO public.user_roles (user_id, role) 
VALUES (
    'USER_ID_HERE', -- Replace with actual user ID from auth.users
    'admin'
) ON CONFLICT (user_id, role) DO NOTHING;

-- Verify the admin role was created
SELECT 
    ur.user_id,
    ur.role,
    au.email,
    ur.created_at
FROM public.user_roles ur
JOIN auth.users au ON ur.user_id = au.id
WHERE au.email = 'luis@lefv.io';
