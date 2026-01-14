-- Add user_lambda column to signal_weight_presets table
-- This allows users to save custom Python lambda code with their presets

ALTER TABLE signal_weight_presets
ADD COLUMN IF NOT EXISTS user_lambda TEXT DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN signal_weight_presets.user_lambda IS 'Optional Python lambda code for custom signal transformation';
