import streamlit as st
from utils import db_util

@st.cache_data(ttl=1800)
def get_data_freshness():
    """
    Query that checks the freshness of tables used in billing operations.
    Returns the schema, table name, and latest mountain time write for each table.
    """
    query = """
    with latest_times as (
      -- Original tables
      SELECT 'cc' AS schema, 'arrears_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.arrears_task
      UNION ALL
      SELECT 'event_cc' AS schema, 'arrears_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.arrears_task
      
      -- cc.arrears_task_2 and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'arrears_task_2' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.arrears_task_2
      UNION ALL
      SELECT 'event_cc' AS schema, 'arrears_task_2' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.arrears_task_2
      
      -- cc.billing_task and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'billing_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.billing_task
      UNION ALL
      SELECT 'event_cc' AS schema, 'billing_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.billing_task
      
      -- cc.billing_task_2 and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'billing_task_2' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.billing_task_2
      UNION ALL
      SELECT 'event_cc' AS schema, 'billing_task_2' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.billing_task_2
      
      -- cc.mca_task and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'mca_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.mca_task
      UNION ALL
      SELECT 'event_cc' AS schema, 'mca_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.mca_task
      
      -- cc.mca_task_2 and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'mca_task_2' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.mca_task_2
      UNION ALL
      SELECT 'event_cc' AS schema, 'mca_task_2' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.mca_task_2
      
      -- cc.mca_task_3 and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'mca_task_3' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.mca_task_3
      UNION ALL
      SELECT 'event_cc' AS schema, 'mca_task_3' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.mca_task_3
      
      -- cc.mca_task_4 and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'mca_task_4' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.mca_task_4
      UNION ALL
      SELECT 'event_cc' AS schema, 'mca_task_4' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.mca_task_4
      
      -- cc.mca_task_5 and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'mca_task_5' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.mca_task_5
      UNION ALL
      SELECT 'event_cc' AS schema, 'mca_task_5' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.mca_task_5
      
      -- cc.widget_task and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'widget_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.widget_task
      UNION ALL
      SELECT 'event_cc' AS schema, 'widget_task' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.widget_task
      
      -- cc.csv_invoice_row_archive and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'csv_invoice_row_archive' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.csv_invoice_row_archive
      UNION ALL
      SELECT 'event_cc' AS schema, 'csv_invoice_row_archive' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.csv_invoice_row_archive
      
      -- cc.invoice and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'invoice' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.invoice
      UNION ALL
      SELECT 'event_cc' AS schema, 'invoice' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.invoice
      
      -- cc.subscription and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'subscription' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.subscription
      UNION ALL
      SELECT 'event_cc' AS schema, 'subscription' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.subscription
      
      -- cc.product and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'product' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.product
      UNION ALL
      SELECT 'event_cc' AS schema, 'product' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.product
      
      -- cc.partner and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'partner' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.partner
      UNION ALL
      SELECT 'event_cc' AS schema, 'partner' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.partner
      
      -- cc.company and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'company' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.company
      UNION ALL
      SELECT 'event_cc' AS schema, 'company' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.company
      
      -- cc.business_unit_cache and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'business_unit_cache' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.business_unit_cache
      UNION ALL
      SELECT 'event_cc' AS schema, 'business_unit_cache' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.business_unit_cache
      
      -- cc.currency and event_cc equivalent
      UNION ALL
      SELECT 'cc' AS schema, 'currency' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM cc.currency
      UNION ALL
      SELECT 'event_cc' AS schema, 'currency' AS table_name, max(__ts_ms) AS latest_ts_ms
      FROM event_cc.currency
    )

    select schema, 
           table_name, 
           convert_timezone('UTC', 'America/Denver', (TIMESTAMP 'epoch' + (latest_ts_ms / 1000 ) * INTERVAL '1 second')) as latest_written_mountain
    from latest_times
    order by schema, table_name
    """
    
    return db_util.query(query, params={}, db="redshift")

def render_data_freshness_section():
    """
    Renders the data warehouse freshness section.
    Can be reused across different pages.
    """
    st.subheader("DataWarehouse Data Freshness")
    
    # Use a spinner while loading the data
    with st.spinner("Checking data freshness..."):
        try:
            freshness_df = get_data_freshness()
            
            # Display the freshness data
            if not freshness_df.empty:
                # Create schema filter
                schemas = sorted(freshness_df['schema'].unique())
                selected_schema = st.selectbox("Filter by Schema:", schemas, index=0)
                
                # Filter the data based on selected schema
                filtered_df = freshness_df[freshness_df['schema'] == selected_schema]
                
                # Display the filtered data
                st.dataframe(filtered_df[['schema', 'table_name', 'latest_written_mountain']], 
                             use_container_width=True, 
                             column_config={
                                 "schema": "Schema",
                                 "table_name": "Table Name",
                                 "latest_written_mountain": st.column_config.DatetimeColumn("Latest Update (Mountain Time)")
                             })
            else:
                st.warning("No data freshness information available.")
        except Exception as e:
            st.error(f"Error retrieving data freshness information: {e}") 