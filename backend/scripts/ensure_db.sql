DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'finvestor') THEN
      CREATE ROLE finvestor LOGIN PASSWORD 'finvestor1234';
   END IF;
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sampleStocksData') THEN
      CREATE DATABASE "sampleStocksData" OWNER finvestor;
   END IF;
EXCEPTION WHEN insufficient_privilege THEN
   RAISE NOTICE 'Skipping CREATE ROLE/DB: insufficient privileges.';
END $$;