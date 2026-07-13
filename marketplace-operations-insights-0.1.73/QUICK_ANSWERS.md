# Quick Answers - Running Locally with Read Replica

## ❓ Your Questions Answered

### Q: How can I run this locally?

**A: Use the automated setup script:**

```bash
./setup.sh
```

Then configure your database credentials and start the app:

```bash
streamlit run src/app.py
```

**Full details in:** [LOCAL_SETUP_GUIDE.md](./LOCAL_SETUP_GUIDE.md)

---

### Q: Does it use Redshift?

**A: It can use either Redshift OR PostgreSQL (your choice):**

- **PostgreSQL** (read replica) - **PREFERRED** when available
- **Redshift** - Fallback option

The application **automatically chooses PostgreSQL over Redshift** when both are configured.

---

### Q: I want it to use read replica

**A: Perfect! The app is designed for this. Add PostgreSQL configuration:**

**Step 1:** Edit `.streamlit/secrets.toml` and add:

```toml
[connections.postgresql]
type = "sql"
url = "postgresql://username:password@read-replica-host:5432/database?sslmode=require"
```

**Step 2:** The app will automatically use PostgreSQL instead of Redshift

**Step 3:** In the Invoice Task Duration Monitoring page, select `postgresql` from the database dropdown

---

## 🎯 Key Benefits of Read Replica Setup

✅ **Better Performance** - Dedicated read capacity  
✅ **Reduced Load** - No impact on production database  
✅ **Lower Latency** - Optimized for analytics queries  
✅ **Automatic Failover** - Falls back to Redshift if needed  

---

## 🚀 Your Invoice Task Duration Monitoring

Your new monitoring feature will work perfectly with the read replica:

1. **Navigate to:** Billing & Invoicing → Billing Analytics → **Invoice Task Duration**
2. **Select Database:** Choose `postgresql` (read replica)
3. **Set Date Range:** Default is last 30 days
4. **Monitor Alerts:** 
   - 🚨 Critical: >24 hours total runtime
   - ⚠️ Warning: >30 minutes individual tasks

---

## 💡 Quick Start Commands

```bash
# 1. Setup
./setup.sh

# 2. Configure PostgreSQL in .streamlit/secrets.toml
# [connections.postgresql]
# url = "postgresql://user:pass@replica-host:5432/db?sslmode=require"

# 3. Start app
streamlit run src/app.py

# 4. Visit: http://localhost:8501
```

---

## 🔧 Database Priority Logic

```python
# Application automatically prefers PostgreSQL
if "postgresql" in st.secrets["connections"]:
    return {"schema": "", "database": "postgresql"}  # ← Uses this
else:
    return {"schema": "cc.", "database": "redshift"}   # ← Fallback
```

**Result:** No code changes needed - just configure PostgreSQL and it's automatically preferred!

---

## 📞 Need Help?

- **Setup Issues:** See [LOCAL_SETUP_GUIDE.md](./LOCAL_SETUP_GUIDE.md)
- **Database Config:** Check `secrets.postgresql.example.toml`
- **Troubleshooting:** Review connection string format and credentials
