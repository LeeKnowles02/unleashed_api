-- =============================================================================
-- Run-level execution log (one row per end-to-end sync/workbook execution)
-- Schema: unleashed
-- =============================================================================

IF SCHEMA_ID('unleashed') IS NULL
    EXEC('CREATE SCHEMA unleashed');
GO

IF OBJECT_ID('unleashed.sync_run', 'U') IS NULL
CREATE TABLE unleashed.sync_run (
    [run_id]        NVARCHAR(64) NOT NULL PRIMARY KEY,
    [start_time]    DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    [end_time]      DATETIME2 NULL,
    [status]        NVARCHAR(16) NOT NULL,
    [total_records] INT NOT NULL DEFAULT 0,
    [total_errors]  INT NOT NULL DEFAULT 0,
    [created_at]    DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT CK_sync_run_status
        CHECK ([status] IN ('SUCCESS', 'FAILED', 'IN_PROGRESS'))
);
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE [name] = 'CK_sync_run_status'
      AND [parent_object_id] = OBJECT_ID('unleashed.sync_run')
)
BEGIN
    ALTER TABLE unleashed.sync_run
    ADD CONSTRAINT CK_sync_run_status
        CHECK ([status] IN ('SUCCESS', 'FAILED', 'IN_PROGRESS'));
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE [name] = 'IX_sync_run_start_time'
      AND [object_id] = OBJECT_ID('unleashed.sync_run')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sync_run_start_time
        ON unleashed.sync_run ([start_time] DESC);
END;
GO

