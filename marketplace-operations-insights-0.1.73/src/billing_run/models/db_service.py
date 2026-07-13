import streamlit as st
import datetime
from typing import Callable, TypeVar, Dict, Any, Optional
import pandas as pd

T = TypeVar('T')  # For return type annotation

class DatabaseService:
    """Service class for database operations"""
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            cls._instance._last_refresh = {}
        return cls._instance
    
    def get_db_config(self):
        """Return the appropriate schema and database based on environment"""
        # Simply check if postgresql connection exists in secrets
        if "postgresql" in st.secrets["connections"]:
            return {"schema": "", "database": "postgresql"}
        else:
            return {"schema": "cc.", "database": "redshift"}
    
    def execute_query(self, query_func: Callable[..., T], **kwargs) -> T:
        """Execute a query function with the right DB config"""
        db_config = self.get_db_config()
        
        # Only add DB params if not already provided
        if "schema" not in kwargs:
            kwargs["schema"] = db_config["schema"]
        if "database" not in kwargs:
            kwargs["database"] = db_config["database"]
            
        # Execute and track refresh time
        result = query_func(**kwargs)
        self._last_refresh[query_func.__name__] = datetime.datetime.now()
        return result
    
    def get_last_refresh(self, func_name: str) -> Optional[datetime.datetime]:
        """Get last refresh time for a function"""
        return self._last_refresh.get(func_name)
      
    def format_last_refresh(self, func_name: str) -> str:
        """Format the last refresh time as a string like '5 minutes ago'"""
        refresh_time = self.get_last_refresh(func_name)
        if not refresh_time:
            return "Never refreshed"
        
        now = datetime.datetime.now()
        diff = now - refresh_time
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds // 3600 > 0:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds // 60 > 0:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return f"{diff.seconds} seconds ago" 