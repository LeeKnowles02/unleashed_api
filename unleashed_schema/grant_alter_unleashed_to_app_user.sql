-- =============================================================================
-- Grant ALTER on schema [unleashed] so the app SQL user can apply audit columns
-- (or run migrations) without dbo. Optional: revoke after patch if policy requires.
-- =============================================================================
-- Run in the **application database** (e.g. unleashed_runner) as a login with
-- sufficient privileges (db_owner or owner of schema unleashed).
--
-- Replace [unleashed_ingest] with your real app user from AZURE_SQL_USER / .env.
-- =============================================================================

GRANT ALTER ON SCHEMA::unleashed TO [unleashed_ingest];
GO

-- After audit columns exist, you may keep this grant for future schema patches,
-- or revoke if you only want dbo to change schema:
-- REVOKE ALTER ON SCHEMA::unleashed TO [unleashed_ingest];
-- GO
