IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'unleashed')
BEGIN
    EXEC('CREATE SCHEMA unleashed');
END
GO

IF OBJECT_ID('unleashed.ExchangeRates', 'U') IS NULL
BEGIN
    CREATE TABLE unleashed.ExchangeRates (
        ExchangeRateID BIGINT IDENTITY(1,1) PRIMARY KEY,
        RateDate DATE NOT NULL,
        BaseCurrency CHAR(3) NOT NULL,
        QuoteCurrency CHAR(3) NOT NULL,
        Rate DECIMAL(18,8) NOT NULL,
        Provider VARCHAR(50) NULL,
        SourceSystem VARCHAR(50) NOT NULL DEFAULT 'Frankfurter',
        LoadedAtUTC DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_UnleashedExchangeRates UNIQUE (
            RateDate,
            BaseCurrency,
            QuoteCurrency,
            Provider
        )
    );
END
GO

IF OBJECT_ID('unleashed.ProcessLog', 'U') IS NULL
BEGIN
    CREATE TABLE unleashed.ProcessLog (
        LogID BIGINT IDENTITY(1,1) PRIMARY KEY,
        ProcessName VARCHAR(150) NOT NULL,
        ActionName VARCHAR(150) NOT NULL,
        Status VARCHAR(20) NOT NULL,
        Detail NVARCHAR(MAX) NULL,
        ErrorMessage NVARCHAR(MAX) NULL,
        StartedAtUTC DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        FinishedAtUTC DATETIME2 NULL
    );
END
GO
