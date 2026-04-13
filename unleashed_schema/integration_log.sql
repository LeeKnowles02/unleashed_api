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
    [status]            NVARCHAR(32) NULL,
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
    [created_by]        NVARCHAR(256) NULL
);
GO

CREATE NONCLUSTERED INDEX IX_integration_log_created_at
    ON unleashed.integration_log ([created_at] DESC);
GO

CREATE NONCLUSTERED INDEX IX_integration_log_correlation_id
    ON unleashed.integration_log ([correlation_id])
    WHERE [correlation_id] IS NOT NULL;
GO

CREATE NONCLUSTERED INDEX IX_integration_log_run_id
    ON unleashed.integration_log ([run_id])
    WHERE [run_id] IS NOT NULL;
GO
