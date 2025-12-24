"""
Recommendation Routes - Personalized Content Recommendations
"""
from flask import Blueprint, render_template, request, flash, session, jsonify
import sqlite3
from datetime import datetime, timedelta
import json

recommendation_bp = Blueprint('recommendation', __name__)

def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('edumate_local.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as err:
        flash(f'Database error: {err}', 'error')
        return None

def get_rule_based_recommendations(user_id, limit=10):
    """Generate rule-based recommendations for a user"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        
        # Get user preferences and activities
        cursor.execute("""
            SELECT 
                u.interests,
                up.preferred_difficulty,
                up.preferred_content_types,
                up.preferred_categories,
                up.learning_goals
            FROM users u
            LEFT JOIN user_preferences up ON u.id = up.user_id
            WHERE u.id = ?
        """, (user_id,))
        
        user_data = cursor.fetchone()
        
        # Get user's recently viewed content to avoid duplicates
        cursor.execute("""
            SELECT content_id 
            FROM user_activities 
            WHERE user_id = ? AND activity_type = 'viewed'
            AND created_at >= date('now', '-30 days')
        """, (user_id,))
        
        viewed_content = [row['content_id'] for row in cursor.fetchall()]
        
        # Build recommendation query
        where_conditions = ["c.is_published = TRUE"]
        params = []
        
        if viewed_content:
            where_conditions.append("c.id NOT IN (%s)" % ','.join(['?'] * len(viewed_content)))
            params.extend(viewed_content)
        
        # Add preference filters
        if user_data and user_data['preferred_difficulty'] and user_data['preferred_difficulty'] != 'mixed':
            where_conditions.append("c.difficulty_level = ?")
            params.append(user_data['preferred_difficulty'])
        
        # Get content matching user interests or categories
        if user_data and user_data['interests']:
            try:
                interests = json.loads(user_data['interests']) if isinstance(user_data['interests'], str) else user_data['interests']
                if interests:
                    interest_conditions = []
                    for interest in interests:
                        interest_conditions.append("c.title LIKE ? OR c.description LIKE ?")
                        params.extend([f'%{interest}%', f'%{interest}%'])
                    where_conditions.append(f"({' OR '.join(interest_conditions)})")
            except:
                pass
        
        # If user has preferred categories, prioritize them
        if user_data and user_data['preferred_categories']:
            try:
                preferred_cats = json.loads(user_data['preferred_categories']) if isinstance(user_data['preferred_categories'], str) else user_data['preferred_categories']
                if preferred_cats:
                    where_conditions.append("c.category_id IN (%s)" % ','.join(['?'] * len(preferred_cats)))
                    params.extend(preferred_cats)
            except:
                pass
        
        # Build final query
        base_query = """
            SELECT 
                c.*,
                cat.name as category_name,
                u.full_name as uploader_name,
                -- Calculate recommendation score
                (c.average_rating * 0.3 + 
                 c.download_count * 0.02 + 
                 c.view_count * 0.01) as score
            FROM content c
            LEFT JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN users u ON c.uploaded_by = u.id
            WHERE ?
            ORDER BY score DESC, c.created_at DESC
            LIMIT ?
        """
        
        final_query = base_query.replace('?', ' AND '.join(where_conditions))
        params.append(limit)
        
        cursor.execute(final_query, params)
        recommendations = cursor.fetchall()
        
        # Log recommendations
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO recommendations 
                (user_id, content_id, recommendation_type, score, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, rec['id'], 'rule_based', rec['score'],
                'Rule-based: matches preferences and interests', datetime.now()
            ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return recommendations
    
    except Exception as err:
        print(f"Recommendation error: {err}")
        return []

@recommendation_bp.route('/for-you')
def for_you():
    """Personalized recommendations page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    recommendations = get_rule_based_recommendations(session['user_id'])
    
    return render_template('recommendation/for_you.html', 
                         recommendations=recommendations)

@recommendation_bp.route('/trending')
def trending():
    """Trending content page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    connection = get_db_connection()
    if not connection:
        return render_template('recommendation/trending.html', trending_content=[])
    
    try:
        cursor = connection.cursor()
        
        # Get trending content (high engagement in last 7 days)
        cursor.execute("""
            SELECT 
                c.*,
                cat.name as category_name,
                u.full_name as uploader_name,
                COUNT(ua.id) as recent_activities,
                c.average_rating
            FROM content c
            LEFT JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN users u ON c.uploaded_by = u.id
            LEFT JOIN user_activities ua ON c.id = ua.content_id 
                AND ua.created_at >= date('now', '-7 days')
            WHERE c.is_published = TRUE
            GROUP BY c.id
            ORDER BY recent_activities DESC, c.average_rating DESC, c.created_at DESC
            LIMIT 20
        """)
        
        trending_content = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return render_template('recommendation/trending.html', 
                             trending_content=trending_content)
    
    except Exception as err:
        flash(f'Error loading trending content: {err}', 'error')
        return render_template('recommendation/trending.html', trending_content=[])

@recommendation_bp.route('/api/refresh')
def api_refresh():
    """API endpoint to refresh recommendations"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    recommendations = get_rule_based_recommendations(session['user_id'])
    
    # Format for API response
    formatted_recs = []
    for rec in recommendations:
        formatted_recs.append({
            'id': rec['id'],
            'title': rec['title'],
            'description': rec['description'][:100] + '...' if rec['description'] and len(rec['description']) > 100 else rec['description'],
            'type': rec['type'],
            'difficulty_level': rec['difficulty_level'],
            'category_name': rec['category_name'],
            'average_rating': float(rec['average_rating']) if rec['average_rating'] else 0,
            'view_count': rec['view_count'],
            'score': float(rec['score']) if rec['score'] else 0
        })
    
    return jsonify({'recommendations': formatted_recs})

@recommendation_bp.route('/api/click/<int:content_id>')
def api_click(content_id):
    """Track when user clicks on a recommendation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Update recommendation click
        cursor.execute("""
            UPDATE recommendations 
            SET was_clicked = TRUE 
            WHERE user_id = ? AND content_id = ? 
            AND created_at >= date('now', '-1 day')
        """, (session['user_id'], content_id))
        
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
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    
    except Exception as err:
        return jsonify({'error': str(err)}), 500

@recommendation_bp.route('/api/feedback/<int:content_id>')
def api_feedback(content_id):
    """Provide feedback on recommendation quality"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    helpful = request.json.get('helpful')
    if helpful is None:
        return jsonify({'error': 'Missing feedback parameter'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Update recommendation feedback
        cursor.execute("""
            UPDATE recommendations 
            SET was_helpful = ? 
            WHERE user_id = ? AND content_id = ? 
            AND created_at >= date('now', '-7 days')
        """, (helpful, session['user_id'], content_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    
    except Exception as err:
        return jsonify({'error': str(err)}), 500