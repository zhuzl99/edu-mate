#!/usr/bin/env python3
"""
Database Migration: Add Unique Constraint to user_activities for bookmarks
This migration adds a unique constraint to prevent duplicate bookmarks
"""
import sqlite3
import os

def migrate_bookmark_constraint():
    """Add unique constraint for bookmarked activities"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'edumate_local.db')
    
    if not os.path.exists(db_path):
        print("Database not found. Please run the application first.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Starting bookmark constraint migration...")
        
        # First, remove duplicate bookmarks (keep the first one)
        print("Removing duplicate bookmark records...")
        cursor.execute("""
            DELETE FROM user_activities 
            WHERE id NOT IN (
                SELECT MIN(id) 
                FROM user_activities 
                WHERE activity_type = 'bookmarked' 
                GROUP BY user_id, content_id
            ) AND activity_type = 'bookmarked'
        """)
        
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            print(f"Removed {deleted_count} duplicate bookmark records")
        
        # Create a new table with unique constraint
        print("Creating new user_activities table with unique constraint...")
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
                UNIQUE (user_id, content_id, activity_type)
            )
        """)
        
        # Copy data from old table to new table
        print("Copying data to new table...")
        cursor.execute("""
            INSERT INTO user_activities_new (
                id, user_id, content_id, activity_type, 
                progress_percentage, time_spent_minutes, created_at
            )
            SELECT id, user_id, content_id, activity_type, 
                   progress_percentage, time_spent_minutes, created_at
            FROM user_activities
        """)
        
        # Drop old table and rename new table
        print("Replacing old table...")
        cursor.execute("DROP TABLE user_activities")
        cursor.execute("ALTER TABLE user_activities_new RENAME TO user_activities")
        
        # Recreate indexes if needed
        cursor.execute("CREATE INDEX idx_user_activities_user_content ON user_activities(user_id, content_id)")
        cursor.execute("CREATE INDEX idx_user_activities_type ON user_activities(activity_type)")
        
        conn.commit()
        conn.close()
        
        print("✅ Bookmark constraint migration completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error during migration: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    migrate_bookmark_constraint()