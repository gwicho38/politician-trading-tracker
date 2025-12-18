-- Create sync_logs table to track Python sync operations
CREATE TABLE public.sync_logs (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  sync_type TEXT NOT NULL, -- 'filing', 'politician', 'trade', 'full_sync', 'chart_data', 'dashboard_stats'
  status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'success', 'failed'
  records_processed INTEGER DEFAULT 0,
  records_created INTEGER DEFAULT 0,
  records_updated INTEGER DEFAULT 0,
  error_message TEXT,
  metadata JSONB DEFAULT '{}',
  started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  completed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.sync_logs ENABLE ROW LEVEL SECURITY;

-- Public read access for sync_logs (admins can see sync status)
CREATE POLICY "Admin read access for sync_logs"
ON public.sync_logs
FOR SELECT
USING (EXISTS (
  SELECT 1 FROM user_roles
  WHERE user_roles.user_id = auth.uid()
  AND user_roles.role = 'admin'
));

-- Service role can manage sync_logs (for Python backend)
CREATE POLICY "Service role write access for sync_logs"
ON public.sync_logs
FOR ALL
USING (true)
WITH CHECK (true);

-- Create index for faster queries
CREATE INDEX idx_sync_logs_created_at ON public.sync_logs(created_at DESC);
CREATE INDEX idx_sync_logs_status ON public.sync_logs(status);