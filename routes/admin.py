"""
Admin Routes - Administrative Dashboard and Management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

admin_bp = Blueprint('admin', __name__)

def get_db_connection():
    """Get database connection"""
    try:
        connection = sqlite3.connect('edumate_local.db')
        connection.row_factory = sqlite3.Row
        return connection
    except Exception as err:
        flash(f'Database error: {err}', 'error')
        return None

def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with system overview"""
    connection = get_db_connection()
    if not connection:
        return render_template('admin/dashboard.html', stats=None)
    
    try:
        cursor = connection.cursor()
        
        # Get system statistics
        stats = {}
        
        # User statistics
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        stats['total_users'] = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE is_active = 1")
        stats['active_users'] = cursor.fetchone()['active_users']
        
        cursor.execute("""
            SELECT role, COUNT(*) as count 
            FROM users 
            GROUP BY role
        """)
        user_roles = {row['role']: row['count'] for row in cursor.fetchall()}
        stats['user_roles'] = user_roles
        
        # Content statistics
        cursor.execute("SELECT COUNT(*) as total_content FROM content")
        stats['total_content'] = cursor.fetchone()['total_content']
        
        cursor.execute("SELECT COUNT(*) as published_content FROM content WHERE is_published = 1")
        stats['published_content'] = cursor.fetchone()['published_content']
        
        # Activity statistics
        cursor.execute("""
            SELECT COUNT(*) as total_activities 
            FROM user_activities 
            WHERE created_at >= date('now', '-7 days')
        """)
        stats['weekly_activities'] = cursor.fetchone()['total_activities']
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as active_learners 
            FROM user_activities 
            WHERE created_at >= date('now', '-7 days')
        """)
        stats['weekly_active_learners'] = cursor.fetchone()['active_learners']
        
        # Recent activities
        cursor.execute("""
            SELECT 
                sl.*, 
                u.full_name, 
                u.username
            FROM system_logs sl
            LEFT JOIN users u ON sl.user_id = u.id
            ORDER BY sl.created_at DESC
            LIMIT 10
        """)
        recent_logs = cursor.fetchall()
        
        # Top content
        cursor.execute("""
            SELECT 
                c.title, 
                c.view_count, 
                c.download_count,
                c.average_rating,
                cat.name as category_name
            FROM content c
            LEFT JOIN categories cat ON c.category_id = cat.id
            WHERE c.is_published = 1
            ORDER BY c.view_count DESC
            LIMIT 5
        """)
        top_content = cursor.fetchall()
        
        # User registration trends (last 30 days)
        cursor.execute("""
            SELECT 
                DATE(created_at) as reg_date,
                COUNT(*) as registrations
            FROM users
            WHERE created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY reg_date ASC
        """)
        registration_trends = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('admin/dashboard.html', 
                             stats=stats,
                             recent_logs=recent_logs,
                             top_content=top_content,
                             registration_trends=registration_trends)
    
    except Exception as err:
        flash(f'Error loading dashboard: {err}', 'error')
        return render_template('admin/dashboard.html', stats=None)

@admin_bp.route('/users')
@admin_required
def users():
    """Manage users"""
    connection = get_db_connection()
    if not connection:
        return render_template('admin/users.html', users_list=[])
    
    try:
        cursor = connection.cursor()
        
        # Get search and filter parameters
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        status_filter = request.args.get('status', '')
        
        # Build query
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("(username LIKE ? OR email LIKE ? OR full_name LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
        
        if role_filter:
            where_conditions.append("role = ?")
            params.append(role_filter)
        
        if status_filter:
            if status_filter == 'active':
                where_conditions.append("is_active = 1")
            elif status_filter == 'inactive':
                where_conditions.append("is_active = 0")
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get users
        cursor.execute(f"""
            SELECT * FROM users
            {where_clause}
            ORDER BY created_at DESC
        """, params)
        
        users_list = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('admin/users.html', 
                             users_list=users_list,
                             search_params=request.args)
    
    except Exception as err:
        flash(f'Error loading users: {err}', 'error')
        return render_template('admin/users.html', 
                             users_list=[],
                             search_params={'search': '', 'role': '', 'status': ''})

@admin_bp.route('/content')
@admin_required
def content():
    """Manage content"""
    connection = get_db_connection()
    if not connection:
        return render_template('admin/content.html', content_list=[])
    
    try:
        cursor = connection.cursor()
        
        # Get search and filter parameters
        search = request.args.get('search', '')
        type_filter = request.args.get('type', '')
        status_filter = request.args.get('status', '')
        
        # Build query
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("(c.title LIKE ? OR c.description LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        if type_filter:
            where_conditions.append("type = ?")
            params.append(type_filter)
        
        if status_filter:
            if status_filter == 'published':
                where_conditions.append("is_published = 1")
            elif status_filter == 'draft':
                where_conditions.append("is_published = 0")
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get content - explicitly list columns to avoid ambiguity
        cursor.execute(f"""
            SELECT 
                c.id,
                c.title,
                c.description,
                c.type,
                c.file_url,
                c.external_link,
                c.cover_image,
                c.difficulty_level,
                c.tags,
                c.uploaded_by,
                c.category_id,
                c.is_published,
                c.download_count,
                c.view_count,
                c.average_rating,
                c.rating_count,
                c.created_at,
                c.updated_at,
                cat.name as category_name,
                u.full_name as uploader_name
            FROM content c
            LEFT JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN users u ON c.uploaded_by = u.id
            {where_clause}
            ORDER BY c.created_at DESC
        """, params)
        
        content_list = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('admin/content.html', 
                             content_list=content_list,
                             search_params=request.args)
    
    except Exception as err:
        flash(f'Error loading content: {err}', 'error')
        return render_template('admin/content.html', 
                             content_list=[],
                             search_params={'search': '', 'type': '', 'status': ''})

@admin_bp.route('/analytics')
@admin_required
def analytics():
    """System analytics and reports"""
    connection = get_db_connection()
    if not connection:
        return render_template('admin/analytics.html', analytics_data=None)
    
    try:
        cursor = connection.cursor()
        
        # Learning analytics
        cursor.execute("""
            SELECT 
                DATE(ua.created_at) as activity_date,
                COUNT(DISTINCT ua.user_id) as active_users,
                COUNT(ua.id) as total_activities,
                AVG(ua.time_spent_minutes) as avg_time_spent
            FROM user_activities ua
            WHERE ua.created_at >= date('now', '-30 days')
            GROUP BY DATE(ua.created_at)
            ORDER BY activity_date ASC
        """)
        daily_activity = cursor.fetchall()
        
        # Content performance
        cursor.execute("""
            SELECT 
                c.type,
                COUNT(*) as content_count,
                AVG(c.average_rating) as avg_rating,
                SUM(c.view_count) as total_views,
                SUM(c.download_count) as total_downloads
            FROM content c
            WHERE c.is_published = 1
            GROUP BY c.type
        """)
        content_performance = cursor.fetchall()
        
        # Category distribution
        cursor.execute("""
            SELECT 
                cat.name,
                COUNT(c.id) as content_count,
                AVG(c.average_rating) as avg_rating,
                SUM(c.view_count) as total_views
            FROM categories cat
            LEFT JOIN content c ON cat.id = c.category_id AND c.is_published = TRUE
            GROUP BY cat.id, cat.name
            HAVING content_count > 0
            ORDER BY content_count DESC
        """)
        category_distribution = cursor.fetchall()
        
        # User engagement
        cursor.execute("""
            SELECT 
                u.role,
                COUNT(DISTINCT ua.user_id) as engaged_users,
                AVG(ua.time_spent_minutes) as avg_time_spent,
                COUNT(DISTINCT ua.content_id) as avg_content_viewed
            FROM users u
            LEFT JOIN user_activities ua ON u.id = ua.user_id
                AND ua.created_at >= date('now', '-30 days')
            GROUP BY u.role
        """)
        user_engagement = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        analytics_data = {
            'daily_activity': daily_activity,
            'content_performance': content_performance,
            'category_distribution': category_distribution,
            'user_engagement': user_engagement
        }
        
        return render_template('admin/analytics.html', analytics_data=analytics_data)
    
    except Exception as err:
        flash(f'Error loading analytics: {err}', 'error')
        return render_template('admin/analytics.html', analytics_data=None)

@admin_bp.route('/toggle-user/<int:user_id>')
@admin_required
def toggle_user(user_id):
    """Toggle user active status"""
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('admin.users'))
    
    try:
        cursor = connection.cursor()
        
        # Get current status
        cursor.execute("SELECT is_active FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            new_status = not user[0]
            cursor.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                (new_status, datetime.now(), user_id)
            )
            connection.commit()
            
            action = 'activated' if new_status else 'deactivated'
            flash(f'User {action} successfully', 'success')
        
        cursor.close()
        connection.close()
        
    except Exception as err:
        flash(f'Error updating user: {err}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/toggle-content/<int:content_id>', methods=['GET', 'POST'])
@admin_required
def toggle_content(content_id):
    """Toggle content published status"""
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('admin.content'))
    
    try:
        cursor = connection.cursor()
        
        # Get content details and current status
        cursor.execute("""
            SELECT is_published, title, uploaded_by 
            FROM content 
            WHERE id = ?
        """, (content_id,))
        content = cursor.fetchone()
        
        if content:
            new_status = not content[0]
            old_status = content[0]
            
            # Update content status
            cursor.execute(
                "UPDATE content SET is_published = ?, updated_at = ? WHERE id = ?",
                (new_status, datetime.now(), content_id)
            )
            
            # Send notification to content owner if status is changing from published to unpublished
            if old_status and not new_status:  # Content is being hidden/unpublished
                subject = "Content Hidden by Administrator"
                message_content = f"""
Dear Content Author,

Your content "{content[1]}" has been temporarily hidden by an administrator.

Reason: The content may not meet platform guidelines or requires review.

Please review your content and ensure it complies with EduMate's content policies. 
You can view and edit your content from your "My Content" page.

📝 Quick Actions:
• View Content: /content/{content_id}
• Edit Content: /content/{content_id}/edit
• My Content: /content/my-content

If you believe this action was taken in error, please contact the administration team or use the "Request Publish" button to request republication.

Content ID: {content_id}
Title: {content[1]}
Action taken on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Thank you for your understanding.

Best regards,
EduMate Administration Team
                """.strip()
                
                # Send system message to content owner
                try:
                    # Use admin user (ID=1) as sender for system messages
                    cursor.execute("""
                        INSERT INTO messages 
                        (sender_id, receiver_id, subject, content, message_type, 
                         related_content_id, sent_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (1, content[2], subject, message_content, 'feedback', 
                          content_id, datetime.now()))
                    
                    connection.commit()
                    flash(f'Content unpublished and notification sent to author successfully', 'success')
                except Exception as notification_err:
                    print(f"Failed to send notification: {notification_err}")
                    flash(f'Content unpublished but failed to send notification to author', 'warning')
            else:
                action = 'published' if new_status else 'unpublished'
                flash(f'Content {action} successfully', 'success')
            
            connection.commit()
        
        cursor.close()
        connection.close()
        
    except Exception as err:
        connection.rollback()
        flash(f'Error updating content: {err}', 'error')
        if 'connection' in locals() and connection:
            connection.close()
        
        # Even on error, check if there's a return_url parameter
        return_url = request.form.get('return_url') or request.referrer or url_for('admin.content')
        return redirect(return_url)
    
    # Check if there's a return_url parameter for successful operations
    return_url = request.form.get('return_url') or request.referrer or url_for('admin.content')
    return redirect(return_url)

@admin_bp.route('/clear-bookmarks', methods=['POST'])
@admin_required
def clear_bookmarks():
    """Clear all bookmarked content for all users"""
    connection = get_db_connection()
    if not connection:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        cursor = connection.cursor()
        
        # Count bookmarks before deletion
        cursor.execute("SELECT COUNT(*) as count FROM user_activities WHERE activity_type = 'bookmarked'")
        bookmark_count = cursor.fetchone()['count']
        
        if bookmark_count == 0:
            flash('No bookmarks found to clear', 'info')
            return redirect(url_for('admin.dashboard'))
        
        # Delete all bookmarked activities
        cursor.execute("DELETE FROM user_activities WHERE activity_type = 'bookmarked'")
        
        # Log the action
        cursor.execute("""
            INSERT INTO system_logs (user_id, action, resource_type, resource_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session['user_id'], 'CLEARED_ALL_BOOKMARKS', 'bookmarks', None, datetime.now()))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        flash(f'Successfully cleared {bookmark_count} bookmark records!', 'success')
        return redirect(url_for('admin.dashboard'))
        
    except Exception as err:
        flash(f'Error clearing bookmarks: {err}', 'error')
        return redirect(url_for('admin.dashboard'))