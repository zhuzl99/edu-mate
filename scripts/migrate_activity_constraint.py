#!/usr/bin/env python3
"""
Add unique constraint to user_activities table to prevent duplicate records
for the same user, content, and activity_type combination.
"""

import sqlite3
import os
from datetime import datetime

def migrate_activity_constraint():
    """Add unique constraint to user_activities table"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'edumate_local.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False
    
    print(f"Starting migration at {datetime.now()}")
    print(f"Database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Remove duplicate records first, keeping only the most recent one
        print("Removing duplicate activity records...")
        cursor.execute("""
            DELETE FROM user_activities 
            WHERE id NOT IN (
                SELECT MAX(id) 
                FROM user_activities 
                GROUP BY user_id, content_id, activity_type
            )
        """)
        
        deleted_count = cursor.rowcount
        print(f"Deleted {deleted_count} duplicate records")
        
        # Create new table with unique constraint
        print("Creating new table with unique constraint...")
        cursor.execute("""
            CREATE TABLE user_activities_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL CHECK (activity_type IN ('viewed', 'downloaded', 'completed', 'bookmarked')),
                progress_percentage INTEGER DEFAULT 0,
                time_spent_minutes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
                UNIQUE(user_id, content_id, activity_type)
            )
        """)
        
        # Copy data to new table
        print("Copying data to new table...")
        cursor.execute("""
            INSERT INTO user_activities_new (
                id, user_id, content_id, activity_type, 
                progress_percentage, time_spent_minutes, created_at
            )
            SELECT id, user_id, content_id, activity_type, 
                   progress_percentage, time_spent_minutes, created_at
            FROM user_activities
            ORDER BY created_at DESC
        """)
        
        copied_count = cursor.rowcount
        print(f"Copied {copied_count} records to new table")
        
        # Drop old table and rename new table
        print("Replacing old table...")
        cursor.execute("DROP TABLE user_activities")
        cursor.execute("ALTER TABLE user_activities_new RENAME TO user_activities")
        
        # Re-create indexes if needed
        cursor.execute("CREATE INDEX idx_user_activities_user_id ON user_activities(user_id)")
        cursor.execute("CREATE INDEX idx_user_activities_content_id ON user_activities(content_id)")
        cursor.execute("CREATE INDEX idx_user_activities_created_at ON user_activities(created_at DESC)")
        
        conn.commit()
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM user_activities")
        final_count = cursor.fetchone()[0]
        
        print(f"Migration completed successfully!")
        print(f"Final record count: {final_count}")
        print(f"Unique constraint added: (user_id, content_id, activity_type)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = migrate_activity_constraint()
    exit(0 if success else 1)