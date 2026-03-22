IF SCHEMA_ID('unleashed') IS NULL
    EXEC('CREATE SCHEMA unleashed');
GO

-- Customers (exports/customers.py)
IF OBJECT_ID('unleashed.Customers', 'U') IS NULL
CREATE TABLE unleashed.Customers (
    [CustomerCode] NVARCHAR(MAX) NULL,
    [CustomerName] NVARCHAR(MAX) NULL,
    [CustomerType] NVARCHAR(MAX) NULL,
    [Email] NVARCHAR(MAX) NULL,
    [PhoneNumber] NVARCHAR(MAX) NULL,
    [MobileNumber] NVARCHAR(MAX) NULL,
    [Website] NVARCHAR(MAX) NULL,
    [CustomerRef] NVARCHAR(MAX) NULL,
    [DiscountRate] NVARCHAR(MAX) NULL,
    [Taxable] NVARCHAR(MAX) NULL,
    [Currency] NVARCHAR(MAX) NULL,
    [Guid] NVARCHAR(255) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_Customers PRIMARY KEY ([Guid]));
GO

-- Invoices (exports/invoices.py)
IF OBJECT_ID('unleashed.Invoices', 'U') IS NULL
CREATE TABLE unleashed.Invoices (
    [InvoiceNumber] NVARCHAR(MAX) NULL,
    [InvoiceDate] DATETIME2 NULL,
    [DueDate] DATETIME2 NULL,
    [Status] NVARCHAR(MAX) NULL,
    [CustomerName] NVARCHAR(MAX) NULL,
    [CustomerCode] NVARCHAR(MAX) NULL,
    [CustomerGuid] NVARCHAR(MAX) NULL,
    [Currency] NVARCHAR(MAX) NULL,
    [ExchangeRate] NVARCHAR(MAX) NULL,
    [SubTotal] NVARCHAR(MAX) NULL,
    [TaxTotal] NVARCHAR(MAX) NULL,
    [Total] NVARCHAR(MAX) NULL,
    [SalesOrderNumber] NVARCHAR(MAX) NULL,
    [SalesOrderGuid] NVARCHAR(MAX) NULL,
    [WarehouseName] NVARCHAR(MAX) NULL,
    [WarehouseGuid] NVARCHAR(MAX) NULL,
    [Guid] NVARCHAR(255) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_Invoices PRIMARY KEY ([Guid]));
GO

-- Products (exports/products.py)
IF OBJECT_ID('unleashed.Products', 'U') IS NULL
CREATE TABLE unleashed.Products (
    [ProductCode] NVARCHAR(MAX) NULL,
    [ProductDescription] NVARCHAR(MAX) NULL,
    [Barcode] NVARCHAR(MAX) NULL,
    [IsObsolete] NVARCHAR(MAX) NULL,
    [IsComponent] NVARCHAR(MAX) NULL,
    [DefaultPurchasePrice] NVARCHAR(MAX) NULL,
    [DefaultSellPrice] NVARCHAR(MAX) NULL,
    [AverageLandCost] NVARCHAR(MAX) NULL,
    [ProductGroup] NVARCHAR(MAX) NULL,
    [UnitOfMeasure] NVARCHAR(MAX) NULL,
    [Guid] NVARCHAR(255) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_Products PRIMARY KEY ([Guid]));
GO

-- Warehouses (exports/warehouses.py)
IF OBJECT_ID('unleashed.Warehouses', 'U') IS NULL
CREATE TABLE unleashed.Warehouses (
    [WarehouseCode] NVARCHAR(MAX) NULL,
    [WarehouseName] NVARCHAR(MAX) NULL,
    [IsDefault] NVARCHAR(MAX) NULL,
    [IsObsolete] NVARCHAR(MAX) NULL,
    [StreetAddress] NVARCHAR(MAX) NULL,
    [Suburb] NVARCHAR(MAX) NULL,
    [City] NVARCHAR(MAX) NULL,
    [Region] NVARCHAR(MAX) NULL,
    [Country] NVARCHAR(MAX) NULL,
    [PostCode] NVARCHAR(MAX) NULL,
    [Guid] NVARCHAR(255) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_Warehouses PRIMARY KEY ([Guid]));
GO

-- StockOnHand (exports/stock_on_hand.py) – one row per product per warehouse
-- PK columns NVARCHAR(50) to keep clustered index under 900-byte limit (50*2 + 50*2 = 200 bytes)
IF OBJECT_ID('unleashed.StockOnHand', 'U') IS NULL
CREATE TABLE unleashed.StockOnHand (
    [ProductCode] NVARCHAR(MAX) NULL,
    [ProductDescription] NVARCHAR(MAX) NULL,
    [ProductGuid] NVARCHAR(50) NOT NULL,
    [WarehouseName] NVARCHAR(MAX) NULL,
    [WarehouseGuid] NVARCHAR(50) NOT NULL,
    [QtyOnHand] NVARCHAR(MAX) NULL,
    [QtyAllocated] NVARCHAR(MAX) NULL,
    [QtyAvailable] NVARCHAR(MAX) NULL,
    [QtyOnPurchase] NVARCHAR(MAX) NULL,
    [QtyOnSalesOrder] NVARCHAR(MAX) NULL,
    [AvgLandCost] NVARCHAR(MAX) NULL,
    [TotalValue] NVARCHAR(MAX) NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_StockOnHand PRIMARY KEY ([ProductGuid], [WarehouseGuid]));
GO

-- CreditNotes (exports/credit_notes.py)
IF OBJECT_ID('unleashed.CreditNotes', 'U') IS NULL
CREATE TABLE unleashed.CreditNotes (
    [CreditNoteNumber] NVARCHAR(MAX) NULL,
    [CreditNoteDate] DATETIME2 NULL,
    [Status] NVARCHAR(MAX) NULL,
    [CustomerName] NVARCHAR(MAX) NULL,
    [CustomerCode] NVARCHAR(MAX) NULL,
    [CustomerGuid] NVARCHAR(MAX) NULL,
    [Currency] NVARCHAR(MAX) NULL,
    [ExchangeRate] NVARCHAR(MAX) NULL,
    [SubTotal] NVARCHAR(MAX) NULL,
    [TaxTotal] NVARCHAR(MAX) NULL,
    [Total] NVARCHAR(MAX) NULL,
    [SalesOrderNumber] NVARCHAR(MAX) NULL,
    [SalesOrderGuid] NVARCHAR(MAX) NULL,
    [InvoiceNumber] NVARCHAR(MAX) NULL,
    [InvoiceGuid] NVARCHAR(MAX) NULL,
    [Guid] NVARCHAR(255) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_CreditNotes PRIMARY KEY ([Guid]));
GO

-- SalesShipments (exports/sales_shipments.py)
IF OBJECT_ID('unleashed.SalesShipments', 'U') IS NULL
CREATE TABLE unleashed.SalesShipments (
    [ShipmentNumber] NVARCHAR(MAX) NULL,
    [ShipmentDate] DATETIME2 NULL,
    [ShipmentStatus] NVARCHAR(MAX) NULL,
    [SalesOrderNumber] NVARCHAR(MAX) NULL,
    [SalesOrderGuid] NVARCHAR(MAX) NULL,
    [CustomerName] NVARCHAR(MAX) NULL,
    [CustomerCode] NVARCHAR(MAX) NULL,
    [CustomerGuid] NVARCHAR(MAX) NULL,
    [WarehouseName] NVARCHAR(MAX) NULL,
    [WarehouseGuid] NVARCHAR(MAX) NULL,
    [Carrier] NVARCHAR(MAX) NULL,
    [TrackingNumber] NVARCHAR(MAX) NULL,
    [Guid] NVARCHAR(255) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_SalesShipments PRIMARY KEY ([Guid]));
GO

-- SalesOrders (exports/sales_orders.py) – one row per order line
-- PK columns NVARCHAR(50) to keep clustered index under 900-byte limit (50*2 + 50*2 = 200 bytes)
IF OBJECT_ID('unleashed.SalesOrders', 'U') IS NULL
CREATE TABLE unleashed.SalesOrders (
    [OrderNumber] NVARCHAR(MAX) NULL,
    [OrderDate] DATETIME2 NULL,
    [RequiredDate] DATETIME2 NULL,
    [CompletedDate] DATETIME2 NULL,
    [ReceivedDate] DATETIME2 NULL,
    [OrderStatus] NVARCHAR(MAX) NULL,
    [CustomerName] NVARCHAR(MAX) NULL,
    [CustomerGuid] NVARCHAR(MAX) NULL,
    [CustomerRef] NVARCHAR(MAX) NULL,
    [Warehouse] NVARCHAR(MAX) NULL,
    [WarehouseGuid] NVARCHAR(MAX) NULL,
    [Currency] NVARCHAR(MAX) NULL,
    [ExchangeRate] NVARCHAR(MAX) NULL,
    [SubTotal] NVARCHAR(MAX) NULL,
    [TaxTotal] NVARCHAR(MAX) NULL,
    [Total] NVARCHAR(MAX) NULL,
    [OrderGuid] NVARCHAR(50) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [LineNumber] NVARCHAR(50) NOT NULL,
    [ProductCode] NVARCHAR(MAX) NULL,
    [ProductDescription] NVARCHAR(MAX) NULL,
    [ProductGuid] NVARCHAR(MAX) NULL,
    [DueDate] DATETIME2 NULL,
    [OrderQuantity] NVARCHAR(MAX) NULL,
    [UnitPrice] NVARCHAR(MAX) NULL,
    [LineTotal] NVARCHAR(MAX) NULL,
    [LineTax] NVARCHAR(MAX) NULL,
    [LineGuid] NVARCHAR(MAX) NULL,
    [LineLastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_SalesOrders PRIMARY KEY ([OrderGuid], [LineNumber]));
GO

-- Suppliers (exports/suppliers.py)
IF OBJECT_ID('unleashed.Suppliers', 'U') IS NULL
CREATE TABLE unleashed.Suppliers (
    [SupplierCode] NVARCHAR(MAX) NULL,
    [SupplierName] NVARCHAR(MAX) NULL,
    [Email] NVARCHAR(MAX) NULL,
    [PhoneNumber] NVARCHAR(MAX) NULL,
    [MobileNumber] NVARCHAR(MAX) NULL,
    [Website] NVARCHAR(MAX) NULL,
    [SupplierRef] NVARCHAR(MAX) NULL,
    [Currency] NVARCHAR(MAX) NULL,
    [Guid] NVARCHAR(255) NOT NULL,
    [LastModifiedOn] DATETIME2 NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_unleashed_Suppliers PRIMARY KEY ([Guid]));
GO


IF OBJECT_ID('unleashed.StockOnHand', 'U') IS NOT NULL
BEGIN
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE [name] = 'PK_unleashed_StockOnHand' AND parent_object_id = OBJECT_ID('unleashed.StockOnHand'))
        ALTER TABLE unleashed.StockOnHand DROP CONSTRAINT PK_unleashed_StockOnHand;
    ALTER TABLE unleashed.StockOnHand ALTER COLUMN [ProductGuid] NVARCHAR(50) NOT NULL;
    ALTER TABLE unleashed.StockOnHand ALTER COLUMN [WarehouseGuid] NVARCHAR(50) NOT NULL;
    ALTER TABLE unleashed.StockOnHand ADD CONSTRAINT PK_unleashed_StockOnHand PRIMARY KEY ([ProductGuid], [WarehouseGuid]);
END
GO

IF OBJECT_ID('unleashed.SalesOrders', 'U') IS NOT NULL
BEGIN
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE [name] = 'PK_unleashed_SalesOrders' AND parent_object_id = OBJECT_ID('unleashed.SalesOrders'))
        ALTER TABLE unleashed.SalesOrders DROP CONSTRAINT PK_unleashed_SalesOrders;
    ALTER TABLE unleashed.SalesOrders ALTER COLUMN [OrderGuid] NVARCHAR(50) NOT NULL;
    ALTER TABLE unleashed.SalesOrders ALTER COLUMN [LineNumber] NVARCHAR(50) NOT NULL;
    ALTER TABLE unleashed.SalesOrders ADD CONSTRAINT PK_unleashed_SalesOrders PRIMARY KEY ([OrderGuid], [LineNumber]);
END
GO


IF OBJECT_ID('unleashed.ConnectionTest', 'U') IS NULL
CREATE TABLE unleashed.ConnectionTest (
    [ID] INT NOT NULL PRIMARY KEY,
    [TestValue] NVARCHAR(100) NOT NULL,
    [CreatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('unleashed.RunLog', 'U') IS NULL
CREATE TABLE unleashed.RunLog (
    [RunID] UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    [RunRef] NVARCHAR(100) NOT NULL,
    [ParentRunRef] NVARCHAR(100) NULL,
    [EndpointName] NVARCHAR(100) NULL,
    [RunType] NVARCHAR(20) NULL,
    [RunMode] NVARCHAR(50) NULL,
    [Status] NVARCHAR(30) NULL,
    [StartedAt] DATETIME2 NULL,
    [FinishedAt] DATETIME2 NULL,
    [DurationSeconds] INT NULL,
    [RowsFetched] INT NULL,
    [RowsWritten] INT NULL,
    [RowsUpdated] INT NULL,
    [RowsDeleted] INT NULL,
    [RequestedUnits] INT NULL,
    [ProcessedUnits] INT NULL,
    [CheckpointStart] NVARCHAR(200) NULL,
    [CheckpointEnd] NVARCHAR(200) NULL,
    [TargetTable] NVARCHAR(200) NULL,
    [Message] NVARCHAR(MAX) NULL,
    [ErrorMessage] NVARCHAR(MAX) NULL,
    [TriggerSource] NVARCHAR(100) NULL,
    [TriggeredBy] NVARCHAR(100) NULL,
    [Environment] NVARCHAR(100) NULL,
    [CreatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('unleashed.TestAssessmentLog', 'U') IS NULL
CREATE TABLE unleashed.TestAssessmentLog (
    [AssessmentID] UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    [AssessmentRef] NVARCHAR(100) NOT NULL,
    [ParentRunRef] NVARCHAR(100) NULL,
    [EndpointName] NVARCHAR(100) NULL,
    [ControlRunRef] NVARCHAR(100) NULL,
    [Batch1RunRef] NVARCHAR(100) NULL,
    [Batch2RunRef] NVARCHAR(100) NULL,
    [AssessmentType] NVARCHAR(50) NULL,
    [ControlUnits] INT NULL,
    [IncrementalUnits] INT NULL,
    [ControlRowCount] INT NULL,
    [IncrementalRowCount] INT NULL,
    [OverlapCount] INT NULL,
    [MissingCount] INT NULL,
    [ExtraCount] INT NULL,
    [CriticalFieldCompletenessPct] DECIMAL(5,2) NULL,
    [CheckpointAssessment] NVARCHAR(30) NULL,
    [RowCountAssessment] NVARCHAR(30) NULL,
    [KeyMatchAssessment] NVARCHAR(30) NULL,
    [OverallAssessment] NVARCHAR(30) NULL,
    [SignOffStatus] NVARCHAR(30) NULL,
    [Notes] NVARCHAR(MAX) NULL,
    [AssessedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    [AssessedBy] NVARCHAR(100) NULL
);
GO

IF OBJECT_ID('unleashed.EndpointControl', 'U') IS NULL
CREATE TABLE unleashed.EndpointControl (
    [EndpointName] NVARCHAR(100) NOT NULL PRIMARY KEY,
    [IsEnabled] BIT NOT NULL DEFAULT 1,
    [LastFullRunRef] NVARCHAR(100) NULL,
    [LastFullRunAt] DATETIME2 NULL,
    [LastTestRunRef] NVARCHAR(100) NULL,
    [LastTestRunAt] DATETIME2 NULL,
    [LastAssessmentRef] NVARCHAR(100) NULL,
    [LastAssessmentStatus] NVARCHAR(30) NULL,
    [LastSignOffStatus] NVARCHAR(30) NULL,
    [LastCheckpoint] NVARCHAR(200) NULL,
    [LastRowCount] INT NULL,
    [LastStatus] NVARCHAR(30) NULL,
    [NextAction] NVARCHAR(200) NULL,
    [Notes] NVARCHAR(MAX) NULL,
    [UpdatedAt] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- =============================================================================
-- Audit columns on endpoint tables
-- =============================================================================
DECLARE @tbl NVARCHAR(300);
DECLARE @sql NVARCHAR(MAX);

DECLARE endpoint_cursor CURSOR FOR
SELECT [name]
FROM sys.tables
WHERE SCHEMA_NAME(schema_id) = 'unleashed'
  AND [name] IN ('Customers', 'Invoices', 'Products', 'Warehouses', 'StockOnHand', 'CreditNotes', 'SalesShipments', 'SalesOrders', 'Suppliers');

OPEN endpoint_cursor;
FETCH NEXT FROM endpoint_cursor INTO @tbl;

WHILE @@FETCH_STATUS = 0
BEGIN
    IF COL_LENGTH('unleashed.' + @tbl, 'RunType') IS NULL
    BEGIN
        SET @sql = 'ALTER TABLE unleashed.' + QUOTENAME(@tbl) + ' ADD [RunType] NVARCHAR(20) NULL;';
        EXEC sp_executesql @sql;
    END;
    IF COL_LENGTH('unleashed.' + @tbl, 'RunRef') IS NULL
    BEGIN
        SET @sql = 'ALTER TABLE unleashed.' + QUOTENAME(@tbl) + ' ADD [RunRef] NVARCHAR(100) NULL;';
        EXEC sp_executesql @sql;
    END;
    IF COL_LENGTH('unleashed.' + @tbl, 'LoadedAt') IS NULL
    BEGIN
        SET @sql = 'ALTER TABLE unleashed.' + QUOTENAME(@tbl) + ' ADD [LoadedAt] DATETIME2 NULL;';
        EXEC sp_executesql @sql;
    END;
    IF COL_LENGTH('unleashed.' + @tbl, 'EndpointName') IS NULL
    BEGIN
        SET @sql = 'ALTER TABLE unleashed.' + QUOTENAME(@tbl) + ' ADD [EndpointName] NVARCHAR(100) NULL;';
        EXEC sp_executesql @sql;
    END;

    FETCH NEXT FROM endpoint_cursor INTO @tbl;
END

CLOSE endpoint_cursor;
DEALLOCATE endpoint_cursor;
GO
