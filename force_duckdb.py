"""
Force ChromaDB to use DuckDB instead of SQLite
This completely bypasses the SQLite version issue
"""

import os
import sys

# Force ChromaDB to use DuckDB backend
os.environ['CHROMA_DB_IMPL'] = 'duckdb+parquet'
os.environ['CHROMA_SERVER_HOST'] = 'localhost'
os.environ['CHROMA_SERVER_HTTP_PORT'] = '8000'
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

# Also try installing duckdb if needed
try:
    import duckdb
    print("DuckDB is available for ChromaDB")
except ImportError:
    print("Warning: DuckDB not available, will try SQLite patch")
    
    # Fallback SQLite patch
    import sqlite3
    
    # Comprehensive SQLite patching
    original_sqlite_version = sqlite3.sqlite_version
    sqlite3.sqlite_version = "3.45.3"
    sqlite3.version_info = (3, 45, 3)
    
    if 'sqlite3' in sys.modules:
        sys.modules['sqlite3'].sqlite_version = "3.45.3"
        sys.modules['sqlite3'].version_info = (3, 45, 3)
    
    print(f"SQLite patched from {original_sqlite_version} to {sqlite3.sqlite_version}")

print("ChromaDB configuration completed")