CREATE TABLE dompet.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('success', 'error', 'warning', 'info')),
    message TEXT NOT NULL,
    description TEXT,
    entity_type TEXT,
    entity_id UUID,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_created ON dompet.notifications (user_id, created_at DESC);
CREATE INDEX idx_notifications_user_unread ON dompet.notifications (user_id) WHERE is_read = FALSE;

GRANT SELECT, INSERT, UPDATE, DELETE ON dompet.notifications TO web_user;
ALTER TABLE dompet.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE dompet.notifications FORCE ROW LEVEL SECURITY;
CREATE POLICY notifications_all ON dompet.notifications
    FOR ALL TO web_user
    USING (user_id = current_setting('app.current_user_id')::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
