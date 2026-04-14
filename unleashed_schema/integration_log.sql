-- =============================================================================
-- Detailed integration / process log (verbose troubleshooting & audit)
-- Schema: unleashed (matches this project)
-- Run as dbo/admin on the application database (e.g. unleashed_runner).
-- Idempotent: safe to re-run (creates table only if missing).
-- =============================================================================

IF SCHEMA_ID('unleashed') IS NULL
    EXEC('CREATE SCHEMA unleashed');
GO

IF OBJECT_ID('unleashed.integration_log', 'U') IS NULL
CREATE TABLE unleashed.integration_log (
    [id]                BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    [created_at]        DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    [project_name]      NVARCHAR(128) NULL,
    [integration_name]  NVARCHAR(128) NULL,
    [source_system]     NVARCHAR(64) NULL,
    [module_name]       NVARCHAR(256) NULL,
    [function_name]     NVARCHAR(256) NULL,
    [log_level]         NVARCHAR(16) NULL,
    [event_type]        NVARCHAR(64) NULL,
    [run_id]            NVARCHAR(64) NULL,
    [correlation_id]    NVARCHAR(64) NULL,
    [company_id]        NVARCHAR(128) NULL,
    [endpoint]          NVARCHAR(512) NULL,
    [entity_name]       NVARCHAR(256) NULL,
    [action]            NVARCHAR(128) NULL,
    [step_name]         NVARCHAR(256) NULL,
    [status]            NVARCHAR(32) NOT NULL,
    [message]           NVARCHAR(MAX) NULL,
    [detail]            NVARCHAR(MAX) NULL,
    [payload_summary]   NVARCHAR(MAX) NULL,
    [record_count]      INT NULL,
    [duration_ms]       INT NULL,
    [http_status_code]  INT NULL,
    [error_type]        NVARCHAR(256) NULL,
    [error_message]     NVARCHAR(MAX) NULL,
    [stack_trace]       NVARCHAR(MAX) NULL,
    [request_url]       NVARCHAR(2048) NULL,
    [request_method]    NVARCHAR(16) NULL,
    [request_params]    NVARCHAR(MAX) NULL,
    [request_headers_safe] NVARCHAR(MAX) NULL,
    [response_summary]  NVARCHAR(MAX) NULL,
    [response_body_safe] NVARCHAR(MAX) NULL,
    [machine_name]      NVARCHAR(256) NULL,
    [environment]       NVARCHAR(64) NULL,
    [created_by]        NVARCHAR(256) NULL,
    CONSTRAINT CK_integration_log_status
        CHECK ([status] IN ('SUCCESS', 'FAILED', 'IN_PROGRESS', 'WARNING'))
);
GO

-- Enforce non-null + standardized status values on existing installations.
IF COL_LENGTH('unleashed.integration_log', 'status') IS NOT NULL
BEGIN
    UPDATE unleashed.integration_log
    SET [status] = CASE
        WHEN [status] IS NULL THEN 'WARNING'
        WHEN UPPER(LTRIM(RTRIM([status]))) IN ('SUCCESS', 'FAILED', 'IN_PROGRESS', 'WARNING') THEN UPPER(LTRIM(RTRIM([status])))
        WHEN UPPER(LTRIM(RTRIM([status]))) IN ('PASS', 'OK', 'DONE', 'COMPLETE', 'COMPLETED') THEN 'SUCCESS'
        WHEN UPPER(LTRIM(RTRIM([status]))) IN ('FAIL', 'ERROR') THEN 'FAILED'
        WHEN UPPER(LTRIM(RTRIM([status]))) IN ('STARTED', 'RUNNING') THEN 'IN_PROGRESS'
        WHEN UPPER(LTRIM(RTRIM([status]))) IN ('SKIPPED', 'DEGRADED') THEN 'WARNING'
        ELSE 'WARNING'
    END;

    ALTER TABLE unleashed.integration_log
    ALTER COLUMN [status] NVARCHAR(32) NOT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE [name] = 'CK_integration_log_status'
      AND [parent_object_id] = OBJECT_ID('unleashed.integration_log')
)
BEGIN
    ALTER TABLE unleashed.integration_log
    ADD CONSTRAINT CK_integration_log_status
        CHECK ([status] IN ('SUCCESS', 'FAILED', 'IN_PROGRESS', 'WARNING'));
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE [name] = 'IX_integration_log_created_at'
      AND [object_id] = OBJECT_ID('unleashed.integration_log')
)
CREATE NONCLUSTERED INDEX IX_integration_log_created_at
    ON unleashed.integration_log ([created_at] DESC);
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE [name] = 'IX_integration_log_correlation_id'
      AND [object_id] = OBJECT_ID('unleashed.integration_log')
)
CREATE NONCLUSTERED INDEX IX_integration_log_correlation_id
    ON unleashed.integration_log ([correlation_id])
    WHERE [correlation_id] IS NOT NULL;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE [name] = 'IX_integration_log_run_id'
      AND [object_id] = OBJECT_ID('unleashed.integration_log')
)
CREATE NONCLUSTERED INDEX IX_integration_log_run_id
    ON unleashed.integration_log ([run_id])
    WHERE [run_id] IS NOT NULL;
GO

IF OBJECT_ID('unleashed.sync_run', 'U') IS NOT NULL
AND OBJECT_ID('unleashed.integration_log', 'U') IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE [name] = 'FK_integration_log_sync_run'
      AND [parent_object_id] = OBJECT_ID('unleashed.integration_log')
)
BEGIN
    ALTER TABLE unleashed.integration_log WITH NOCHECK
    ADD CONSTRAINT FK_integration_log_sync_run
        FOREIGN KEY ([run_id]) REFERENCES unleashed.sync_run([run_id]);
END;
GO
