-- =============================================================================
-- Patch: add audit columns to all Unleashed endpoint tables
-- =============================================================================
-- Run this against the same database the app uses (e.g. unleashed_runner).
-- Idempotent — safe to re-run.
--
-- Fixes: SetupRequiredError "Missing required columns ... RunType, RunRef,
--        LoadedAt, EndpointName" when running exports other than SalesOrders.
--
-- Requires: ALTER permission on unleashed.* tables (or run as dbo / admin).
-- =============================================================================

IF SCHEMA_ID('unleashed') IS NULL
    EXEC('CREATE SCHEMA unleashed');
GO

IF OBJECT_ID('unleashed.Customers', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.Customers', 'RunType') IS NULL ALTER TABLE unleashed.Customers ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.Customers', 'RunRef') IS NULL ALTER TABLE unleashed.Customers ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.Customers', 'LoadedAt') IS NULL ALTER TABLE unleashed.Customers ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.Customers', 'EndpointName') IS NULL ALTER TABLE unleashed.Customers ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.Invoices', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.Invoices', 'RunType') IS NULL ALTER TABLE unleashed.Invoices ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.Invoices', 'RunRef') IS NULL ALTER TABLE unleashed.Invoices ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.Invoices', 'LoadedAt') IS NULL ALTER TABLE unleashed.Invoices ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.Invoices', 'EndpointName') IS NULL ALTER TABLE unleashed.Invoices ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.Products', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.Products', 'RunType') IS NULL ALTER TABLE unleashed.Products ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.Products', 'RunRef') IS NULL ALTER TABLE unleashed.Products ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.Products', 'LoadedAt') IS NULL ALTER TABLE unleashed.Products ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.Products', 'EndpointName') IS NULL ALTER TABLE unleashed.Products ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.Warehouses', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.Warehouses', 'RunType') IS NULL ALTER TABLE unleashed.Warehouses ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.Warehouses', 'RunRef') IS NULL ALTER TABLE unleashed.Warehouses ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.Warehouses', 'LoadedAt') IS NULL ALTER TABLE unleashed.Warehouses ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.Warehouses', 'EndpointName') IS NULL ALTER TABLE unleashed.Warehouses ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.StockOnHand', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.StockOnHand', 'RunType') IS NULL ALTER TABLE unleashed.StockOnHand ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.StockOnHand', 'RunRef') IS NULL ALTER TABLE unleashed.StockOnHand ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.StockOnHand', 'LoadedAt') IS NULL ALTER TABLE unleashed.StockOnHand ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.StockOnHand', 'EndpointName') IS NULL ALTER TABLE unleashed.StockOnHand ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.CreditNotes', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.CreditNotes', 'RunType') IS NULL ALTER TABLE unleashed.CreditNotes ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.CreditNotes', 'RunRef') IS NULL ALTER TABLE unleashed.CreditNotes ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.CreditNotes', 'LoadedAt') IS NULL ALTER TABLE unleashed.CreditNotes ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.CreditNotes', 'EndpointName') IS NULL ALTER TABLE unleashed.CreditNotes ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.SalesShipments', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.SalesShipments', 'RunType') IS NULL ALTER TABLE unleashed.SalesShipments ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.SalesShipments', 'RunRef') IS NULL ALTER TABLE unleashed.SalesShipments ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.SalesShipments', 'LoadedAt') IS NULL ALTER TABLE unleashed.SalesShipments ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.SalesShipments', 'EndpointName') IS NULL ALTER TABLE unleashed.SalesShipments ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.SalesOrders', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.SalesOrders', 'RunType') IS NULL ALTER TABLE unleashed.SalesOrders ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.SalesOrders', 'RunRef') IS NULL ALTER TABLE unleashed.SalesOrders ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.SalesOrders', 'LoadedAt') IS NULL ALTER TABLE unleashed.SalesOrders ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.SalesOrders', 'EndpointName') IS NULL ALTER TABLE unleashed.SalesOrders ADD [EndpointName] NVARCHAR(100) NULL;
END
GO

IF OBJECT_ID('unleashed.Suppliers', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('unleashed.Suppliers', 'RunType') IS NULL ALTER TABLE unleashed.Suppliers ADD [RunType] NVARCHAR(20) NULL;
    IF COL_LENGTH('unleashed.Suppliers', 'RunRef') IS NULL ALTER TABLE unleashed.Suppliers ADD [RunRef] NVARCHAR(100) NULL;
    IF COL_LENGTH('unleashed.Suppliers', 'LoadedAt') IS NULL ALTER TABLE unleashed.Suppliers ADD [LoadedAt] DATETIME2 NULL;
    IF COL_LENGTH('unleashed.Suppliers', 'EndpointName') IS NULL ALTER TABLE unleashed.Suppliers ADD [EndpointName] NVARCHAR(100) NULL;
END
GO
