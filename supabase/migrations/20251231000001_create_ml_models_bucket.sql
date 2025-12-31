-- Create storage bucket for ML models
-- This bucket stores trained model artifacts (.pkl files)

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'ml-models',
    'ml-models',
    false,  -- private bucket
    104857600,  -- 100MB max file size
    ARRAY['application/octet-stream']  -- binary files only
)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for service_role are not needed - service_role bypasses RLS
-- The bucket will only be accessed by backend services using the service role key
