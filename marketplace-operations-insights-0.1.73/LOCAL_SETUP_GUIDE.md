# Local Setup Guide - Using Read Replica

This guide will help you set up the Marketplace Operations Insights application locally using a PostgreSQL read replica instead of Redshift.

## 🚀 Quick Setup

### 1. Prerequisites

- **Python 3.11** (installed via Homebrew)
- **PostgreSQL client libraries** 
- **Access to PostgreSQL read replica** credentials

### 2. Run Setup Script

```bash
# Make setup script executable and run it
chmod +x setup.sh
./setup.sh
```

This will:
- Create a Python 3.11 virtual environment
- Install all dependencies
- Set up the secrets template
- Install `psycopg2` for PostgreSQL connectivity

### 3. Configure Database Connection

Edit `.streamlit/secrets.toml` and **add the PostgreSQL connection**:

```toml
[connections.redshift]
type = "sql"
url = "redshift+redshift_connector://<user>:<password>@<db_url>:5439/pax8dw?sslmode=prefer"

# Add this section for PostgreSQL read replica
[connections.postgresql]
type = "sql"
url = "postgresql://<username>:<password>@<read_replica_host>:<port>/<database_name>?sslmode=require"

[auth]
app_password="your_app_password"

[auth0]
enabled = true
domain = "p8p-production.us.auth0.com"
client_id = "your_client_id"
client_secret = "your_client_secret"
callback_url = "http://localhost:8501/"
audience = "https://p8p-production.us.auth0.com/userinfo"
cookie_secret = "your_alphanumeric_cookie_secret"

[jira]
username = "your_jira_username"
password = "your_jira_password"
url = "https://your-instance.atlassian.net"
```

### 4. PostgreSQL Connection String Format

```toml
[connections.postgresql]
type = "sql"
url = "postgresql://username:password@hostname:5432/database_name?sslmode=require"
```

**Example:**
```toml
[connections.postgresql]
type = "sql"
url = "postgresql://readonly_user:password123@prod-replica.amazonaws.com:5432/pax8dw?sslmode=require"
```

### 5. Start the Application

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Start Streamlit
streamlit run src/app.py
```

The app will be available at: http://localhost:8501

## 🔧 Database Priority Logic

The application automatically **prioritizes PostgreSQL over Redshift** when available:

1. **PostgreSQL (Read Replica)** - Used when `[connections.postgresql]` exists in secrets
2. **Redshift** - Fallback when PostgreSQL is not configured

This is handled in `src/billing_run/models/db_service.py`:

```python
def get_db_config(self):
    """Return the appropriate schema and database based on environment"""
    if "postgresql" in st.secrets["connections"]:
        return {"schema": "", "database": "postgresql"}
    else:
        return {"schema": "cc.", "database": "redshift"}
```

## 🎯 Invoice Task Duration Monitoring with Read Replica

Your new **Invoice Task Duration Monitoring** feature will automatically use the PostgreSQL read replica when configured. The monitoring page allows you to:

1. **Select Database**: Choose between `postgresql` and `redshift` in the UI
2. **Default Behavior**: Uses PostgreSQL when available
3. **Same Schema**: Works with both databases (schema differences handled automatically)

## 📊 Schema Differences

| Database | Schema Prefix | Example Table |
|----------|---------------|---------------|
| **PostgreSQL** | _(none)_ | `billing_task` |
| **Redshift** | `cc.` | `cc.billing_task` |

The application handles this automatically - when using PostgreSQL, no schema prefix is added.

## 🛠️ Troubleshooting

### Connection Issues

**Problem**: "PostgreSQL connection not configured"
**Solution**: Ensure `[connections.postgresql]` section exists in `.streamlit/secrets.toml`

**Problem**: Connection timeout or refused
**Solutions**:
- Verify read replica hostname and port
- Check VPN/network access to database
- Validate username/password credentials
- Ensure SSL mode is correct (`require` vs `prefer`)

### Dependencies Issues

**Problem**: `psycopg2` installation fails
**Solutions**:
```bash
# Try installing PostgreSQL development headers
brew install postgresql

# Or install binary version
pip install psycopg2-binary
```

**Problem**: Python version issues
**Solution**: Ensure Python 3.11 is installed:
```bash
brew install python@3.11
```

### Performance Considerations

1. **Read Replica Lag**: Data might be slightly behind primary database
2. **Query Timeout**: Large date ranges may timeout - reduce scope if needed
3. **Connection Limits**: Read replicas may have connection limits

## 🔍 Verifying Read Replica Usage

You can verify the application is using PostgreSQL by:

1. **Task Manager Page**: Look for "Read Replica" section
2. **Database Selector**: In Invoice Task Duration Monitoring, `postgresql` will be available
3. **Logs**: Check Streamlit logs for connection details

## 📈 Performance Benefits

Using the read replica provides:

✅ **Reduced load** on production database  
✅ **Better query performance** for analytics  
✅ **Isolation** from production workloads  
✅ **Lower latency** (if replica is geographically closer)

## 🚨 Important Notes

1. **Read-Only**: PostgreSQL connection should be read-only for safety
2. **Data Freshness**: Read replica may have slight lag vs primary database
3. **Failover**: Application will fallback to Redshift if PostgreSQL fails
4. **Security**: Use strong passwords and SSL connections

## 📝 Environment Variables (Alternative Setup)

Instead of editing `secrets.toml`, you can also set environment variables:

```bash
export POSTGRESQL_URL="postgresql://user:pass@host:5432/db"
export REDSHIFT_URL="redshift+redshift_connector://user:pass@host:5439/db"
```

## 🎉 Next Steps

After setup:

1. Navigate to **Billing & Invoicing** → **Billing Analytics** → **Invoice Task Duration**
2. Select `postgresql` database in the dropdown
3. Choose your date range
4. Monitor invoice task performance with real-time alerting!

The monitoring will show alerts when:
- 🚨 **Critical**: Total runtime > 24 hours
- ⚠️ **Warning**: Individual tasks > 30 minutes

Happy monitoring! 🚀
