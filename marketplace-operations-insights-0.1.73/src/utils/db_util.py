import streamlit as st
from typing import Dict
import numpy as np
from psycopg2.extensions import register_adapter, AsIs

conn = {}

def adapt_numpy_int64(n):
    return AsIs(int(n))

register_adapter(np.int64, adapt_numpy_int64)

def query(query: str, params: Dict = None, ttl: int = 3600, db="redshift"):
    global conn
    if db not in conn:
        conn[db] = st.connection(db, type="sql")

    # Convert all numpy.int64 in params to int
    if params:
        params = {k: int(v) if isinstance(v, np.int64) else v for k, v in params.items()}

    return conn[db].query(query, params=params, ttl=ttl)

def reset():
    global conn
    # close each connection
    for db in conn:
        conn[db].reset()
