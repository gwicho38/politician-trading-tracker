-- Insert admin role for user luis@lefv.io
INSERT INTO public.user_roles (user_id, role) 
VALUES ('75c90d53-8173-454e-b990-ec51ca3e3294', 'admin')
ON CONFLICT (user_id, role) DO NOTHING;