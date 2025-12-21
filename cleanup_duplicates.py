"""
清理数据库中的重复数据
"""
import sqlite3
from datetime import datetime

def cleanup_database():
    """清理数据库中的重复记录"""
    
    conn = sqlite3.connect('edumate_local.db')
    cursor = conn.cursor()
    
    print("=" * 80)
    print("开始清理数据库重复数据...")
    print("=" * 80)
    
    # 1. 清理 content_feedback 表中的重复数据
    print("\n1. 检查 content_feedback 表...")
    cursor.execute("""
        SELECT content_id, user_id, COUNT(*) as count
        FROM content_feedback
        GROUP BY content_id, user_id
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"   发现 {len(duplicates)} 组重复的反馈记录")
        for content_id, user_id, count in duplicates:
            print(f"   - Content {content_id}, User {user_id}: {count} 条重复")
            
            # 保留最新的记录，删除旧的
            cursor.execute("""
                DELETE FROM content_feedback
                WHERE id NOT IN (
                    SELECT id FROM content_feedback
                    WHERE content_id = ? AND user_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ) AND content_id = ? AND user_id = ?
            """, (content_id, user_id, content_id, user_id))
        
        deleted_count = cursor.rowcount
        print(f"   ✓ 已删除 {deleted_count} 条重复记录")
    else:
        print("   ✓ 没有发现重复记录")
    
    # 2. 清理 user_activities 表中的重复数据
    print("\n2. 检查 user_activities 表...")
    cursor.execute("""
        SELECT user_id, content_id, activity_type, COUNT(*) as count
        FROM user_activities
        GROUP BY user_id, content_id, activity_type
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"   发现 {len(duplicates)} 组重复的活动记录")
        for user_id, content_id, activity_type, count in duplicates:
            print(f"   - User {user_id}, Content {content_id}, Type {activity_type}: {count} 条重复")
            
            # 保留最新的记录，删除旧的
            cursor.execute("""
                DELETE FROM user_activities
                WHERE id NOT IN (
                    SELECT id FROM user_activities
                    WHERE user_id = ? AND content_id = ? AND activity_type = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ) AND user_id = ? AND content_id = ? AND activity_type = ?
            """, (user_id, content_id, activity_type, user_id, content_id, activity_type))
        
        deleted_count = cursor.rowcount
        print(f"   ✓ 已删除 {deleted_count} 条重复记录")
    else:
        print("   ✓ 没有发现重复记录")
    
    # 3. 清理 content 表中的重复标题
    print("\n3. 检查 content 表...")
    cursor.execute("""
        SELECT title, COUNT(*) as count
        FROM content
        GROUP BY title
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"   发现 {len(duplicates)} 组重复标题的内容")
        for title, count in duplicates:
            print(f"   - 标题 '{title}': {count} 条记录")
            
            # 显示详细信息，但不自动删除（需要人工确认）
            cursor.execute("""
                SELECT id, title, uploaded_by, created_at
                FROM content
                WHERE title = ?
                ORDER BY created_at DESC
            """, (title,))
            items = cursor.fetchall()
            for item in items:
                print(f"     ID: {item[0]}, Uploader: {item[1]}, Created: {item[3]}")
        
        print("   ⚠ 请手动检查并删除重复的内容")
    else:
        print("   ✓ 没有发现重复标题")
    
    # 4. 更新 content 表的统计数据
    print("\n4. 更新内容统计数据...")
    cursor.execute("""
        UPDATE content
        SET average_rating = (
            SELECT COALESCE(AVG(CAST(rating AS FLOAT)), 0)
            FROM content_feedback
            WHERE content_feedback.content_id = content.id
        ),
        rating_count = (
            SELECT COUNT(*)
            FROM content_feedback
            WHERE content_feedback.content_id = content.id
        )
    """)
    updated_count = cursor.rowcount
    print(f"   ✓ 已更新 {updated_count} 条内容的统计数据")
    
    # 提交更改
    conn.commit()
    
    # 5. 显示数据库统计
    print("\n" + "=" * 80)
    print("数据库统计信息:")
    print("=" * 80)
    
    cursor.execute("SELECT COUNT(*) FROM users")
    print(f"总用户数: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM content WHERE is_published = 1")
    published = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM content WHERE is_published = 0")
    unpublished = cursor.fetchone()[0]
    print(f"总内容数: {published + unpublished} (已发布: {published}, 未发布: {unpublished})")
    
    cursor.execute("SELECT COUNT(*) FROM content_feedback")
    print(f"总反馈数: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM user_activities")
    print(f"总活动数: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM categories")
    print(f"总分类数: {cursor.fetchone()[0]}")
    
    print("\n✅ 数据库清理完成！")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    cleanup_database()
