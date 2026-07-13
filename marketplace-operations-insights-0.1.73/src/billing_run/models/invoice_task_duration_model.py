"""
Model for invoice task duration analysis and monitoring.
Provides functions to fetch and analyze run durations for createPartnerInvoice and createCompanyInvoice tasks.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
from utils import db_util
from queries.queries import Queries


@st.cache_data(ttl=300)
def fetch_invoice_task_duration_analysis(start_date: str, end_date: str, database: str = None) -> pd.DataFrame:
    """
    Fetch invoice task duration analysis with alerting for the specified date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format  
        database (str, optional): Database to query. Defaults to None.
        
    Returns:
        pd.DataFrame: DataFrame containing duration analysis with alert flags
    """
    # Get the appropriate schema prefix based on database
    schema_prefix = ""
    if database == "redshift":
        schema_prefix = "cc."
    elif database == "postgresql":
        schema_prefix = ""
    else:
        # Auto-detect based on available connections
        if "postgresql" in st.secrets.get("connections", {}):
            schema_prefix = ""
            database = "postgresql"
        else:
            schema_prefix = "cc."
            database = "redshift"
    
    # Get the query and replace table names with schema-prefixed versions
    query = Queries.get_invoice_task_duration_analysis(start_date, end_date)
    
    # Handle database-specific syntax differences
    if database == "redshift":
        # Add schema prefix to all table names for Redshift
        tables_to_prefix = [
            "billing_task", "billing_task_2", 
            "mca_task", "mca_task_2", "mca_task_3", "mca_task_4", "mca_task_5"
        ]
        for table in tables_to_prefix:
            query = query.replace(f"FROM {table} ", f"FROM {schema_prefix}{table} ")
        
        # Replace PostgreSQL JSON syntax with Redshift JSON syntax with error handling
        # PostgreSQL: (payload::json->'invoiceDate'->>'value')::date
        # Redshift: JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date with IS_VALID_JSON check
        query = query.replace(
            "(payload::json->'invoiceDate'->>'value')::date",
            "CASE WHEN IS_VALID_JSON(payload) THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date ELSE NULL END"
        )
    elif schema_prefix:
        # Handle other databases that might need schema prefix
        tables_to_prefix = [
            "billing_task", "billing_task_2", 
            "mca_task", "mca_task_2", "mca_task_3", "mca_task_4", "mca_task_5"
        ]
        for table in tables_to_prefix:
            query = query.replace(f"FROM {table} ", f"FROM {schema_prefix}{table} ")
    
    params = {
        "start_date": start_date,
        "end_date": end_date
    }
    
    try:
        result_df = db_util.query(query, params=params, db=database)
        
        # Basic validation of query results
        if result_df.empty:
            pass  # Will be handled by empty DataFrame logic below
            
        # Ensure required columns exist - add them if missing to prevent KeyError
        required_columns = [
            'alert_24hr_exceeded', 'alert_30min_task_exceeded', 'alert_message',
            'total_runtime_hours', 'invoice_date', 'task_table', 'method'
        ]
        
        for col in required_columns:
            if col not in result_df.columns:
                if col in ['alert_24hr_exceeded', 'alert_30min_task_exceeded']:
                    result_df[col] = False
                elif col == 'alert_message':
                    result_df[col] = None
                elif col == 'total_runtime_hours':
                    result_df[col] = 0.0
                else:
                    result_df[col] = ''
        
        return result_df
        
    except Exception as e:
        # Return empty DataFrame with required columns if query fails
        import pandas as pd
        empty_df = pd.DataFrame(columns=[
            'task_table', 'invoice_date', 'method', 'total_tasks',
            'min_runtime_ms', 'max_runtime_ms', 'avg_runtime_ms', 'total_runtime_ms',
            'min_runtime_sec', 'max_runtime_sec', 'avg_runtime_sec', 'total_runtime_sec',
            'total_runtime_min', 'total_runtime_hours',
            'p50_runtime_sec', 'p95_runtime_sec', 'p99_runtime_sec',
            'alert_24hr_exceeded', 'alert_30min_task_exceeded', 'alert_message'
        ])
        return empty_df


def get_alert_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate summary of alerts from the duration analysis data.
    
    Args:
        df (pd.DataFrame): DataFrame from fetch_invoice_task_duration_analysis
        
    Returns:
        Dict[str, Any]: Summary of alerts and metrics
    """
    if df.empty:
        return {
            "total_alerts": 0,
            "critical_alerts": 0,
            "warning_alerts": 0,
            "alert_details": [],
            "max_runtime_hours": 0,
            "affected_dates": []
        }
    
    # Count alerts - handle missing columns gracefully
    try:
        critical_alerts = df[df['alert_24hr_exceeded'] == True] if 'alert_24hr_exceeded' in df.columns else pd.DataFrame()
        warning_alerts = df[df['alert_30min_task_exceeded'] == True] if 'alert_30min_task_exceeded' in df.columns else pd.DataFrame()
    except (KeyError, AttributeError):
        critical_alerts = pd.DataFrame()
        warning_alerts = pd.DataFrame()
    
    alert_details = []
    
    # Add critical alerts
    for _, row in critical_alerts.iterrows():
        alert_details.append({
            "severity": "CRITICAL",
            "date": row.get('invoice_date'),
            "table": row.get('task_table'),
            "method": row.get('method'),
            "runtime_hours": row.get('total_runtime_hours', 0),
            "total_tasks": row.get('total_tasks', 0),
            "message": f"Total runtime {row.get('total_runtime_hours', 0):.2f}h exceeds 24h threshold"
        })
    
    # Add warning alerts
    for _, row in warning_alerts.iterrows():
        if row.get('alert_24hr_exceeded') != True:  # Don't double-count critical alerts
            alert_details.append({
                "severity": "WARNING", 
                "date": row.get('invoice_date'),
                "table": row.get('task_table'),
                "method": row.get('method'),
                "max_runtime_sec": row.get('max_runtime_sec', 0),
                "total_tasks": row.get('total_tasks', 0),
                "message": f"Individual task {row.get('max_runtime_sec', 0):.2f}s exceeds 30min threshold"
            })
    
    return {
        "total_alerts": len(alert_details),
        "critical_alerts": len(critical_alerts),
        "warning_alerts": len(warning_alerts) - len(critical_alerts.merge(warning_alerts, how='inner')),
        "alert_details": sorted(alert_details, key=lambda x: (x.get('date', ''), x['severity']), reverse=True),
        "max_runtime_hours": df['total_runtime_hours'].max() if 'total_runtime_hours' in df.columns else 0,
        "affected_dates": sorted(df[df['alert_message'].notna()]['invoice_date'].unique().tolist(), reverse=True) if 'alert_message' in df.columns else []
    }


def get_performance_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate performance summary statistics from the duration analysis data.
    
    Args:
        df (pd.DataFrame): DataFrame from fetch_invoice_task_duration_analysis
        
    Returns:
        Dict[str, Any]: Performance summary metrics
    """
    if df.empty:
        return {
            "total_tasks": 0,
            "total_runtime_hours": 0,
            "avg_runtime_sec": 0,
            "p95_runtime_sec": 0,
            "slowest_task_table": "N/A",
            "date_range_days": 0
        }
    
    # Calculate summary metrics
    total_tasks = df['total_tasks'].sum()
    total_runtime_hours = df['total_runtime_hours'].sum()
    
    # Weight average by task count
    if total_tasks > 0:
        weighted_avg_runtime = (df['avg_runtime_sec'] * df['total_tasks']).sum() / total_tasks
    else:
        weighted_avg_runtime = 0
        
    # Find slowest performing table
    slowest_idx = df['total_runtime_hours'].idxmax() if not df.empty else None
    slowest_task_table = df.loc[slowest_idx, 'task_table'] if slowest_idx is not None else "N/A"
    
    # Calculate date range
    if 'invoice_date' in df.columns and not df['invoice_date'].isna().all():
        date_range_days = (pd.to_datetime(df['invoice_date'].max()) - pd.to_datetime(df['invoice_date'].min())).days + 1
    else:
        date_range_days = 0
    
    return {
        "total_tasks": int(total_tasks),
        "total_runtime_hours": round(total_runtime_hours, 2),
        "avg_runtime_sec": round(weighted_avg_runtime, 2),
        "p95_runtime_sec": round(df['p95_runtime_sec'].max() if 'p95_runtime_sec' in df.columns else 0, 2),
        "slowest_task_table": slowest_task_table,
        "date_range_days": date_range_days
    }


def get_default_date_range() -> tuple[str, str]:
    """
    Get default date range for the analysis (last 30 days).
    
    Returns:
        tuple[str, str]: (start_date, end_date) in YYYY-MM-DD format
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def format_runtime_display(seconds: float) -> str:
    """
    Format runtime seconds into a human-readable string.
    
    Args:
        seconds (float): Runtime in seconds
        
    Returns:
        str: Formatted runtime string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
