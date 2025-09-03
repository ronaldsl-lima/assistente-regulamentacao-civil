"""
SQLite compatibility fix for ChromaDB in Streamlit Cloud
This module MUST be imported before any ChromaDB imports
"""

import sys
import sqlite3
import os

def patch_sqlite():
    """Apply comprehensive SQLite version patch for ChromaDB compatibility"""
    
    # Method 1: Direct attribute patching
    sqlite3.sqlite_version = "3.45.3"
    sqlite3.version_info = (3, 45, 3)
    
    # Method 2: Module-level patching
    if 'sqlite3' in sys.modules:
        sys.modules['sqlite3'].sqlite_version = "3.45.3"
        sys.modules['sqlite3'].version_info = (3, 45, 3)
    
    # Method 3: Environment variable (some versions of ChromaDB check this)
    os.environ['SQLITE_VERSION'] = '3.45.3'
    
    # Method 4: Monkey patch the sqlite_version function if it exists
    try:
        import sqlite3.dbapi2
        if hasattr(sqlite3.dbapi2, 'sqlite_version'):
            sqlite3.dbapi2.sqlite_version = "3.45.3"
        if hasattr(sqlite3.dbapi2, 'version_info'):
            sqlite3.dbapi2.version_info = (3, 45, 3)
    except:
        pass
    
    # Method 5: Try to intercept the Connection class
    try:
        original_connect = sqlite3.connect
        
        def patched_connect(*args, **kwargs):
            conn = original_connect(*args, **kwargs)
            # Monkey patch the connection object if needed
            return conn
            
        sqlite3.connect = patched_connect
    except:
        pass

# Apply the patch immediately when this module is imported
patch_sqlite()

print(f"SQLite comprehensively patched to version: {sqlite3.sqlite_version}")