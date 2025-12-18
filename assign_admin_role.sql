-- Assign admin role to luis@lefv.io user
-- User ID: a3560fab-9597-479b-8cfa-b089d2a6d504

INSERT INTO public.user_roles (user_id, role) 
VALUES ('a3560fab-9597-479b-8cfa-b089d2a6d504', 'admin') 
ON CONFLICT (user_id, role) DO NOTHING;

-- Verify the admin role was assigned
SELECT 
    ur.user_id,
    ur.role,
    au.email,
    ur.created_at
FROM public.user_roles ur
JOIN auth.users au ON ur.user_id = au.id
WHERE au.email = 'luis@lefv.io';
