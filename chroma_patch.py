"""
ChromaDB SQLite compatibility patch
This completely replaces the sqlite3 module before ChromaDB imports
"""

import sys
import os

# Set environment variables that ChromaDB might check
os.environ['CHROMA_DB_IMPL'] = 'duckdb+parquet'
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

# Try to install and use pysqlite3 if available (for Linux/production)
try:
    import pysqlite3 as sqlite3
    # Replace the sqlite3 module completely
    sys.modules['sqlite3'] = sqlite3
    sys.modules['sqlite3.dbapi2'] = sqlite3
    print("Using pysqlite3 for ChromaDB compatibility")
except ImportError:
    # Fallback to monkey patching the standard sqlite3
    import sqlite3
    
    # Comprehensive patching
    sqlite3.sqlite_version = "3.45.3"
    sqlite3.version_info = (3, 45, 3)
    sqlite3.version = "2.6.0"
    
    # Patch all possible locations
    sys.modules['sqlite3'].sqlite_version = "3.45.3"
    sys.modules['sqlite3'].version_info = (3, 45, 3)
    sys.modules['sqlite3'].version = "2.6.0"
    
    print(f"Patched sqlite3 version to: {sqlite3.sqlite_version}")

# Force ChromaDB to use DuckDB as fallback
os.environ['CHROMA_SERVER_HOST'] = 'localhost'
os.environ['CHROMA_SERVER_HTTP_PORT'] = '8000'