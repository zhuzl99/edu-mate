"""
Content Management Routes - Browse, Upload, View Content
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

def allowed_file(filename, content_type):
    """Check if file is allowed for content type"""
    ALLOWED_EXTENSIONS = {
        'video': {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'},
        'document': {'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'},
        'presentation': {'ppt', 'pptx', 'pdf', 'odp', 'key', 'doc', 'docx'},  # Allow Word docs for presentations
        'pdf': {'pdf'}
    }
    
    # Handle case where content_type is 'link' - files shouldn't be uploaded for links
    if content_type == 'link':
        return False
    
    if '.' not in filename:
        return False
    
    # Get the file extension (everything after the last dot)
    ext = filename.rsplit('.', 1)[1].lower().strip()
    
    # Debug logging before cleaning
    current_app.logger.debug(f'Original filename: {repr(filename)}')
    current_app.logger.debug(f'Original extension: {repr(ext)}')
    
    # Only remove spaces, keep valid extension characters (letters, numbers)
    ext = ext.strip()
    # Remove any whitespace within the extension (shouldn't happen, but just in case)
    ext = ''.join(c for c in ext if not c.isspace())
    
    # Debug logging after cleaning
    current_app.logger.debug(f'Cleaned extension: {repr(ext)}, content_type: {content_type}')
    
    if content_type in ALLOWED_EXTENSIONS:
        allowed_exts = ALLOWED_EXTENSIONS[content_type]
        current_app.logger.debug(f'Available extensions for {content_type}: {allowed_exts}')
        current_app.logger.debug(f'Extension {ext} in allowed set: {ext in allowed_exts}')
        current_app.logger.debug(f'Type of ext: {type(ext)}, len of ext: {len(ext)}')
        current_app.logger.debug(f'Direct comparison: ext == "docx": {ext == "docx"}')
        current_app.logger.debug(f'Contains check: "docx" in allowed_exts: {"docx" in allowed_exts}')
        return ext in allowed_exts
    
    # If content_type is not recognized, allow common file types
    COMMON_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx', 'mp4', 'avi', 'mov', 'wmv'}
    if ext in COMMON_EXTENSIONS:
        current_app.logger.debug(f'Content type {content_type} not recognized, but extension {ext} is common - allowing')
        return True
    
    current_app.logger.debug(f'Extension {ext} not allowed for content type {content_type}')
    return False

content_bp = Blueprint('content', __name__)

def get_db_connection():
    """Get database connection"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'edumate_local.db')
        
        # Check if database file exists and is writable
        if not os.path.exists(db_path):
            current_app.logger.error(f"Database file not found: {db_path}")
            flash('Database file not found. Please contact administrator.', 'error')
            return None
            
        if not os.access(db_path, os.R_OK | os.W_OK):
            current_app.logger.error(f"Database file permission denied: {db_path}")
            flash('Database permission denied. Please check file permissions.', 'error')
            return None
        
        # Connect with timeout and write-ahead logging
        connection = sqlite3.connect(db_path, timeout=10.0)
        connection.row_factory = sqlite3.Row  # This makes results behave like dictionaries
        
        # Enable WAL mode for better concurrency
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=NORMAL')
        connection.execute('PRAGMA busy_timeout=10000')
        
        return connection
        
    except sqlite3.Error as err:
        current_app.logger.error(f"SQLite error: {err}")
        flash(f'Database connection error: {err}', 'error')
        return None
    except Exception as err:
        current_app.logger.error(f"Unexpected database error: {err}")
        flash(f'Database error: {err}', 'error')
        return None

@content_bp.route('/browse')
def browse():
    """Browse and search content"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('dashboard'))
    
    try:
        cursor = connection.cursor()
        
        # Get search parameters
        search_query = request.args.get('q', '')
        category_id = request.args.get('category', '')
        difficulty = request.args.get('difficulty', '')
        content_type = request.args.get('type', '')
        page = int(request.args.get('page', 1))
        per_page = 12
        
        # Build query
        # Admins can see all content (including unpublished) for moderation
        if session.get('user_role') == 'admin':
            where_conditions = []  # Admins see all content
        else:
            where_conditions = ["c.is_published = 1"]  # Others only see published content
        params = []
        
        # Debug: log the query building process
        current_app.logger.debug(f"User role: {session.get('user_role')}")
        current_app.logger.debug(f"Where conditions: {where_conditions}")
        
        if search_query:
            where_conditions.append("(c.title LIKE ? OR c.description LIKE ?)")
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        if category_id:
            where_conditions.append("c.category_id = ?")
            params.append(category_id)
        
        if difficulty:
            where_conditions.append("c.difficulty_level = ?")
            params.append(difficulty)
        
        if content_type:
            where_conditions.append("c.type = ?")
            params.append(content_type)
        
        # Build WHERE clause
        if where_conditions:
            where_clause = " AND ".join(where_conditions)
        else:
            where_clause = "1=1"  # Always true condition
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM content c
            WHERE {where_clause}
        """
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Get paginated results with deduplication
        offset = (page - 1) * per_page
        
        query = f"""
            SELECT DISTINCT
                c.id,
                c.title,
                c.description,
                c.type,
                c.difficulty_level,
                c.file_url,
                c.external_link,
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
                u.full_name as uploader_name,
                (SELECT COUNT(*) FROM user_activities ua 
                 WHERE ua.content_id = c.id AND ua.user_id = ? 
                 LIMIT 1) as user_viewed
            FROM content c
            LEFT JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN users u ON c.uploaded_by = u.id
            WHERE {where_clause}
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT ? OFFSET ?
        """
        
        cursor.execute(query, [session['user_id']] + params + [per_page, offset])
        content_list = cursor.fetchall()
        
        # Get categories for filter
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('content/browse.html',
                             content_list=content_list,
                             categories=categories,
                             total_count=total_count,
                             total_pages=total_pages,
                             current_page=page,
                             search_params=request.args)
    
    except Exception as err:
        flash(f'Error loading content: {err}', 'error')
        return redirect(url_for('dashboard'))

@content_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload new content"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Check if user is instructor or admin
    if session.get('user_role') not in ['instructor', 'admin']:
        flash('Only instructors and admins can upload content', 'error')
        # Redirect based on user role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('user_role') == 'instructor':
            return redirect(url_for('user.profile'))
        else:  # student
            return redirect(url_for('index'))
    
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('dashboard'))
    
    try:
        cursor = connection.cursor()
        
        # Get categories for the form
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            content_type = request.form.get('type')
            difficulty = request.form.get('difficulty')
            category_id = request.form.get('category_id')
            tags = request.form.getlist('tags')
            external_link = request.form.get('external_link')
            source_type = request.form.get('source_type')
            publish_now = request.form.get('publish_now') is not None
            
            # Validation
            if not all([title, content_type, difficulty]):
                flash('Please fill in all required fields', 'error')
                return render_template('content/upload.html', categories=categories)
            
            file_url = external_link
            
            # Handle file upload (both sync and async)
            if source_type == 'file':
                # Check for async uploaded file first
                uploaded_file_url = request.form.get('uploaded_file_url')
                uploaded_filename = request.form.get('uploaded_filename')
                
                if uploaded_file_url and uploaded_filename:
                    # File was uploaded asynchronously
                    file_url = uploaded_file_url
                else:
                    # Traditional synchronous upload
                    if 'file' not in request.files:
                        flash('No file selected', 'error')
                        return render_template('content/upload.html', categories=categories)
                    
                    file = request.files['file']
                    if file.filename == '':
                        flash('No file selected', 'error')
                        return render_template('content/upload.html', categories=categories)
                    
                    if file and allowed_file(file.filename, content_type):
                        # Create uploads directory if it doesn't exist
                        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder)
                        
                        # Generate unique filename
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        unique_filename = timestamp + filename
                        
                        file_path = os.path.join(upload_folder, unique_filename)
                        file.save(file_path)
                        
                        # Create URL for the file
                        file_url = f'/uploads/{unique_filename}'
                    else:
                        flash('File type not allowed for this content type', 'error')
                        return render_template('content/upload.html', categories=categories)
            
            # Insert content
            tags_json = str(tags) if tags else None
            
            cursor.execute("""
                INSERT INTO content 
                (title, description, type, difficulty_level, external_link, file_url,
                 uploaded_by, category_id, tags, is_published, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, description, content_type, difficulty, external_link, file_url,
                session['user_id'], category_id or None, tags_json,
                1 if publish_now else 0, datetime.now(), datetime.now()  # SQLite uses 1 for boolean
            ))
            
            content_id = cursor.lastrowid
            connection.commit()
            
            # Log the upload
            cursor.execute("""
                INSERT INTO system_logs (user_id, action, resource_type, resource_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (session['user_id'], 'UPLOADED', 'content', content_id, datetime.now()))
            connection.commit()
            
            # Redirect based on publish status
            if publish_now:
                flash('Content published successfully!', 'success')
                return redirect(url_for('content.view', content_id=content_id))
            else:
                flash('Content saved as draft successfully!', 'success')
                return redirect(url_for('content.browse'))
        
        # GET request - show upload form
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('content/content_form.html', 
                            is_edit=False, 
                            categories=categories)
    
    except Exception as err:
        flash(f'Error uploading content: {err}', 'error')
        return redirect(url_for('dashboard'))

@content_bp.route('/upload-file', methods=['POST'])
def upload_file():
    """Handle async file upload with progress tracking"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if session.get('user_role') not in ['instructor', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get content_type from form or detect from file extension
    provided_content_type = request.form.get('content_type', '').strip()
    filename_lower = file.filename.lower()
    
    # Always validate if the provided content type matches the file extension
    # If not provided or doesn't match, auto-detect based on extension
    detected_type = None
    if filename_lower.endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv')):
        detected_type = 'video'
    elif filename_lower.endswith(('.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt')):
        detected_type = 'document'
    elif filename_lower.endswith(('.ppt', '.pptx', '.odp', '.key')):
        detected_type = 'presentation'
    else:
        detected_type = 'document'  # Default fallback
    
    current_app.logger.debug(f'File extension detection for: {filename_lower}')
    current_app.logger.debug(f'Detected content type: {detected_type}')
    current_app.logger.debug(f'Provided content type: {provided_content_type}')
    
    # Use provided type if it's valid and matches, otherwise use detected type
    if provided_content_type and provided_content_type != '':
        # Check if provided type matches detected type
        if provided_content_type == detected_type:
            content_type = provided_content_type
            current_app.logger.debug(f'Using provided content type: {content_type}')
        else:
            # Provided type doesn't match file extension, use detected type
            content_type = detected_type
            current_app.logger.debug(f'Provided type {provided_content_type} does not match detected type {detected_type}, using detected type')
    else:
        # No content type provided, use detected type
        content_type = detected_type
        current_app.logger.debug(f'No content type provided, using detected type: {content_type}')
    
    # Debug logging
    current_app.logger.debug(f'Upload request - filename: {file.filename}, content_type: {content_type}')
    current_app.logger.debug(f'File extension: {file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "none"}')
    current_app.logger.debug(f'allowed_file check result: {allowed_file(file.filename, content_type)}')
    
    if not allowed_file(file.filename, content_type):
        return jsonify({'error': f'File type not allowed for content type: {content_type}. File: {file.filename}'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Create URL for the file
        file_url = f'/uploads/{unique_filename}'
        
        # Return success response with file info
        return jsonify({
            'success': True,
            'file_url': file_url,
            'filename': unique_filename,
            'original_name': file.filename,
            'size': os.path.getsize(file_path)
        })
        
    except Exception as err:
        current_app.logger.error(f'File upload error: {err}')
        return jsonify({'error': 'Upload failed'}), 500

@content_bp.route('/<int:content_id>')
def view(content_id):
    """View specific content"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('content.browse'))
    
    try:
        cursor = connection.cursor()
        
        # Get content details - admins can see all content, others only see published content
        if session.get('user_role') == 'admin':
            cursor.execute("""
                SELECT 
                    c.*,
                    cat.name as category_name,
                    u.full_name as uploader_name,
                    u.username as uploader_username
                FROM content c
                LEFT JOIN categories cat ON c.category_id = cat.id
                LEFT JOIN users u ON c.uploaded_by = u.id
                WHERE c.id = ?
            """, (content_id,))
        else:
            cursor.execute("""
                SELECT 
                    c.*,
                    cat.name as category_name,
                    u.full_name as uploader_name,
                    u.username as uploader_username
                FROM content c
                LEFT JOIN categories cat ON c.category_id = cat.id
                LEFT JOIN users u ON c.uploaded_by = u.id
                WHERE c.id = ? AND c.is_published = 1
            """, (content_id,))
        
        content = cursor.fetchone()
        
        if not content:
            flash('Content not found', 'error')
            return redirect(url_for('content.browse'))
        
        # Increment view count
        cursor.execute("""
            UPDATE content 
            SET view_count = view_count + 1 
            WHERE id = ?
        """, (content_id,))
        
        # Log user activity - check if exists first
        cursor.execute("""
            SELECT id FROM user_activities 
            WHERE user_id = ? AND content_id = ? AND activity_type = 'viewed'
        """, (session['user_id'], content_id))
        
        existing_activity = cursor.fetchone()
        
        if existing_activity:
            # Update existing activity timestamp
            cursor.execute("""
                UPDATE user_activities 
                SET created_at = ?
                WHERE id = ?
            """, (datetime.now(), existing_activity['id']))
        else:
            # Insert new activity record
            cursor.execute("""
                INSERT INTO user_activities (user_id, content_id, activity_type, created_at)
                VALUES (?, ?, ?, ?)
            """, (session['user_id'], content_id, 'viewed', datetime.now()))
        
        # Get user's rating for this content
        cursor.execute("""
            SELECT cf.rating, cf.comment, cf.created_at,
                   u.full_name, u.username
            FROM content_feedback cf
            JOIN users u ON cf.user_id = u.id
            WHERE cf.content_id = ? AND cf.user_id = ?
        """, (content_id, session['user_id']))
        
        user_feedback = cursor.fetchone()
        
        # Check if user has bookmarked this content
        cursor.execute("""
            SELECT id FROM user_activities 
            WHERE user_id = ? AND content_id = ? AND activity_type = 'bookmarked'
        """, (session['user_id'], content_id))
        
        user_bookmark = cursor.fetchone()
        is_bookmarked = user_bookmark is not None
        
        # Get all feedback for this content with pagination support
        cursor.execute("""
            SELECT 
                cf.id, cf.rating, cf.comment, cf.created_at, cf.updated_at,
                COALESCE(u.full_name, u.username) as user_name,
                u.id as user_id
            FROM content_feedback cf
            JOIN users u ON cf.user_id = u.id
            WHERE cf.content_id = ?
            ORDER BY cf.created_at DESC
        """, (content_id,))
        
        feedback_list = cursor.fetchall()
        
        # Get feedback statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_count,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating = 5 THEN 1 END) as five_star,
                COUNT(CASE WHEN rating = 4 THEN 1 END) as four_star,
                COUNT(CASE WHEN rating = 3 THEN 1 END) as three_star,
                COUNT(CASE WHEN rating = 2 THEN 1 END) as two_star,
                COUNT(CASE WHEN rating = 1 THEN 1 END) as one_star
            FROM content_feedback 
            WHERE content_id = ?
        """, (content_id,))
        feedback_stats = cursor.fetchone()
        
        # Get feedback count
        feedback_count = feedback_stats['total_count'] if feedback_stats else 0
        
        # Get related content (same category) - SQLite uses RANDOM() instead of RAND()
        cursor.execute("""
            SELECT id, title, type, difficulty_level, average_rating, view_count
            FROM content 
            WHERE category_id = ? AND id != ? AND is_published = 1
            ORDER BY RANDOM()
            LIMIT 5
        """, (content['category_id'], content_id))
        
        related_content = cursor.fetchall()
        
        # Get uploader name
        cursor.execute("SELECT full_name FROM users WHERE id = ?", (content['uploaded_by'],))
        uploader = cursor.fetchone()
        uploader_name = uploader['full_name'] if uploader else 'Unknown'
        
        # Get user activity for this content
        user_activity = None
        if 'user_id' in session:
            cursor.execute("""
                SELECT activity_type, progress_percentage, time_spent_minutes
                FROM user_activities 
                WHERE user_id = ? AND content_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (session['user_id'], content_id))
            user_activity = cursor.fetchone()
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return render_template('content/view.html',
                             content=content,
                             user_feedback=user_feedback,
                             feedback_list=feedback_list,
                             feedback_count=feedback_count,
                             feedback_stats=feedback_stats,
                             related_content=related_content,
                             uploader_name=uploader_name,
                             user_activity=user_activity,
                             is_bookmarked=is_bookmarked)
    
    except Exception as err:
        flash(f'Error loading content: {err}', 'error')
        return redirect(url_for('content.browse'))

@content_bp.route('/<int:content_id>/rate', methods=['POST'])
def rate(content_id):
    """Rate content"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        if not rating or not (1 <= int(rating) <= 5):
            return jsonify({'error': 'Invalid rating'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Failed to connect to database'}), 500
        
        cursor = connection.cursor()
        
        # Check if feedback already exists
        cursor.execute("""
            SELECT id FROM content_feedback 
            WHERE content_id = ? AND user_id = ?
        """, (content_id, session['user_id']))
        
        existing = cursor.fetchone()
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing:
            # Update existing rating
            cursor.execute("""
                UPDATE content_feedback 
                SET rating = ?, comment = ?, updated_at = ?
                WHERE content_id = ? AND user_id = ?
            """, (int(rating), comment, current_time, content_id, session['user_id']))
        else:
            # Insert new rating
            cursor.execute("""
                INSERT INTO content_feedback (content_id, user_id, rating, comment, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (content_id, session['user_id'], int(rating), comment, current_time, current_time))
        
        # Update content's average rating
        cursor.execute("""
            UPDATE content 
            SET average_rating = (
                SELECT COALESCE(AVG(CAST(rating AS FLOAT)), 0) 
                FROM content_feedback 
                WHERE content_id = ?
            ),
            rating_count = (
                SELECT COUNT(*) 
                FROM content_feedback 
                WHERE content_id = ?
            )
            WHERE id = ?
        """, (content_id, content_id, content_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'message': 'Rating submitted successfully'})
    
    except ValueError as ve:
        current_app.logger.error(f"Rating value error: {str(ve)}")
        return jsonify({'error': f'Invalid rating value: {str(ve)}'}), 400
    except sqlite3.Error as se:
        current_app.logger.error(f"Database error in rating: {str(se)}")
        return jsonify({'error': f'Database error: {str(se)}'}), 500
    except Exception as err:
        current_app.logger.error(f"Rating submission error: {str(err)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': f'An error occurred: {str(err)}'}), 500

@content_bp.route('/<int:content_id>/activity', methods=['POST'])
def record_activity(content_id):
    """Record user activity for content"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        # Get JSON data
        if request.is_json:
            data = request.get_json()
            activity_type = data.get('activity_type', 'viewed')
        else:
            # Fallback to form data
            activity_type = request.form.get('activity_type', 'viewed')
        
        # Validate activity type
        valid_activities = ['viewed', 'completed', 'bookmarked']
        if activity_type not in valid_activities:
            return jsonify({'error': 'Invalid activity type'}), 400
        
        # Check if content exists - admins can access all content, others only published content
        if session.get('user_role') == 'admin':
            content = connection.execute(
                "SELECT id FROM content WHERE id = ?",
                (content_id,)
            ).fetchone()
        else:
            content = connection.execute(
                "SELECT id FROM content WHERE id = ? AND is_published = 1",
                (content_id,)
            ).fetchone()
        
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Record the activity - check if exists first, then update or insert
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id FROM user_activities 
            WHERE user_id = ? AND content_id = ? AND activity_type = ?
        """, (session['user_id'], content_id, activity_type))
        
        existing_activity = cursor.fetchone()
        
        if existing_activity:
            # Update existing activity timestamp
            cursor.execute("""
                UPDATE user_activities 
                SET created_at = ?
                WHERE id = ?
            """, (datetime.now(), existing_activity['id']))
        else:
            # Insert new activity record
            cursor.execute("""
                INSERT INTO user_activities (user_id, content_id, activity_type, created_at)
                VALUES (?, ?, ?, ?)
            """, (session['user_id'], content_id, activity_type, datetime.now()))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'message': f'Activity {activity_type} recorded'})
    
    except Exception as err:
        current_app.logger.error(f"Error recording activity: {err}")
        return jsonify({'error': str(err)}), 500

@content_bp.route('/<int:content_id>/bookmark', methods=['POST'])
def toggle_bookmark(content_id):
    """Toggle bookmark status for content"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Check if content exists and is accessible
        if session.get('user_role') == 'admin':
            content = connection.execute(
                "SELECT id FROM content WHERE id = ?",
                (content_id,)
            ).fetchone()
        else:
            content = connection.execute(
                "SELECT id FROM content WHERE id = ? AND is_published = 1",
                (content_id,)
            ).fetchone()
        
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Check if already bookmarked
        cursor.execute("""
            SELECT id FROM user_activities 
            WHERE user_id = ? AND content_id = ? AND activity_type = 'bookmarked'
        """, (session['user_id'], content_id))
        
        existing_bookmark = cursor.fetchone()
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing_bookmark:
            # Remove bookmark
            cursor.execute("""
                DELETE FROM user_activities 
                WHERE user_id = ? AND content_id = ? AND activity_type = 'bookmarked'
            """, (session['user_id'], content_id))
            
            action = 'UNBOOKMARKED'
            message = 'Bookmark removed successfully'
            is_bookmarked = False
        else:
            # Add bookmark (check for duplicates first, then insert)
            cursor.execute("""
                SELECT id FROM user_activities 
                WHERE user_id = ? AND content_id = ? AND activity_type = 'bookmarked'
            """, (session['user_id'], content_id))
            
            existing = cursor.fetchone()
            if not existing:
                cursor.execute("""
                    INSERT INTO user_activities 
                    (user_id, content_id, activity_type, created_at)
                    VALUES (?, ?, ?, ?)
                """, (session['user_id'], content_id, 'bookmarked', current_time))
            
            action = 'BOOKMARKED'
            message = 'Content bookmarked successfully'
            is_bookmarked = True
        
        # Log the action
        cursor.execute("""
            INSERT INTO system_logs (user_id, action, resource_type, resource_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session['user_id'], action, 'bookmark', content_id, datetime.now()))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': message,
            'is_bookmarked': is_bookmarked
        })
    
    except Exception as err:
        current_app.logger.error(f"Error toggling bookmark: {err}")
        return jsonify({'error': str(err)}), 500

@content_bp.route('/<int:content_id>/feedback/<int:feedback_id>/delete', methods=['POST'])
def delete_feedback(content_id, feedback_id):
    """Delete a comment/feedback"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Get feedback details to check permissions
        cursor.execute("""
            SELECT cf.user_id as feedback_user_id, cf.content_id,
                   c.uploaded_by as content_author_id
            FROM content_feedback cf
            JOIN content c ON cf.content_id = c.id
            WHERE cf.id = ? AND cf.content_id = ?
        """, (feedback_id, content_id))
        
        feedback = cursor.fetchone()
        
        if not feedback:
            return jsonify({'error': 'Feedback not found'}), 404
        
        # Check permissions: admin can delete any feedback, users can delete their own
        current_user_id = session['user_id']
        is_admin = session.get('user_role') == 'admin'
        is_feedback_owner = feedback['feedback_user_id'] == current_user_id
        
        if not (is_admin or is_feedback_owner):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Delete the feedback
        cursor.execute("""
            DELETE FROM content_feedback 
            WHERE id = ? AND content_id = ?
        """, (feedback_id, content_id))
        
        # Update content's average rating
        cursor.execute("""
            UPDATE content 
            SET average_rating = (
                SELECT COALESCE(AVG(CAST(rating AS FLOAT)), 0) 
                FROM content_feedback 
                WHERE content_id = ?
            ),
            rating_count = (
                SELECT COUNT(*) 
                FROM content_feedback 
                WHERE content_id = ?
            )
            WHERE id = ?
        """, (content_id, content_id, content_id))
        
        # Log the deletion
        action_type = 'ADMIN_DELETED_FEEDBACK' if is_admin else 'USER_DELETED_FEEDBACK'
        cursor.execute("""
            INSERT INTO system_logs (user_id, action, resource_type, resource_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (current_user_id, action_type, 'feedback', feedback_id, datetime.now()))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': 'Feedback deleted successfully'
        })
    
    except Exception as err:
        current_app.logger.error(f"Error deleting feedback: {err}")
        return jsonify({'error': str(err)}), 500

@content_bp.route('/<int:content_id>/edit', methods=['GET', 'POST'])
def edit(content_id):
    """Edit existing content"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if session.get('user_role') not in ['instructor', 'admin']:
        flash('You do not have permission to edit content', 'error')
        return redirect(url_for('content.view', content_id=content_id))
    
    connection = get_db_connection()
    if not connection:
        flash('Database error', 'error')
        return redirect(url_for('content.view', content_id=content_id))
    
    cursor = None
    try:
        cursor = connection.cursor()
        
        # Get content details
        cursor.execute("""
            SELECT c.*, cat.name as category_name
            FROM content c
            LEFT JOIN categories cat ON c.category_id = cat.id
            WHERE c.id = ?
        """, (content_id,))
        
        content = cursor.fetchone()
        
        if not content:
            flash('Content not found', 'error')
            return redirect(url_for('content.browse'))
        
        # Check if user has permission to edit this content
        if session.get('user_role') != 'admin' and content['uploaded_by'] != session['user_id']:
            flash('You do not have permission to edit this content', 'error')
            return redirect(url_for('content.view', content_id=content_id))
        
        # Get categories for the form
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        
        if request.method == 'POST':
            # Handle form submission
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            content_type = request.form.get('type')
            difficulty = request.form.get('difficulty')
            category_id = request.form.get('category_id')
            tags = request.form.get('tags')
            external_link = request.form.get('external_link')
            source_type = request.form.get('source_type')
            publish_now = request.form.get('publish_now') is not None
            
            # Validation
            if not title:
                flash('Title is required', 'error')
                return render_template('content/content_form.html', 
                                    is_edit=True,
                                    content=content, 
                                    categories=categories)
            
            # Handle file upload based on source type
            file_url = None
            if source_type == 'file':
                # Check for async uploaded file first
                uploaded_file_url = request.form.get('uploaded_file_url')
                uploaded_filename = request.form.get('uploaded_filename')
                
                if uploaded_file_url and uploaded_filename:
                    # File was uploaded asynchronously
                    file_url = uploaded_file_url
                else:
                    # Traditional synchronous upload (fallback)
                    if 'file' in request.files:
                        file = request.files['file']
                        if file.filename != '' and allowed_file(file.filename, content_type):
                            # Create uploads directory if it doesn't exist
                            upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
                            if not os.path.exists(upload_folder):
                                os.makedirs(upload_folder)
                            
                            filename = secure_filename(file.filename)
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                            unique_filename = timestamp + filename
                            
                            file_path = os.path.join(upload_folder, unique_filename)
                            file.save(file_path)
                            
                            file_url = f'/uploads/{unique_filename}'
            elif source_type == 'link':
                file_url = None  # Will use external_link
            elif source_type == 'current':
                # Keep current file - no changes to file_url/external_link
                file_url = content['file_url']
                external_link = content['external_link']
            
            # Update content
            cursor.execute("""
                UPDATE content 
                SET title = ?, description = ?, type = ?, difficulty_level = ?,
                    category_id = ?, external_link = ?, file_url = ?, tags = ?, 
                    is_published = ?, updated_at = ?
                WHERE id = ?
            """, (
                title, description, content_type, difficulty, 
                category_id or None, external_link, file_url, tags, 
                1 if publish_now else 0, datetime.now(), content_id
            ))
            
            connection.commit()
            
            # Redirect based on publish status
            if publish_now:
                flash('Content updated and published successfully!', 'success')
                return redirect(url_for('content.view', content_id=content_id))
            else:
                flash('Content updated and saved as draft successfully!', 'success')
                return redirect(url_for('content.browse'))
        
        # GET request - show edit form
        return render_template('content/content_form.html', 
                            is_edit=True, 
                            content=content, 
                            categories=categories)
        
    except Exception as err:
        flash(f'Error editing content: {err}', 'error')
        return redirect(url_for('content.view', content_id=content_id))
    finally:
        # Ensure cursor and connection are properly closed
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@content_bp.route('/<int:content_id>/delete', methods=['POST'])
def delete_content(content_id):
    """Delete content"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if session.get('user_role') not in ['admin']:
        flash('Only administrators can delete content', 'error')
        return redirect(url_for('content.view', content_id=content_id))
    
    connection = get_db_connection()
    if not connection:
        flash('Database error', 'error')
        return redirect(url_for('content.view', content_id=content_id))
    
    try:
        cursor = connection.cursor()
        
        # Get content details for logging
        cursor.execute("SELECT title, uploaded_by FROM content WHERE id = ?", (content_id,))
        content = cursor.fetchone()
        
        if not content:
            flash('Content not found', 'error')
            return redirect(url_for('content.browse'))
        
        # Check if user has permission to delete this content
        if session.get('user_role') != 'admin' and content['uploaded_by'] != session['user_id']:
            flash('You do not have permission to delete this content', 'error')
            return redirect(url_for('content.view', content_id=content_id))
        
        # Delete related feedback
        cursor.execute("DELETE FROM content_feedback WHERE content_id = ?", (content_id,))
        
        # Delete related user activities
        cursor.execute("DELETE FROM user_activities WHERE content_id = ?", (content_id,))
        
        # Delete the content
        cursor.execute("DELETE FROM content WHERE id = ?", (content_id,))
        
        connection.commit()
        
        # Log the deletion
        cursor.execute("""
            INSERT INTO system_logs (user_id, action, resource_type, resource_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session['user_id'], 'DELETED', 'content', content_id, datetime.now()))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        flash(f'Content "{content["title"]}" has been deleted successfully!', 'success')
        return redirect(url_for('content.browse'))
        
    except Exception as err:
        flash(f'Error deleting content: {err}', 'error')
        return redirect(url_for('content.view', content_id=content_id))

@content_bp.route('/api/search')
def api_search():
    """API endpoint for content search"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify({'results': []})
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Build query based on user role
        if session.get('user_role') == 'admin':
            # Admins can search all content
            cursor.execute("""
                SELECT id, title, description, type, category_id
                FROM content 
                WHERE (title LIKE ? OR description LIKE ?)
                ORDER BY title
                LIMIT 10
            """, (f'%{query}%', f'%{query}%'))
        else:
            # Others only see published content
            cursor.execute("""
                SELECT id, title, description, type, category_id
                FROM content 
                WHERE is_published = 1 
                AND (title LIKE ? OR description LIKE ?)
                ORDER BY title
                LIMIT 10
            """, (f'%{query}%', f'%{query}%'))
        
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return jsonify({'results': results})
    
    except Exception as err:
        return jsonify({'error': str(err)}), 500