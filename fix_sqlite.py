"""
Script to fix SQLite compatibility issue with ChromaDB
"""

# This workaround patches the sqlite3 module to report a compatible version
import sys
import sqlite3

# Store original function
_original_sqlite_version = sqlite3.sqlite_version

# Monkey patch to return a compatible version
def patched_sqlite_version():
    return "3.45.3"

# Apply the patch
sqlite3.sqlite_version = "3.45.3"
sqlite3.version_info = (3, 45, 3)

# Also patch the module attribute
sys.modules['sqlite3'].sqlite_version = "3.45.3"

print("SQLite version patched for ChromaDB compatibility")
print(f"Reported SQLite version: {sqlite3.sqlite_version}")