# Database Migrations

This directory contains SQL migration scripts for the Supafund Market Creation Agent database.

## Migration Files

### 001_create_prediction_markets_table.sql

Creates the `prediction_markets` table to track created markets and prevent duplicates.

**Features:**
- Unique constraint on `application_id` to prevent duplicate markets
- Market status tracking (created, active, closed, resolved, failed)
- Full audit trail with created_at/updated_at timestamps
- JSON metadata storage for flexible data
- Automatic updated_at trigger

## How to Apply Migrations

### Option 1: Supabase Dashboard
1. Go to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy and paste the contents of `001_create_prediction_markets_table.sql`
4. Execute the SQL

### Option 2: Supabase CLI
```bash
# If you have Supabase CLI installed
supabase db reset
# or apply specific migration
psql -h <your-supabase-host> -U postgres -d postgres -f 001_create_prediction_markets_table.sql
```

### Option 3: Manual SQL Execution
Connect to your PostgreSQL database and execute the migration file directly.

## Migration Order

Execute migrations in numerical order:
1. `001_create_prediction_markets_table.sql`

## Verification

After applying the migration, verify the table was created:

```sql
-- Check if table exists
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'prediction_markets'
ORDER BY ordinal_position;

-- Check constraints
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'prediction_markets';

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'prediction_markets';
```

## Rollback

If you need to rollback the migration:

```sql
-- Remove the table and all related objects
DROP TABLE IF EXISTS public.prediction_markets CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
```

## Notes

- The migration includes Row Level Security (RLS) setup - ensure your Supabase policies allow access
- The table includes foreign key constraints to `program_applications` table
- Indexes are created for optimal query performance
- The trigger automatically updates `updated_at` field on record changes