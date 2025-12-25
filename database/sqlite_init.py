"""
SQLite Database Configuration for EduMate
Main database setup for local development
"""
import sqlite3
import os
from datetime import datetime

def create_sqlite_database():
    """Create SQLite database and tables"""
    
    # Remove existing database if it exists
    if os.path.exists('edumate_local.db'):
        os.remove('edumate_local.db')
    
    # Connect to SQLite database
    conn = sqlite3.connect('edumate_local.db')
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            id_number VARCHAR(20) UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'instructor', 'admin')),
            profile_picture TEXT DEFAULT NULL,
            bio TEXT DEFAULT NULL,
            interests TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            email_verified BOOLEAN DEFAULT FALSE,
            last_login TIMESTAMP NULL
        )
    """)
    
    # Create categories table
    cursor.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT DEFAULT NULL,
            parent_id INTEGER NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)
    
    # Create content table
    cursor.execute("""
        CREATE TABLE content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255) NOT NULL,
            description TEXT DEFAULT NULL,
            type TEXT NOT NULL CHECK (type IN ('pdf', 'video', 'link', 'document', 'presentation')),
            file_url VARCHAR(500) DEFAULT NULL,
            external_link VARCHAR(500) DEFAULT NULL,
            cover_image VARCHAR(500) DEFAULT NULL,
            difficulty_level TEXT NOT NULL CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
            tags TEXT DEFAULT NULL,
            uploaded_by INTEGER NOT NULL,
            category_id INTEGER NULL,
            is_published BOOLEAN DEFAULT FALSE,
            download_count INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            average_rating REAL DEFAULT 0.00,
            rating_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)
    
    # Create content_feedback table
    cursor.execute("""
        CREATE TABLE content_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT DEFAULT NULL,
            helpful BOOLEAN DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (content_id, user_id)
        )
    """)
    
    # Create user_activities table
    cursor.execute("""
        CREATE TABLE user_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL CHECK (activity_type IN ('viewed', 'downloaded', 'completed', 'bookmarked', 'in_progress')),
            progress_percentage INTEGER DEFAULT 0,
            time_spent_minutes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
        )
    """)
    
    # Create recommendations table
    cursor.execute("""
        CREATE TABLE recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            recommendation_type TEXT NOT NULL CHECK (recommendation_type IN ('rule_based', 'collaborative', 'content_based')),
            score REAL DEFAULT 0.0000,
            reason TEXT DEFAULT NULL,
            was_clicked BOOLEAN DEFAULT FALSE,
            was_helpful BOOLEAN DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
        )
    """)
    
    # Create user_preferences table
    cursor.execute("""
        CREATE TABLE user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            preferred_difficulty TEXT DEFAULT 'mixed' CHECK (preferred_difficulty IN ('beginner', 'intermediate', 'advanced', 'mixed')),
            preferred_content_types TEXT DEFAULT NULL,
            preferred_categories TEXT DEFAULT NULL,
            learning_goals TEXT DEFAULT NULL,
            notification_settings TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (user_id)
        )
    """)
    
    # Create learning_paths table
    cursor.execute("""
        CREATE TABLE learning_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255) NOT NULL,
            description TEXT DEFAULT NULL,
            created_by INTEGER NOT NULL,
            is_public BOOLEAN DEFAULT TRUE,
            difficulty_level TEXT NOT NULL CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
            estimated_hours INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Create path_content table
    cursor.execute("""
        CREATE TABLE path_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            order_index INTEGER NOT NULL,
            is_required BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (path_id) REFERENCES learning_paths(id) ON DELETE CASCADE,
            FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
        )
    """)
    
    # Create user_path_enrollments table
    cursor.execute("""
        CREATE TABLE user_path_enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            path_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            progress_percentage INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (path_id) REFERENCES learning_paths(id) ON DELETE CASCADE,
            UNIQUE (user_id, path_id)
        )
    """)
    
    # Create system_logs table
    cursor.execute("""
        CREATE TABLE system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NULL,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50) DEFAULT NULL,
            resource_id INTEGER DEFAULT NULL,
            ip_address VARCHAR(45) DEFAULT NULL,
            user_agent TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    
    # Create messages table for internal messaging system
    cursor.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            subject VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            message_type VARCHAR(20) DEFAULT 'personal' CHECK (message_type IN ('personal', 'system', 'announcement', 'feedback')),
            priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
            is_read BOOLEAN DEFAULT FALSE,
            is_deleted_by_sender BOOLEAN DEFAULT FALSE,
            is_deleted_by_receiver BOOLEAN DEFAULT FALSE,
            parent_message_id INTEGER NULL,
            related_content_id INTEGER NULL,
            related_user_id INTEGER NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL,
            FOREIGN KEY (related_content_id) REFERENCES content(id) ON DELETE SET NULL,
            FOREIGN KEY (related_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    
    # Create message_notifications table for notification settings
    cursor.execute("""
        CREATE TABLE message_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notification_type VARCHAR(30) NOT NULL CHECK (notification_type IN ('new_message', 'message_reply', 'system_announcement', 'content_feedback')),
            is_enabled BOOLEAN DEFAULT TRUE,
            email_enabled BOOLEAN DEFAULT FALSE,
            browser_push_enabled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (user_id, notification_type)
        )
    """)
    
    # Insert default users
    from werkzeug.security import generate_password_hash
    
    # Admin account
    admin_password = generate_password_hash('admin123')
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name, role, is_active, email_verified, id_number)
        VALUES ('admin@edumate.com', 'admin@edumate.com', ?, 'System Administrator', 'admin', TRUE, TRUE, 'ADM001')
    """, (admin_password,))
    
    # Instructor demo account
    instructor_password = generate_password_hash('instructor123')
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name, role, is_active, email_verified, id_number)
        VALUES ('test_instructor', 'instructor@edumate.com', ?, 'Test Instructor', 'instructor', TRUE, TRUE, 'INS001')
    """, (instructor_password,))
    
    # Student demo accounts
    student_password1 = generate_password_hash('student123')
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name, role, is_active, email_verified, id_number)
        VALUES ('test_student', 'student@edumate.com', ?, 'Test Student', 'student', TRUE, TRUE, 'STU001')
    """, (student_password1,))
    
    student_password2 = generate_password_hash('123123123')
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name, role, is_active, email_verified, id_number)
        VALUES ('zhuyuedong', 'zhuyuedong@edumate.com', ?, 'Zhu Yuedong', 'student', TRUE, TRUE, 'STU002')
    """, (student_password2,))
    
    # Insert default categories
    categories = [
        ('Computer Science', 'Computer science and programming topics'),
        ('Data Science', 'Data analysis, machine learning, and statistics'),
        ('Web Development', 'Frontend and backend web development'),
        ('Mobile Development', 'iOS and Android app development'),
        ('Database', 'Database design and management'),
        ('Mathematics', 'Mathematical concepts and applications'),
        ('Languages', 'Foreign language learning'),
        ('Business', 'Business and management topics')
    ]
    
    cursor.executemany("""
        INSERT INTO categories (name, description) VALUES (?, ?)
    """, categories)
    
    # Insert default message notification settings for all users
    cursor.execute("""
        INSERT INTO message_notifications (user_id, notification_type)
        SELECT id, 'new_message' FROM users
    """)
    
    cursor.execute("""
        INSERT INTO message_notifications (user_id, notification_type)
        SELECT id, 'message_reply' FROM users
    """)
    
    cursor.execute("""
        INSERT INTO message_notifications (user_id, notification_type)
        SELECT id, 'system_announcement' FROM users
    """)
    
    cursor.execute("""
        INSERT INTO message_notifications (user_id, notification_type)
        SELECT id, 'content_feedback' FROM users
    """)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("✅ SQLite database 'edumate_local.db' created successfully!")
    print("\n👤 Default users created:")
    print("\n🔹 Administrator:")
    print("   Username: admin@edumate.com")
    print("   Email: admin@edumate.com")
    print("   Password: admin123")
    print("   Role: admin")
    
    print("\n🔹 Test Instructor:")
    print("   Username: test_instructor")
    print("   Email: instructor@edumate.com")
    print("   Password: instructor123")
    print("   Role: instructor")
    
    print("\n🔹 Test Students:")
    print("   Username: test_student")
    print("   Email: student@edumate.com")
    print("   Password: student123")
    print("   Role: student")
    
    print("\n   Username: zhuyuedong")
    print("   Email: zhuyuedong@edumate.com")
    print("   Password: 123123123")
    print("   Role: student")

if __name__ == '__main__':
    create_sqlite_database()