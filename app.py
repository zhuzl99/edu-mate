"""
EduMate - Personalized Learning Companion
Main Flask Application
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import logging
import os
from datetime import datetime
from config import config

# Load configuration
config_name = 'development'  # Change this to 'production' for production
app = Flask(__name__)
app.config.from_object(config[config_name])

def get_db_connection():
    """Get database connection"""
    try:
        db_path = app.config.get('DATABASE_PATH', 'edumate_local.db')
        
        # Check if database file exists and is writable
        if not os.path.exists(db_path):
            app.logger.error(f"Database file not found: {db_path}")
            flash('Database file not found. Please contact administrator.', 'error')
            return None
            
        if not os.access(db_path, os.R_OK | os.W_OK):
            app.logger.error(f"Database file permission denied: {db_path}")
            flash('Database permission denied. Please check file permissions.', 'error')
            return None
        
        # Connect with timeout and write-ahead logging
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA busy_timeout=10000')
        
        return conn
        
    except sqlite3.Error as err:
        app.logger.error(f"SQLite error: {err}")
        flash(f'Database connection error: {err}', 'error')
        return None
    except Exception as err:
        app.logger.error(f"Unexpected database error: {err}")
        flash(f'Database error: {err}', 'error')
        return None

# Setup logging for debugging
if app.config.get('DEBUG'):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
    )
    app.logger.debug('Debug mode enabled')

# Custom Jinja2 filters
@app.template_filter('format_datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime string or object"""
    if value is None:
        return 'Unknown'
    
    # If it's already a datetime object
    if isinstance(value, datetime):
        return value.strftime(format)
    
    # If it's a string, try to parse it
    if isinstance(value, str):
        try:
            # Try parsing SQLite datetime format
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            return dt.strftime(format)
        except ValueError:
            try:
                # Try alternative format
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
                return dt.strftime(format)
            except ValueError:
                # If parsing fails, return the original string
                return value
    
    return str(value)

@app.template_filter('split_tags')
def split_tags(value):
    """Split tags string into list"""
    if not value:
        return []
    
    # If it's already a list, return as is
    if isinstance(value, list):
        return value
    
    # Handle string representation of list
    if isinstance(value, str):
        if '[' in value and ']' in value:
            # Remove brackets and quotes, then split by comma
            clean_value = value.replace('[', '').replace(']', '').replace("'", '').replace('"', '')
            tags = [tag.strip() for tag in clean_value.split(',') if tag.strip()]
        else:
            # Handle simple comma-separated string
            tags = [tag.strip() for tag in value.split(',') if tag.strip()]
        return tags
    
    return []

# Import route blueprints
from routes.auth import auth_bp
from routes.user import user_bp
from routes.content import content_bp
from routes.recommendation import recommendation_bp
from routes.admin import admin_bp

# Add custom static route for uploads
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    from flask import send_from_directory
    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
    return send_from_directory(upload_folder, filename)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(content_bp, url_prefix='/content')
app.register_blueprint(recommendation_bp, url_prefix='/recommend')
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def index():
    """Home page - EduMate landing page - same for all users"""
    # Get user info for template if logged in
    connection = get_db_connection()
    if not connection:
        return render_template('index.html', user=None, featured_content=[])
    
    user = None
    featured_content = []
    
    try:
        if 'user_id' in session:
            # Get user information with preferences for personalized recommendations
            user = connection.execute("""
                SELECT u.*, p.preferred_difficulty, p.preferred_content_types, 
                       p.preferred_categories, p.learning_goals
                FROM users u
                LEFT JOIN user_preferences p ON u.id = p.user_id
                WHERE u.id = ?
            """, (session['user_id'],)).fetchone()
            
            # Build personalized featured content query based on user preferences
            where_conditions = ["c.is_published = 1"]
            query_params = []
            
            print(f"\n{'='*80}")
            print(f"HOME PAGE: Loading featured content for user {session['user_id']}")
            print(f"{'='*80}")
            
            # Filter by preferred content types if set
            if user and user['preferred_content_types']:
                preferred_types = user['preferred_content_types']
                types_list = []
                
                if isinstance(preferred_types, str):
                    if preferred_types.startswith('['):
                        import json
                        try:
                            types_list = json.loads(preferred_types.replace("'", '"'))
                            print(f"DEBUG: Parsed content types: {types_list}")
                        except Exception as e:
                            print(f"DEBUG: JSON parse failed: {e}")
                            types_list = [t.strip() for t in preferred_types.strip('[]').replace("'", "").split(',') if t.strip()]
                    else:
                        types_list = [t.strip() for t in preferred_types.split(',') if t.strip()]
                    
                    if types_list:
                        placeholders = ','.join(['?' for _ in types_list])
                        where_conditions.append(f"c.type IN ({placeholders})")
                        query_params.extend(types_list)
                        print(f"DEBUG: Added content type filter for home page")
            
            # Filter by preferred difficulty if set
            if user and user['preferred_difficulty'] and user['preferred_difficulty'] != 'mixed':
                where_conditions.append("c.difficulty_level = ?")
                query_params.append(user['preferred_difficulty'])
                print(f"DEBUG: Added difficulty filter: {user['preferred_difficulty']}")
            
            where_clause = " AND ".join(where_conditions)
            
            print(f"DEBUG: Home page WHERE clause: {where_clause}")
            print(f"DEBUG: Home page query params: {query_params}")
            
            # Get featured content based on user preferences
            # Use RANDOM() for variety, but prefer higher-rated content
            featured_content = connection.execute(f"""
                SELECT c.* FROM content c 
                WHERE {where_clause}
                ORDER BY RANDOM() 
                LIMIT 6
            """, query_params).fetchall()
            
            print(f"DEBUG: Found {len(featured_content)} featured items for home page")
            
            # If no content matches preferences AND no content type preference is set,
            # fall back to random recommendations
            if not featured_content and not (user and user['preferred_content_types']):
                print("DEBUG: No preferences set, using random content")
                featured_content = connection.execute("""
                    SELECT c.* FROM content c 
                    WHERE c.is_published = 1 
                    ORDER BY RANDOM() 
                    LIMIT 6
                """).fetchall()
        
        # Always render the index page (don't redirect)
        return render_template('index.html', user=user, featured_content=featured_content)
    
    except Exception as e:
        flash('Error loading home page', 'error')
        return render_template('index.html', user=None, featured_content=[])
    finally:
        if connection:
            connection.close()



@app.route('/dashboard')
def dashboard():
    """Main dashboard route - redirects to appropriate dashboard based on role"""
    print(f"\n{'='*80}")
    print(f"DASHBOARD ROUTE CALLED for user_id: {session.get('user_id')}, role: {session.get('user_role')}")
    print(f"{'='*80}")
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Redirect to appropriate dashboard based on user role
    if session.get('user_role') == 'admin':
        print("Redirecting admin to admin dashboard")
        return redirect(url_for('admin.dashboard'))
    elif session.get('user_role') == 'instructor':
        print("Redirecting instructor to profile")
        return redirect(url_for('user.profile'))
    elif session.get('user_role') == 'student':
        print("Showing student dashboard")
        # Continue to student dashboard logic
        pass
    else:
        print("Unknown role, redirecting to index")
        return redirect(url_for('index'))
    
    # Only students can access this dashboard
    if session.get('user_role') != 'student':
        flash('Access denied. This dashboard is only available for students.', 'error')
        return redirect(url_for('index'))
    
    connection = get_db_connection()
    if not connection:
        return render_template('dashboard.html', user=None, recent_activities=[])
    
    try:
        # Get user information with preferences
        user = connection.execute("""
            SELECT u.*, p.preferred_difficulty, p.preferred_content_types, 
                   p.preferred_categories, p.learning_goals
            FROM users u
            LEFT JOIN user_preferences p ON u.id = p.user_id
            WHERE u.id = ?
        """, (session['user_id'],)).fetchone()
        
        # Get recent activities based on user role
        if user and user['role'] == 'student':
            # Get student's recent learning activities
            recent_activities = connection.execute("""
                SELECT c.id as content_id, c.title, c.type, ua.activity_type, ua.created_at 
                FROM user_activities ua 
                JOIN content c ON ua.content_id = c.id 
                WHERE ua.user_id = ? 
                ORDER BY ua.created_at DESC 
                LIMIT 5
            """, (session['user_id'],)).fetchall()
        elif user and user['role'] == 'instructor':
            # Get instructor's uploaded content
            recent_activities = connection.execute("""
                SELECT id as content_id, title, type, created_at 
                FROM content 
                WHERE uploaded_by = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            """, (session['user_id'],)).fetchall()
        else:
            recent_activities = []
        
        # Get recommended content for students
        recommended_content = []
        bookmarked_content = []
        user_stats = {}
        if user and user['role'] == 'student':
            # Build recommendation query based on user preferences
            where_conditions = ["c.is_published = 1"]
            query_params = []
            
            # Debug: Print user preferences
            print(f"DEBUG Dashboard: User {session['user_id']} preferences:")
            print(f"  - preferred_content_types: {user['preferred_content_types']}")
            print(f"  - preferred_difficulty: {user['preferred_difficulty']}")
            print(f"  - preferred_categories: {user['preferred_categories']}")
            
            # Filter by preferred content types if set
            if user['preferred_content_types']:
                # Parse the preferred_content_types (stored as comma-separated string or JSON)
                preferred_types = user['preferred_content_types']
                types_list = []
                
                if isinstance(preferred_types, str):
                    # Could be stored as JSON array string like "['video','document']" or comma-separated
                    if preferred_types.startswith('['):
                        # JSON array format
                        import json
                        try:
                            types_list = json.loads(preferred_types.replace("'", '"'))
                        except Exception as e:
                            print(f"DEBUG: JSON parse failed: {e}, trying manual parse")
                            types_list = [t.strip() for t in preferred_types.strip('[]').replace("'", "").split(',') if t.strip()]
                    else:
                        # Comma-separated format
                        types_list = [t.strip() for t in preferred_types.split(',') if t.strip()]
                    
                    print(f"DEBUG: Parsed content types: {types_list}")
                    
                    if types_list:
                        placeholders = ','.join(['?' for _ in types_list])
                        where_conditions.append(f"c.type IN ({placeholders})")
                        query_params.extend(types_list)
                        print(f"DEBUG: Added content type filter: c.type IN ({placeholders})")
                        print(f"DEBUG: Query params: {query_params}")
            
            # Filter by preferred difficulty if set
            if user['preferred_difficulty'] and user['preferred_difficulty'] != 'mixed':
                where_conditions.append("c.difficulty_level = ?")
                query_params.append(user['preferred_difficulty'])
            
            # Filter by preferred categories if set
            if user['preferred_categories']:
                preferred_cats = user['preferred_categories']
                if isinstance(preferred_cats, str):
                    if preferred_cats.startswith('['):
                        import json
                        try:
                            cats_list = json.loads(preferred_cats.replace("'", '"'))
                        except:
                            cats_list = [c.strip() for c in preferred_cats.strip('[]').replace("'", "").split(',') if c.strip()]
                    else:
                        cats_list = [c.strip() for c in preferred_cats.split(',') if c.strip()]
                    
                    if cats_list:
                        placeholders = ','.join(['?' for _ in cats_list])
                        where_conditions.append(f"cat.name IN ({placeholders})")
                        query_params.extend(cats_list)
            
            where_clause = " AND ".join(where_conditions)
            
            print(f"DEBUG: Final WHERE clause: {where_clause}")
            print(f"DEBUG: Final query params: {query_params}")
            
            recommended_content = connection.execute(f"""
                SELECT c.*, cat.name as category_name
                FROM content c 
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE {where_clause}
                ORDER BY c.average_rating DESC, c.view_count DESC 
                LIMIT 3
            """, query_params).fetchall()
            
            print(f"DEBUG: Found {len(recommended_content)} recommended items")
            for item in recommended_content:
                print(f"  - {item['title']} (type: {item['type']})")
            
            # If no content matches preferences AND no content type preference is set, 
            # fall back to general recommendations
            if not recommended_content and not user['preferred_content_types']:
                print("DEBUG: No content found and no preferences set, using fallback")
                recommended_content = connection.execute("""
                    SELECT c.*, cat.name as category_name
                    FROM content c 
                    LEFT JOIN categories cat ON c.category_id = cat.id
                    WHERE c.is_published = 1 
                    ORDER BY c.average_rating DESC, c.view_count DESC 
                    LIMIT 3
                """).fetchall()
            
            # Calculate user statistics
            # 1. Learning Progress - percentage of completed content
            total_content = connection.execute("""
                SELECT COUNT(*) as count FROM content WHERE is_published = 1
            """).fetchone()['count']
            
            completed_content = connection.execute("""
                SELECT COUNT(DISTINCT ua.content_id) as count 
                FROM user_activities ua 
                WHERE ua.user_id = ? AND ua.activity_type = 'completed'
            """, (session['user_id'],)).fetchone()['count']
            
            learning_progress = round((completed_content / total_content * 100), 1) if total_content > 0 else 0
            
            # 2. Completed - number of completed activities
            completed_count = connection.execute("""
                SELECT COUNT(*) as count 
                FROM user_activities ua 
                WHERE ua.user_id = ? AND ua.activity_type = 'completed'
            """, (session['user_id'],)).fetchone()['count']
            
            # 3. In Progress - content currently being studied
            in_progress_count = connection.execute("""
                SELECT COUNT(DISTINCT ua.content_id) as count 
                FROM user_activities ua 
                WHERE ua.user_id = ? AND ua.activity_type = 'in_progress'
            """, (session['user_id'],)).fetchone()['count']
            
            user_stats = {
                'learning_progress': learning_progress,
                'completed_count': completed_count,
                'in_progress_count': in_progress_count
            }
            
            # Get bookmarked content
            bookmarked_content = connection.execute("""
                SELECT DISTINCT c.id as content_id, c.title, c.type, c.description, 
                       c.difficulty_level, c.average_rating, c.view_count,
                       cat.name as category_name, ua.created_at as bookmarked_at
                FROM user_activities ua
                JOIN content c ON ua.content_id = c.id
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE ua.user_id = ? AND ua.activity_type = 'bookmarked' AND c.is_published = 1
                ORDER BY ua.created_at DESC
                LIMIT 6
            """, (session['user_id'],)).fetchall()
        
        return render_template('dashboard.html', 
                             user=user, 
                             recent_activities=recent_activities,
                             recommended_content=recommended_content,
                             user_stats=user_stats,
                             bookmarked_content=bookmarked_content)
    
    except Exception as e:
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', 
                             user=None, 
                             recent_activities=[], 
                             recommended_content=[],
                             user_stats={},
                             bookmarked_content=[])
    finally:
        if connection:
            connection.close()

@app.errorhandler(413)
def too_large(error):
    flash('File too large. Maximum file size is 100MB.', 'error')
    return redirect(url_for('content.upload'))

@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Internal Server Error: {error}')
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(
        debug=app.config.get('DEBUG', True),
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000)
    )