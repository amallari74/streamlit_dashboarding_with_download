import re
from utils import db_util
import streamlit as st
import pandas as pd

def validate_schema_name(schema):
    """
    Validates that a schema name contains only allowed characters.
    Returns cleaned schema name with trailing dot if valid, raises ValueError if invalid.
    """
    if not schema:
        return ""
    
    # Only allow alphanumeric chars, underscores, and dots
    if not re.match(r'^[a-zA-Z0-9_\.]+$', schema):
        raise ValueError("Invalid schema name. Only alphanumeric characters, underscores, and dots are allowed.")
    
    # Ensure schema ends with a dot
    return schema if schema.endswith('.') else schema + '.'

@st.cache_data(ttl=300)
def fetch_latest_completed_tasks(schema="", database=None):
    """
    Fetches the latest completed tasks from multiple task tables.
    Timestamps are stored in UTC in both databases.
    
    Args:
        schema (str): Database schema prefix. Must contain only alphanumeric chars, underscores, and dots.
        database (str): Database to query.
        
    Raises:
        ValueError: If schema name contains invalid characters
    """
    try:
        schema = validate_schema_name(schema)
    except ValueError as e:
        st.error(str(e))
        return pd.DataFrame()

    # Define date functions - both databases store in UTC
    if database == "redshift":
        date_func = "DATE_TRUNC('month', CURRENT_DATE AT TIME ZONE 'UTC')"
        # For Redshift: ensure timestamp is returned with UTC timezone
        date_format = "updated_dt AT TIME ZONE 'UTC' as updated_dt"
    else:  # PostgreSQL
        date_func = "date_trunc('month', CURRENT_DATE AT TIME ZONE 'UTC')"
        # For PostgreSQL: ensure timestamp is returned with UTC timezone
        date_format = "updated_dt AT TIME ZONE 'UTC' as updated_dt"
    
    query = f"""
    WITH latest_tasks AS (
        -- Billing tasks - latest finished task
        SELECT 
            'billing_task' as table_name, 
            method, 
            {date_format},
            'Billing' as task_type,
            service as task_runner
        FROM {schema}billing_task
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}billing_task WHERE status='finished')
        AND status='finished'

        UNION ALL

        -- Billing task 2 - latest finished task
        SELECT 
            'billing_task_2' as table_name, 
            method, 
            {date_format},
            'Billing' as task_type,
            service as task_runner
        FROM {schema}billing_task_2
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}billing_task_2 WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- Arrears tasks - latest finished task
        SELECT 
            'arrears_task' as table_name, 
            method, 
            {date_format},
            'Arrears' as task_type,
            service as task_runner
        FROM {schema}arrears_task
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}arrears_task WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- Arrears task 2 - latest finished task
        SELECT 
            'arrears_task_2' as table_name, 
            method, 
            {date_format},
            'Arrears' as task_type,
            service as task_runner
        FROM {schema}arrears_task_2
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}arrears_task_2 WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- MCA task - latest finished task
        SELECT 
            'mca_task' as table_name, 
            method, 
            {date_format},
            'MCA' as task_type,
            service as task_runner
        FROM {schema}mca_task
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}mca_task WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- MCA task 2 - latest finished task  
        SELECT 
            'mca_task_2' as table_name, 
            method, 
            {date_format},
            'MCA' as task_type,
            service as task_runner
        FROM {schema}mca_task_2
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}mca_task_2 WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- MCA task 3 - latest finished task  
        SELECT 
            'mca_task_3' as table_name, 
            method, 
            {date_format},
            'MCA' as task_type,
            service as task_runner
        FROM {schema}mca_task_3
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}mca_task_3 WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- MCA task 4 - latest finished task  
        SELECT 
            'mca_task_4' as table_name, 
            method, 
            {date_format},
            'MCA' as task_type,
            service as task_runner
        FROM {schema}mca_task_4
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}mca_task_4 WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- MCA task 5 - latest finished task  
        SELECT 
            'mca_task_5' as table_name, 
            method, 
            {date_format},
            'MCA' as task_type,
            service as task_runner
        FROM {schema}mca_task_5
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}mca_task_5 WHERE status='finished')
        AND status='finished'
        
        UNION ALL
        
        -- Widget task - latest finished task
        SELECT 
            'widget_task' as table_name, 
            method, 
            {date_format},
            'Widget' as task_type,
            service as task_runner
        FROM {schema}widget_task
        WHERE updated_dt = (SELECT MAX(updated_dt) FROM {schema}widget_task WHERE status='finished')
        AND status='finished'
    ),
    
    ranked_tasks AS (
        SELECT 
            table_name,
            method,
            updated_dt,
            task_type,
            COALESCE(task_runner, 'unknown') as task_runner,
            ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY updated_dt DESC) as rn
        FROM latest_tasks
    )
    SELECT 
        table_name,
        method,
        updated_dt,
        task_type,
        task_runner
    FROM ranked_tasks
    WHERE rn = 1
    ORDER BY updated_dt DESC
    LIMIT 20
    """
    
    # Get data from database
    df = db_util.query(query, db=database, ttl=600)
    
    # Ensure timestamps are UTC-aware
    if not df.empty and 'updated_dt' in df.columns:
        # Timestamps from database are in UTC, make sure pandas knows this
        df['updated_dt'] = pd.to_datetime(df['updated_dt'], utc=True)
    
    return df

@st.cache_data(ttl=180)
def fetch_open_tasks_count(schema="", database=None):
    """
    Fetches the count of open tasks (status='new') from multiple task tables.
    
    Args:
        schema (str): Database schema prefix. Must contain only alphanumeric chars, underscores, and dots.
        database (str): Database to query.
        
    Raises:
        ValueError: If schema name contains invalid characters
    """
    try:
        schema = validate_schema_name(schema)
    except ValueError as e:
        st.error(str(e))
        return pd.DataFrame()

    tables = [
        'billing_task',
        'billing_task_2',
        'arrears_task',
        'arrears_task_2',
        'mca_task',
        'mca_task_2',
        'mca_task_3',
        'mca_task_4',
        'mca_task_5',
        'widget_task'
    ]
    
    # First, query for table existence and collect a comprehensive list of methods across all tables
    all_methods = set()
    table_exists = {}
    
    # Dictionary to store hourly completion counts for each table
    hourly_completion = {}
    
    for table in tables:
        try:
            # Check if the table exists and has open tasks
            existence_query = f"""
            SELECT table_name, method 
            FROM (
                SELECT '{table}' as table_name, method
                FROM {schema}{table}
                WHERE status='new'
                GROUP BY method
                UNION ALL
                SELECT '{table}' as table_name, method
                FROM {schema}{table}
                GROUP BY method
                LIMIT 1
            ) subquery
            LIMIT 10
            """
            
            try:
                result = db_util.query(existence_query, db=database, ttl=600)
                table_exists[table] = not result.empty
                
                # Collect methods from this table
                if not result.empty and 'method' in result.columns:
                    methods = result['method'].dropna().unique()
                    for method in methods:
                        all_methods.add(method)
            except Exception as e:
                import logging
                logging.error(f"Error checking if {table} exists: {str(e)}")
                print(f"Error checking if {table} exists: {str(e)}")
                table_exists[table] = False
        except:
            table_exists[table] = False
    
    # Add a default "unknown" method to ensure we always have at least one method
    if not all_methods:
        all_methods.add('unknown')
        
    # Query for tasks completed in the last hour for each table
    for table in tables:
        if table_exists.get(table, False):
            # Get DB-specific timestamp function - use UTC consistently
            if database == "redshift":
                hour_ago_func = "DATEADD(hour, -1, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"
            else:  # PostgreSQL 
                # Ensure we're using UTC consistently to match how updated_dt is stored
                hour_ago_func = "(NOW() AT TIME ZONE 'UTC') - INTERVAL '1 hour'"
                
            # For time consistency, make sure we're comparing UTC timestamps
            hourly_query = f"""
            SELECT '{table}' as table_name, 
                   COUNT(*) as hourly_count 
            FROM {schema}{table} 
            WHERE status='finished' 
              AND updated_dt >= {hour_ago_func}
            """
            
            try:
                result = db_util.query(hourly_query, db=database, ttl=180)
                if not result.empty:
                    hourly_completion[table] = int(result.iloc[0]['hourly_count'])
                else:
                    hourly_completion[table] = 0
            except Exception as e:
                print(f"Error querying hourly completion for {table}: {str(e)}")
                hourly_completion[table] = 0
        else:
            hourly_completion[table] = 0
    
    # Now query each table for open tasks with consistent result structure
    all_results = []
    
    for table in tables:
        if table_exists[table]:
            # Query for open tasks
            query = f"""
            SELECT '{table}' as table_name, 
                   COALESCE(method, 'unknown') as method, 
                   COUNT(*) as open_count 
            FROM {schema}{table} 
            WHERE status='new'
            GROUP BY method
            """
            
            try:
                result = db_util.query(query, db=database, ttl=600)
                if not result.empty:
                    all_results.append(result)
                else:
                    # Table exists but has no open tasks - add zero count for each known method
                    dummy_data = []
                    for method in all_methods:
                        dummy_data.append({
                            'table_name': table,
                            'method': method,
                            'open_count': 0
                        })
                    all_results.append(pd.DataFrame(dummy_data))
            except Exception as e:
                print(f"Error querying {table}: {str(e)}")
                # Add an error row
                dummy_df = pd.DataFrame({
                    'table_name': [table],
                    'method': ['error_querying'],
                    'open_count': [0]
                })
                all_results.append(dummy_df)
        else:
            # Table doesn't exist - add dummy row indicating table not found
            dummy_df = pd.DataFrame({
                'table_name': [table],
                'method': ['table_not_found'],
                'open_count': [0]
            })
            all_results.append(dummy_df)
    
    # Combine all results into a single DataFrame
    try:
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            
            # Ensure we have at least one row for each table to display
            for table in tables:
                if table not in combined_df['table_name'].values:
                    dummy_row = pd.DataFrame({
                        'table_name': [table],
                        'method': ['no_data'],
                        'open_count': [0]
                    })
                    combined_df = pd.concat([combined_df, dummy_row], ignore_index=True)
            
            # Add hourly completion counts to the dataframe
            # First, create a unique list of table names in the dataframe
            unique_tables = combined_df['table_name'].unique()
            
            # Create a mapping of table to hourly count
            hourly_data = []
            for table in unique_tables:
                hourly_data.append({
                    'table_name': table,
                    'hourly_completed': hourly_completion.get(table, 0)
                })
            
            # Convert to dataframe
            hourly_df = pd.DataFrame(hourly_data)
            
            # Merge with the original dataframe
            # Group by table_name first to avoid duplicating the hourly count for each method
            table_counts = combined_df.groupby('table_name').first().reset_index()[['table_name']]
            table_counts = pd.merge(table_counts, hourly_df, on='table_name', how='left')
            
            # Now put the hourly counts back into the original dataframe structure
            result_df = pd.merge(combined_df, table_counts[['table_name', 'hourly_completed']], 
                                on='table_name', how='left')
            
            return result_df
        else:
            # Create a DataFrame with one row per table, all showing zero open tasks
            dummy_data = []
            for table in tables:
                dummy_data.append({
                    'table_name': table,
                    'method': 'no_data',
                    'open_count': 0,
                    'hourly_completed': hourly_completion.get(table, 0)
                })
            return pd.DataFrame(dummy_data)
    except Exception as e:
        # Log the error and return a DataFrame with one row per table
        print(f"Error in fetch_open_tasks_count: {str(e)}")
        dummy_data = []
        for table in tables:
            dummy_data.append({
                'table_name': table,
                'method': 'error',
                'open_count': 0,
                'hourly_completed': 0
            })
        return pd.DataFrame(dummy_data)
