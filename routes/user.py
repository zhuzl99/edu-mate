"""
User Management Routes - Profile, Settings, Preferences
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

user_bp = Blueprint('user', __name__)

def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('edumate_local.db')
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    except Exception as err:
        flash(f'Database error: {err}', 'error')
        return None

@user_bp.route('/profile')
def profile():
    """Display user profile"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    connection = get_db_connection()
    if not connection:
        # Redirect based on user role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('user_role') == 'instructor':
            return redirect(url_for('user.profile'))
        else:  # student
            return redirect(url_for('dashboard'))
    
    try:
        cursor = connection.cursor()
        
        # Get user information
        cursor.execute(
            "SELECT * FROM users WHERE id = ?",
            (session['user_id'],)
        )
        user = cursor.fetchone()
        
        # Get user statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT ua.content_id) as content_viewed,
                COUNT(ua.id) as total_activities,
                SUM(ua.time_spent_minutes) as total_time_spent,
                AVG(cf.rating) as avg_rating_given
            FROM users u
            LEFT JOIN user_activities ua ON u.id = ua.user_id
            LEFT JOIN content_feedback cf ON u.id = cf.user_id
            WHERE u.id = ?
        """, (session['user_id'],)
        )
        stats = cursor.fetchone()
        
        # Get recent activities
        cursor.execute("""
            SELECT c.id as content_id, c.title, c.type, ua.activity_type, ua.created_at
            FROM user_activities ua
            JOIN content c ON ua.content_id = c.id
            WHERE ua.user_id = ?
            ORDER BY ua.created_at DESC
            LIMIT 10
        """, (session['user_id'],)
        )
        recent_activities = cursor.fetchall()
        
        connection.close()
        
        return render_template('user/profile.html', 
                             user=user, 
                             stats=stats, 
                             recent_activities=recent_activities)
    
    except Exception as err:
        flash(f'Error loading profile: {err}', 'error')
        # Redirect based on user role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('user_role') == 'instructor':
            return redirect(url_for('user.profile'))
        else:  # student
            return redirect(url_for('dashboard'))

@user_bp.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    """Edit user profile"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('user.profile'))
    
    try:
        if request.method == 'POST':
            full_name = request.form.get('full_name')
            bio = request.form.get('bio')
            interests = request.form.getlist('interests')
            
            # Update user profile
            interests_json = str(interests) if interests else None
            
            connection.execute("""
                UPDATE users 
                SET full_name = ?, bio = ?, interests = ?, updated_at = ?
                WHERE id = ?
            """, (full_name, bio, interests_json, datetime.now(), session['user_id']))
            
            connection.commit()
            
            # Update session
            session['full_name'] = full_name
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('user.profile'))
        
        # GET request - show edit form
        user = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (session['user_id'],)
        ).fetchone()
        
        connection.close()
        
        return render_template('user/edit_profile.html', user=user)
    
    except Exception as err:
        flash(f'Error updating profile: {err}', 'error')
        return redirect(url_for('user.profile'))

@user_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """User settings and preferences"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    connection = get_db_connection()
    if not connection:
        # Redirect based on user role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('user_role') == 'instructor':
            return redirect(url_for('user.profile'))
        else:  # student
            return redirect(url_for('dashboard'))
    
    try:
        if request.method == 'POST':
            # Check if this is a password change request
            if 'current_password' in request.form:
                # Handle password change
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                
                # Basic validation
                if not current_password:
                    flash('Please enter your current password', 'error')
                    return redirect(url_for('user.settings'))
                
                if not new_password or not confirm_password:
                    flash('Please enter both new password and confirmation', 'error')
                    return redirect(url_for('user.settings'))
                
                if new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                    return redirect(url_for('user.settings'))
                
                # Validate new password format (letters and numbers only)
                import re
                password_pattern = r'^[a-zA-Z0-9]+$'
                if not re.match(password_pattern, new_password):
                    flash('Password can only contain letters (a-z, A-Z) and numbers, no special symbols', 'error')
                    return redirect(url_for('user.settings'))
                
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long', 'error')
                    return redirect(url_for('user.settings'))
                
                # Verify current password
                user = connection.execute(
                    "SELECT password_hash FROM users WHERE id = ?",
                    (session['user_id'],)
                ).fetchone()
                
                from werkzeug.security import check_password_hash
                if not check_password_hash(user['password_hash'], current_password):
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('user.settings'))
                
                # Update password
                new_password_hash = generate_password_hash(new_password)
                connection.execute("""
                    UPDATE users 
                    SET password_hash = ?, updated_at = ?
                    WHERE id = ?
                """, (new_password_hash, datetime.now(), session['user_id']))
                
                connection.commit()
                flash('Password updated successfully!', 'success')
                return redirect(url_for('user.settings'))
            
            # Handle preferences update
            preferred_difficulty = request.form.get('preferred_difficulty', 'mixed')
            preferred_content_types = request.form.getlist('preferred_content_types')
            preferred_categories = request.form.getlist('preferred_categories')
            learning_goals = request.form.get('learning_goals')
            
            # Convert lists to string format for storage
            content_types_str = str(preferred_content_types) if preferred_content_types else None
            categories_str = str(preferred_categories) if preferred_categories else None
            
            # Log what we're saving
            print(f"DEBUG: Saving preferences for user {session['user_id']}")
            print(f"DEBUG: Content types: {preferred_content_types} -> {content_types_str}")
            print(f"DEBUG: Categories: {preferred_categories} -> {categories_str}")
            print(f"DEBUG: Difficulty: {preferred_difficulty}")
            
            # Check if user preferences record exists
            existing_prefs = connection.execute("""
                SELECT id FROM user_preferences WHERE user_id = ?
            """, (session['user_id'],)).fetchone()
            
            if existing_prefs:
                # Update existing preferences
                print(f"DEBUG: Updating existing preferences (id: {existing_prefs['id']})")
                connection.execute("""
                    UPDATE user_preferences 
                    SET preferred_difficulty = ?,
                        preferred_content_types = ?,
                        preferred_categories = ?,
                        learning_goals = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """, (
                    preferred_difficulty,
                    content_types_str,
                    categories_str,
                    learning_goals,
                    datetime.now(),
                    session['user_id']
                ))
            else:
                # Insert new preferences record
                print(f"DEBUG: Creating new preferences record")
                connection.execute("""
                    INSERT INTO user_preferences 
                    (user_id, preferred_difficulty, preferred_content_types, 
                     preferred_categories, learning_goals, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session['user_id'],
                    preferred_difficulty,
                    content_types_str,
                    categories_str,
                    learning_goals,
                    datetime.now(),
                    datetime.now()
                ))
            
            connection.commit()
            
            # Verify the save
            saved_prefs = connection.execute("""
                SELECT * FROM user_preferences WHERE user_id = ?
            """, (session['user_id'],)).fetchone()
            print(f"DEBUG: Saved preferences: {dict(saved_prefs) if saved_prefs else 'None'}")
            
            flash('Preferences updated successfully!', 'success')
            return redirect(url_for('user.settings'))
        
        # GET request - show settings form
        user_data = connection.execute("""
            SELECT u.*, p.* 
            FROM users u
            LEFT JOIN user_preferences p ON u.id = p.user_id
            WHERE u.id = ?
        """, (session['user_id'],)
        ).fetchone()
        
        # Get available categories
        categories = connection.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
        
        connection.close()
        
        return render_template('user/settings.html', 
                             user=user_data, 
                             categories=categories)
    
    except Exception as err:
        flash(f'Error loading settings: {err}', 'error')
        return redirect(url_for('dashboard'))

@user_bp.route('/progress')
def progress():
    """Display learning progress"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    connection = get_db_connection()
    if not connection:
        # Redirect based on user role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('user_role') == 'instructor':
            return redirect(url_for('user.profile'))
        else:  # student
            return redirect(url_for('dashboard'))
    
    try:
        # Get progress data by category
        progress_by_category = connection.execute("""
            SELECT 
                c.name as category_name,
                COUNT(DISTINCT ua.content_id) as content_completed,
                COUNT(DISTINCT cont.id) as total_content,
                (COUNT(DISTINCT ua.content_id) * 100.0 / COUNT(DISTINCT cont.id)) as completion_percentage
            FROM user_activities ua
            JOIN content cont ON ua.content_id = cont.id
            JOIN categories c ON cont.category_id = c.id
            WHERE ua.user_id = ? AND ua.activity_type = 'completed'
            GROUP BY c.id, c.name
            ORDER BY completion_percentage DESC
        """, (session['user_id'],)
        ).fetchall()
        
        # Get learning streak
        streak_data = connection.execute("""
            SELECT 
                COUNT(DISTINCT DATE(created_at)) as learning_days,
                MAX(created_at) as last_activity_date
            FROM user_activities
            WHERE user_id = ? AND created_at >= date('now', '-30 days')
        """, (session['user_id'],)
        ).fetchone()
        
        # Get time spent by day
        weekly_activity = connection.execute("""
            SELECT 
                DATE(created_at) as activity_date,
                SUM(time_spent_minutes) as total_minutes
            FROM user_activities
            WHERE user_id = ? AND created_at >= date('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY activity_date ASC
        """, (session['user_id'],)
        ).fetchall()
        
        connection.close()
        
        return render_template('user/progress.html',
                             progress_by_category=progress_by_category,
                             streak_data=streak_data,
                             weekly_activity=weekly_activity)
    
    except Exception as err:
        flash(f'Error loading progress: {err}', 'error')
        return redirect(url_for('dashboard'))