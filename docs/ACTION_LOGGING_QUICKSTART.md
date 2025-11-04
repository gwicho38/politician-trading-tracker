# Action Logging System - Quick Start Guide

## ✅ System Status: ACTIVE

The global action logging system is now installed and operational!

## 🎯 What's Working

All system actions are now being logged:
- ✅ Manual data collection actions
- ✅ Ticker backfill operations
- ✅ Scheduled job executions
- ✅ Job control actions (pause/resume/run/remove)

## 📋 Viewing Action Logs

1. Open your Streamlit app
2. Navigate to **Action Logs** page (📋 icon in sidebar)
3. Explore the three tabs:
   - **Recent Actions**: See all logged actions with filters
   - **Statistics**: View 7-day summaries and success rates
   - **Failed Actions**: Quickly identify and troubleshoot errors

## 🔍 What You'll See

The test script created 3 test actions:
- `test_action` (completed)
- `test_workflow` (completed)
- `test_failure` (failed)

These will appear in your Action Logs page. Once you trigger real actions (like data collection), you'll see them logged there too!

## 📊 Action Types Being Logged

| Action Type | Trigger | What It Captures |
|------------|---------|------------------|
| `data_collection_start` | "🚀 Start Collection" button | Sources, lookback days, results |
| `ticker_backfill` | "🔄 Backfill Missing Tickers" button | Records updated/not found |
| `job_execution` | Scheduled jobs running | Job ID, duration, success/failure |
| `job_pause` | "⏸️ Pause" button | Job paused |
| `job_resume` | "▶️ Resume" button | Job resumed |
| `job_manual_run` | "▶️ Run Now" button | Manual job trigger |
| `job_remove` | "🗑️ Remove" button | Job removed |

## 🧪 Test It Out

### Quick Test:
1. Go to **Data Collection** page
2. Click "🚀 Start Collection" (even with no sources selected)
3. Go to **Action Logs** page
4. You should see your collection action logged!

### What to Check:
- ✅ Action appears in Recent Actions
- ✅ Timestamp is correct
- ✅ Your user email is captured
- ✅ Status shows completed or failed appropriately
- ✅ Duration is calculated
- ✅ Details are captured in action_details

## 📈 Monitoring Tips

### Daily Checks:
- Review **Failed Actions** tab for any errors
- Check **Statistics** tab for success rates
- Monitor average action durations

### Weekly Reviews:
- Analyze user activity patterns
- Identify frequently failing actions
- Review action frequency trends

### Troubleshooting:
If actions aren't being logged:
1. Check Supabase connection in app logs
2. Verify `action_logs` table exists in database
3. Check for any error messages in application logs
4. Run the test script: `uv run python scripts/test_action_logging.py`

## 🔗 Database Queries

### View Recent Actions (SQL):
```sql
SELECT
  action_timestamp,
  action_type,
  action_name,
  status,
  user_id,
  duration_seconds
FROM action_logs
ORDER BY action_timestamp DESC
LIMIT 50;
```

### Check Success Rates:
```sql
SELECT * FROM action_logs_summary
ORDER BY total_count DESC;
```

### Find Failed Actions:
```sql
SELECT
  action_timestamp,
  action_type,
  user_id,
  error_message
FROM action_logs
WHERE status = 'failed'
ORDER BY action_timestamp DESC
LIMIT 20;
```

### User Activity:
```sql
SELECT * FROM user_activity_summary
ORDER BY total_actions DESC;
```

## 💡 Pro Tips

1. **Use Filters**: The Action Logs page has powerful filters - use them to narrow down searches
2. **Check Failed Actions First**: Start your day by reviewing the Failed Actions tab
3. **Monitor Durations**: Unusually long durations might indicate performance issues
4. **Track Patterns**: Use the Statistics tab to spot usage patterns over time
5. **Export Data**: You can query the database directly for custom reports

## 🎯 Success Metrics

Monitor these to ensure system health:
- **Overall Success Rate**: Should be >95%
- **Average Action Duration**: Track for performance trends
- **Failed Action Count**: Should be minimal
- **User Activity**: Track engagement levels

## 📚 Additional Resources

- **Full Implementation Guide**: `docs/implementation/action_logging_implementation.md`
- **Detailed Action Guide**: `docs/ACTION_LOGGING_GUIDE.md`
- **Architecture Overview**: `docs/CODEBASE_ARCHITECTURE.md`
- **GitHub Issue**: [#11](https://github.com/gwicho38/politician-trading-tracker/issues/11)

## 🆘 Support

If you encounter issues:
1. Check application logs for errors
2. Run the test script to verify system functionality
3. Review the troubleshooting section in `ACTION_LOGGING_GUIDE.md`
4. Check GitHub issue #11 for known issues and solutions

---

**Status**: ✅ System Active and Tested
**Last Updated**: November 3, 2025
**Test Results**: 6/6 tests passed
