# Database CRUD Interface Guide

## Overview

The Admin Dashboard now includes a comprehensive **Database CRUD** interface that allows you to Create, Read, Update, and Delete records from all Supabase tables directly from the web UI.

## Access

1. Navigate to **Admin** page (requires admin email)
2. Click the **🗂️ Database CRUD** tab
3. Select a table from the dropdown

## Available Tables

- **trading_disclosures** - Main trading data (politician transactions)
- **politicians** - Politician information (name, role, party, state)
- **action_logs** - Application action logs
- **scheduled_jobs** - Scheduled job definitions
- **user_sessions** - User authentication sessions

## Features

### 📖 Read/View Tab

**View and export table data**

Features:
- ✅ View up to 1000 records at once
- ✅ Toggle "Latest first" ordering
- ✅ Automatic detection of timestamp columns
- ✅ Export to CSV
- ✅ Refresh button to reload data

**Example Usage:**
1. Select table (e.g., "trading_disclosures")
2. Set number of records (default: 50)
3. Check "Latest first" for newest records
4. Click "🔄 Refresh Data" to reload
5. Click "📥 Download as CSV" to export

### ➕ Create/Insert Tab

**Add new records to tables**

Features:
- ✅ Pre-filled JSON templates for each table
- ✅ Column names displayed
- ✅ JSON validation before insert
- ✅ Success confirmation with inserted data
- ✅ Helpful JSON formatting tips

**Example - Insert New Trade:**
```json
{
  "politician_id": "uuid-of-politician",
  "transaction_date": "2025-11-04T00:00:00Z",
  "disclosure_date": "2025-11-04T00:00:00Z",
  "asset_name": "Apple Inc. - Common Stock",
  "asset_ticker": "AAPL",
  "asset_type": "stock",
  "transaction_type": "purchase",
  "amount_range_min": 15001,
  "amount_range_max": 50000,
  "status": "active",
  "source": "us_senate",
  "source_url": "https://efdsearch.senate.gov/..."
}
```

**Steps:**
1. Select table
2. Edit the JSON template
3. Click "➕ Insert Record"
4. 🎈 Success! Record is added

**Tips:**
- UUID fields (like `id`) are auto-generated - don't include them
- Use ISO 8601 format for dates: `"2025-11-04T00:00:00Z"`
- Use double quotes for strings
- Check existing records for format examples

### ✏️ Update/Edit Tab

**Modify existing records**

Features:
- ✅ Browse records in table format
- ✅ Select record by ID
- ✅ View current data before editing
- ✅ Edit as JSON
- ✅ Only changed fields are updated
- ✅ Success confirmation

**Steps:**
1. Select table
2. Browse records in the table
3. Select a record from the dropdown (by ID)
4. View current data in expander
5. Edit the JSON
6. Click "💾 Update Record"
7. ✅ Success! Record is updated

**Example - Update Trade Status:**
```json
{
  "politician_id": "uuid-of-politician",
  "transaction_date": "2025-11-04T00:00:00Z",
  "asset_ticker": "AAPL",
  "transaction_type": "sale",
  "amount_range_min": 50001,
  "amount_range_max": 100000,
  "status": "completed"
}
```

**Important:**
- The ID field is automatically excluded from updates
- You can edit any field except the primary key
- All fields in the JSON are sent to Supabase

### 🗑️ Delete Tab

**Remove records (with confirmation)**

Features:
- ⚠️ Deletion warning displayed
- ✅ Browse records before deletion
- ✅ View record details before confirming
- ✅ Type "DELETE" to confirm
- ✅ Cannot delete without confirmation
- ✅ Page auto-refreshes after deletion

**Steps:**
1. Select table
2. Browse records in the table
3. Select record to delete from dropdown
4. Review record details in expander
5. Type **DELETE** in confirmation box
6. Click "🗑️ Delete Record"
7. ✅ Success! Record is deleted

**Safety Features:**
- Button is disabled until you type "DELETE"
- Deletion is permanent and cannot be undone
- Warning message displayed prominently

## Common Use Cases

### 1. Testing Data Collection

**Insert a test politician trade:**
1. Go to **Database CRUD** → Select "trading_disclosures"
2. Click **➕ Create/Insert** tab
3. Modify the template with test data
4. Insert record
5. Verify in **📖 Read/View** tab

### 2. Cleaning Up Test Data

**Delete test records:**
1. Go to **Database CRUD** → Select table
2. Click **🗑️ Delete** tab
3. Find the test record
4. Type "DELETE" and confirm

### 3. Updating Job Schedules

**Modify a scheduled job:**
1. Select "Scheduled Jobs" table
2. Click **✏️ Update/Edit** tab
3. Select the job to modify
4. Update schedule or description
5. Save changes

### 4. Exporting Data for Analysis

**Export politician trades:**
1. Select "trading_disclosures" table
2. Click **📖 Read/View** tab
3. Set limit to 1000 (or desired amount)
4. Click "📥 Download as CSV"
5. Open in Excel, Google Sheets, or pandas

## Error Handling

### Table Not Found

**Error:** `Could not find the table 'public.table_name' in the schema cache`

**Solution:** Table needs to be created in Supabase. See `SETUP_DATABASE.md`

### Permission Denied

**Error:** `permission denied for table`

**Solution:** Check RLS (Row Level Security) policies in Supabase

### Invalid JSON

**Error:** `Invalid JSON: Expecting property name`

**Solution:**
- Check for trailing commas
- Use double quotes, not single quotes
- Validate JSON with online tool

### Constraint Violation

**Error:** `duplicate key value violates unique constraint`

**Solution:**
- Record with same unique field already exists
- Check unique constraints in table schema
- Update existing record instead of inserting

## Security

### Authentication Required
- ✅ Must be logged in with admin email
- ✅ Admin emails whitelist: `ADMIN_EMAILS` in code

### RLS Policies
All tables have Row Level Security enabled:
- **trading_disclosures**: Authenticated users can CRUD
- **politicians**: Authenticated users can CRUD
- **action_logs**: Authenticated users can CRUD
- **scheduled_jobs**: Authenticated users can CRUD
- **user_sessions**: Users can only CRUD their own sessions

### Audit Trail
All CRUD operations can be logged to `action_logs` table for auditing.

## Best Practices

### 1. Always Review Before Deleting
- ⚠️ Deletion is permanent
- Export data as CSV before bulk deletions
- Keep backups of important data

### 2. Use Consistent Formats
- Dates: ISO 8601 format `YYYY-MM-DDTHH:MM:SSZ`
- Amounts: Use proper numeric types
- Enums: Check existing values for valid options

### 3. Test with Small Batches
- Insert one record first to test format
- Verify in Read/View tab before bulk operations
- Use test data before production data

### 4. Export Regularly
- Download CSVs for backup
- Keep historical snapshots
- Use for offline analysis

## Keyboard Shortcuts

- **Ctrl/Cmd + Enter** in JSON text area: Submit form (browser default)
- **Tab** in JSON text area: Indent (4 spaces)

## Troubleshooting

### Records Not Showing

**Check:**
1. Table exists in Supabase
2. RLS policies allow SELECT
3. Records actually exist (check Supabase dashboard)
4. No filters applied

### Insert Fails Silently

**Check:**
1. JSON is valid
2. Required fields are provided
3. Data types match schema
4. RLS policies allow INSERT

### Update Doesn't Change Data

**Check:**
1. ID column is correct
2. Updated fields are different from current
3. RLS policies allow UPDATE
4. No triggers preventing update

### Delete Button Disabled

**Reason:** Type "DELETE" in the confirmation box to enable

## API Reference

The CRUD interface uses these Supabase methods:

```python
# Read
conn.table(table_name).select("*").limit(50).execute()

# Create
conn.table(table_name).insert(data).execute()

# Update
conn.table(table_name).update(data).eq("id", record_id).execute()

# Delete
conn.table(table_name).delete().eq("id", record_id).execute()
```

## Future Enhancements

Planned features:
- [ ] Bulk insert from CSV
- [ ] Bulk update from CSV
- [ ] Advanced filtering and search
- [ ] Query builder UI
- [ ] Custom SQL queries
- [ ] Relationship visualization
- [ ] Column type validation
- [ ] Form-based editing (alternative to JSON)

## Support

- **Documentation:** `/docs/DATABASE_CRUD_GUIDE.md` (this file)
- **Database Setup:** `/SETUP_DATABASE.md`
- **Supabase Docs:** `/supabase/README.md`
- **Issues:** https://github.com/gwicho38/politician-trading-tracker/issues

## Summary

The Database CRUD interface provides a powerful, user-friendly way to manage your Supabase data directly from the Admin dashboard. All four CRUD operations (Create, Read, Update, Delete) are fully implemented with proper error handling, validation, and safety features.

**Key Features:**
- ✅ Full CRUD for all tables
- ✅ JSON-based data entry
- ✅ CSV export
- ✅ Safe deletion with confirmation
- ✅ Real-time data viewing
- ✅ Comprehensive error handling

Start using it now in **Admin** → **🗂️ Database CRUD**!
