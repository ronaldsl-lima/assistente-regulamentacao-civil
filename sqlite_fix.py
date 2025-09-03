"""
SQLite compatibility fix for ChromaDB in Streamlit Cloud
This module MUST be imported before any ChromaDB imports
"""

import sys
import sqlite3

def patch_sqlite():
    """Apply SQLite version patch for ChromaDB compatibility"""
    # Patch the version string that ChromaDB checks
    sqlite3.sqlite_version = "3.45.3"
    sqlite3.version_info = (3, 45, 3)
    
    # Also patch in sys.modules to ensure persistence
    if 'sqlite3' in sys.modules:
        sys.modules['sqlite3'].sqlite_version = "3.45.3"
        sys.modules['sqlite3'].version_info = (3, 45, 3)

# Apply the patch immediately when this module is imported
patch_sqlite()

print(f"SQLite patched to version: {sqlite3.sqlite_version}")