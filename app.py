"""
EduMate - Personalized Learning Companion
Main Flask Application
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import logging
from datetime import datetime
from config import config

# Load configuration
config_name = 'development'  # Change this to 'production' for production
app = Flask(__name__)
app.config.from_object(config[config_name])

def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('edumate_local.db')
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    except Exception as err:
        flash(f'Database error: {err}', 'error')
        return None

# Setup logging for debugging
if app.config.get('DEBUG'):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
    )
    app.logger.debug('Debug mode enabled')

# Import route blueprints
from routes.auth import auth_bp
from routes.user import user_bp
from routes.content import content_bp
from routes.recommendation import recommendation_bp
from routes.admin import admin_bp

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
    """Main dashboard for students only"""
    print(f"\n{'='*80}")
    print(f"DASHBOARD ROUTE CALLED for user_id: {session.get('user_id')}")
    print(f"{'='*80}")
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Only allow students to access the dashboard
    if session.get('user_role') != 'student':
        flash('Access denied. Dashboard is only available for students.', 'error')
        # Redirect based on user role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('user_role') == 'instructor':
            return redirect(url_for('user.profile'))
        else:
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
            
            # 3. In Progress - content accessed but not completed
            in_progress_count = connection.execute("""
                SELECT COUNT(DISTINCT ua.content_id) as count 
                FROM user_activities ua 
                WHERE ua.user_id = ? AND ua.activity_type != 'completed'
            """, (session['user_id'],)).fetchone()['count']
            
            # 4. Achievements - count of positive ratings given or milestones
            achievements_count = connection.execute("""
                SELECT COUNT(*) as count 
                FROM content_feedback cf 
                WHERE cf.user_id = ? AND cf.rating >= 4
            """, (session['user_id'],)).fetchone()['count']
            
            user_stats = {
                'learning_progress': learning_progress,
                'completed_count': completed_count,
                'in_progress_count': in_progress_count,
                'achievements_count': achievements_count
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