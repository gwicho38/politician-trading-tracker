-- Credential Rotation Tracking Migration
-- Adds columns to track when API keys were created/rotated for security compliance
-- Enables 90-day rotation reminders and credential health monitoring

-- Add key_created_at columns for each credential type
ALTER TABLE user_api_keys ADD COLUMN IF NOT EXISTS paper_key_created_at TIMESTAMPTZ;
ALTER TABLE user_api_keys ADD COLUMN IF NOT EXISTS live_key_created_at TIMESTAMPTZ;
ALTER TABLE user_api_keys ADD COLUMN IF NOT EXISTS supabase_key_created_at TIMESTAMPTZ;
ALTER TABLE user_api_keys ADD COLUMN IF NOT EXISTS quiverquant_key_created_at TIMESTAMPTZ;

-- Add rotation_reminder_sent column to track notification state
ALTER TABLE user_api_keys ADD COLUMN IF NOT EXISTS rotation_reminder_sent_at TIMESTAMPTZ;

-- Create function to check credential age and return health status
CREATE OR REPLACE FUNCTION get_credential_health(p_user_email TEXT)
RETURNS TABLE (
    credential_type TEXT,
    is_configured BOOLEAN,
    days_since_creation INTEGER,
    days_until_rotation INTEGER,
    health_status TEXT,
    last_validated TIMESTAMPTZ
) AS $$
DECLARE
    rotation_days CONSTANT INTEGER := 90;
    warning_threshold CONSTANT INTEGER := 14;  -- Warn 14 days before rotation
    rec RECORD;
BEGIN
    -- Get user record
    SELECT * INTO rec FROM user_api_keys WHERE user_email = p_user_email;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Paper API Key
    credential_type := 'paper_api';
    is_configured := rec.paper_api_key IS NOT NULL AND rec.paper_api_key != '';

    IF is_configured THEN
        days_since_creation := COALESCE(
            EXTRACT(DAY FROM NOW() - COALESCE(rec.paper_key_created_at, rec.created_at)),
            0
        )::INTEGER;
        days_until_rotation := rotation_days - days_since_creation;
        last_validated := rec.paper_validated_at;

        IF days_until_rotation < 0 THEN
            health_status := 'expired';
        ELSIF days_until_rotation <= warning_threshold THEN
            health_status := 'warning';
        ELSE
            health_status := 'healthy';
        END IF;
    ELSE
        days_since_creation := NULL;
        days_until_rotation := NULL;
        last_validated := NULL;
        health_status := 'not_configured';
    END IF;

    RETURN NEXT;

    -- Live API Key
    credential_type := 'live_api';
    is_configured := rec.live_api_key IS NOT NULL AND rec.live_api_key != '';

    IF is_configured THEN
        days_since_creation := COALESCE(
            EXTRACT(DAY FROM NOW() - COALESCE(rec.live_key_created_at, rec.created_at)),
            0
        )::INTEGER;
        days_until_rotation := rotation_days - days_since_creation;
        last_validated := rec.live_validated_at;

        IF days_until_rotation < 0 THEN
            health_status := 'expired';
        ELSIF days_until_rotation <= warning_threshold THEN
            health_status := 'warning';
        ELSE
            health_status := 'healthy';
        END IF;
    ELSE
        days_since_creation := NULL;
        days_until_rotation := NULL;
        last_validated := NULL;
        health_status := 'not_configured';
    END IF;

    RETURN NEXT;

    -- QuiverQuant API Key
    credential_type := 'quiverquant_api';
    is_configured := rec.quiverquant_api_key IS NOT NULL AND rec.quiverquant_api_key != '';

    IF is_configured THEN
        days_since_creation := COALESCE(
            EXTRACT(DAY FROM NOW() - COALESCE(rec.quiverquant_key_created_at, rec.created_at)),
            0
        )::INTEGER;
        days_until_rotation := rotation_days - days_since_creation;
        last_validated := rec.quiverquant_validated_at;

        IF days_until_rotation < 0 THEN
            health_status := 'expired';
        ELSIF days_until_rotation <= warning_threshold THEN
            health_status := 'warning';
        ELSE
            health_status := 'healthy';
        END IF;
    ELSE
        days_since_creation := NULL;
        days_until_rotation := NULL;
        last_validated := NULL;
        health_status := 'not_configured';
    END IF;

    RETURN NEXT;

    -- Supabase Keys
    credential_type := 'supabase';
    is_configured := rec.supabase_url IS NOT NULL AND rec.supabase_url != '';

    IF is_configured THEN
        days_since_creation := COALESCE(
            EXTRACT(DAY FROM NOW() - COALESCE(rec.supabase_key_created_at, rec.created_at)),
            0
        )::INTEGER;
        days_until_rotation := rotation_days - days_since_creation;
        last_validated := rec.supabase_validated_at;

        IF days_until_rotation < 0 THEN
            health_status := 'expired';
        ELSIF days_until_rotation <= warning_threshold THEN
            health_status := 'warning';
        ELSE
            health_status := 'healthy';
        END IF;
    ELSE
        days_since_creation := NULL;
        days_until_rotation := NULL;
        last_validated := NULL;
        health_status := 'not_configured';
    END IF;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to get users needing rotation reminders
CREATE OR REPLACE FUNCTION get_users_needing_rotation_reminder()
RETURNS TABLE (
    user_email TEXT,
    user_name TEXT,
    credentials_expiring TEXT[],
    earliest_expiry_days INTEGER
) AS $$
DECLARE
    rotation_days CONSTANT INTEGER := 90;
    warning_threshold CONSTANT INTEGER := 14;
    reminder_cooldown CONSTANT INTERVAL := '7 days';
BEGIN
    RETURN QUERY
    SELECT
        u.user_email::TEXT,
        u.user_name::TEXT,
        ARRAY_REMOVE(ARRAY[
            CASE WHEN u.paper_api_key IS NOT NULL
                 AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.paper_key_created_at, u.created_at))::INTEGER) <= warning_threshold
                 THEN 'paper_api' END,
            CASE WHEN u.live_api_key IS NOT NULL
                 AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.live_key_created_at, u.created_at))::INTEGER) <= warning_threshold
                 THEN 'live_api' END,
            CASE WHEN u.quiverquant_api_key IS NOT NULL
                 AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.quiverquant_key_created_at, u.created_at))::INTEGER) <= warning_threshold
                 THEN 'quiverquant_api' END,
            CASE WHEN u.supabase_url IS NOT NULL
                 AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.supabase_key_created_at, u.created_at))::INTEGER) <= warning_threshold
                 THEN 'supabase' END
        ], NULL) AS credentials_expiring,
        LEAST(
            CASE WHEN u.paper_api_key IS NOT NULL
                 THEN (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.paper_key_created_at, u.created_at))::INTEGER) END,
            CASE WHEN u.live_api_key IS NOT NULL
                 THEN (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.live_key_created_at, u.created_at))::INTEGER) END,
            CASE WHEN u.quiverquant_api_key IS NOT NULL
                 THEN (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.quiverquant_key_created_at, u.created_at))::INTEGER) END,
            CASE WHEN u.supabase_url IS NOT NULL
                 THEN (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.supabase_key_created_at, u.created_at))::INTEGER) END
        )::INTEGER AS earliest_expiry_days
    FROM user_api_keys u
    WHERE
        -- Has at least one credential configured
        (u.paper_api_key IS NOT NULL OR u.live_api_key IS NOT NULL
         OR u.quiverquant_api_key IS NOT NULL OR u.supabase_url IS NOT NULL)
        -- Haven't sent reminder recently
        AND (u.rotation_reminder_sent_at IS NULL OR u.rotation_reminder_sent_at < NOW() - reminder_cooldown)
        -- At least one credential is expiring
        AND (
            (u.paper_api_key IS NOT NULL AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.paper_key_created_at, u.created_at))::INTEGER) <= warning_threshold)
            OR (u.live_api_key IS NOT NULL AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.live_key_created_at, u.created_at))::INTEGER) <= warning_threshold)
            OR (u.quiverquant_api_key IS NOT NULL AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.quiverquant_key_created_at, u.created_at))::INTEGER) <= warning_threshold)
            OR (u.supabase_url IS NOT NULL AND (rotation_days - EXTRACT(DAY FROM NOW() - COALESCE(u.supabase_key_created_at, u.created_at))::INTEGER) <= warning_threshold)
        )
    ORDER BY earliest_expiry_days ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to set key_created_at when keys are updated
CREATE OR REPLACE FUNCTION update_key_created_at()
RETURNS TRIGGER AS $$
BEGIN
    -- Paper API key changed
    IF (OLD.paper_api_key IS DISTINCT FROM NEW.paper_api_key) AND NEW.paper_api_key IS NOT NULL THEN
        NEW.paper_key_created_at := NOW();
    END IF;

    -- Live API key changed
    IF (OLD.live_api_key IS DISTINCT FROM NEW.live_api_key) AND NEW.live_api_key IS NOT NULL THEN
        NEW.live_key_created_at := NOW();
    END IF;

    -- QuiverQuant API key changed
    IF (OLD.quiverquant_api_key IS DISTINCT FROM NEW.quiverquant_api_key) AND NEW.quiverquant_api_key IS NOT NULL THEN
        NEW.quiverquant_key_created_at := NOW();
    END IF;

    -- Supabase URL changed (proxy for all Supabase credentials)
    IF (OLD.supabase_url IS DISTINCT FROM NEW.supabase_url) AND NEW.supabase_url IS NOT NULL THEN
        NEW.supabase_key_created_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS track_key_creation ON user_api_keys;
CREATE TRIGGER track_key_creation
    BEFORE UPDATE ON user_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_key_created_at();

-- Also handle INSERT for new rows
CREATE OR REPLACE FUNCTION set_initial_key_created_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.paper_api_key IS NOT NULL THEN
        NEW.paper_key_created_at := NOW();
    END IF;

    IF NEW.live_api_key IS NOT NULL THEN
        NEW.live_key_created_at := NOW();
    END IF;

    IF NEW.quiverquant_api_key IS NOT NULL THEN
        NEW.quiverquant_key_created_at := NOW();
    END IF;

    IF NEW.supabase_url IS NOT NULL THEN
        NEW.supabase_key_created_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_initial_key_created ON user_api_keys;
CREATE TRIGGER set_initial_key_created
    BEFORE INSERT ON user_api_keys
    FOR EACH ROW EXECUTE FUNCTION set_initial_key_created_at();

-- Comments
COMMENT ON COLUMN user_api_keys.paper_key_created_at IS 'Timestamp when paper API key was created/rotated (for 90-day rotation tracking)';
COMMENT ON COLUMN user_api_keys.live_key_created_at IS 'Timestamp when live API key was created/rotated (for 90-day rotation tracking)';
COMMENT ON COLUMN user_api_keys.supabase_key_created_at IS 'Timestamp when Supabase credentials were created/rotated (for 90-day rotation tracking)';
COMMENT ON COLUMN user_api_keys.quiverquant_key_created_at IS 'Timestamp when QuiverQuant API key was created/rotated (for 90-day rotation tracking)';
COMMENT ON COLUMN user_api_keys.rotation_reminder_sent_at IS 'Last time a rotation reminder was sent (cooldown tracking)';
COMMENT ON FUNCTION get_credential_health(TEXT) IS 'Returns credential health status for a user, including days until rotation needed';
COMMENT ON FUNCTION get_users_needing_rotation_reminder() IS 'Returns users who need rotation reminders (credentials expiring within 14 days)';
