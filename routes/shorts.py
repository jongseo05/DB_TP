from flask import Blueprint, request, jsonify
from db import get_db

shorts_bp = Blueprint("shorts", __name__)


# ==================================================
# 1) 쇼츠 상세 조회 + 댓글수 포함
# ==================================================
@shorts_bp.route("/shorts/<int:shorts_id>", methods=["GET"])
def shorts_detail(shorts_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    sql = """
        SELECT 
            s.shorts_id,
            s.title,
            s.video_url,
            s.thumbnail_url,
            s.duration_seconds,
            s.views,
            s.created_at,
            u.username,
            u.handle,
            u.profile_img,
            (SELECT COUNT(*) FROM Shorts_Comment WHERE shorts_id = s.shorts_id) AS comment_count,
            (SELECT COUNT(*) FROM Shorts_Like WHERE shorts_id = s.shorts_id AND type='like') AS like_count,
            (SELECT COUNT(*) FROM Shorts_Like WHERE shorts_id = s.shorts_id AND type='dislike') AS dislike_count
        FROM Shorts s
        JOIN Users u ON s.user_id = u.user_id
        WHERE s.shorts_id = %s;
    """

    cur.execute(sql, (shorts_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Shorts not found"}), 404

    return jsonify(row)


# ==================================================
# 2) 쇼츠 추천
# ==================================================
@shorts_bp.route("/shorts/recommend", methods=["GET"])
def shorts_recommend():
    user_id = request.args.get("user_id")

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    sql = """
        SELECT s.*,
            u.username,
            u.handle,
            u.profile_img,
            (SELECT COUNT(*) FROM Shorts_Like 
             WHERE shorts_id = s.shorts_id AND type='like') AS like_count,
            (SELECT COUNT(*) FROM Shorts_Like 
             WHERE shorts_id = s.shorts_id AND type='dislike') AS dislike_count,
            (SELECT COUNT(*) FROM Shorts_Comment 
             WHERE shorts_id = s.shorts_id) AS comment_count
        FROM Shorts s
        JOIN Users u ON s.user_id = u.user_id
        WHERE s.shorts_id NOT IN (
            SELECT shorts_id FROM Shorts_NotInterested WHERE user_id = %s
        )
          AND s.user_id NOT IN (
            SELECT blocked_user_id FROM Channel_Block WHERE user_id = %s
        )
        ORDER BY s.views DESC, s.created_at DESC
        LIMIT 50;
    """

    cur.execute(sql, (user_id, user_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(rows)


# ==================================================
# 3) 좋아요 / 싫어요
# ==================================================
@shorts_bp.route("/shorts/like", methods=["POST"])
def shorts_like():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")
    like_type = request.json.get("type")  # 'like' or 'dislike'

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        sql = """
            INSERT INTO Shorts_Like (shorts_id, user_id, type)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE type=%s;
        """

        cur.execute(sql, (shorts_id, user_id, like_type, like_type))
        conn.commit()
        
        # 좋아요/싫어요 통계 조회
        cur.execute("""
            SELECT 
                s.shorts_id,
                s.title,
                u.username,
                u.handle,
                COUNT(CASE WHEN sl.type = 'like' THEN 1 END) AS total_likes,
                COUNT(CASE WHEN sl.type = 'dislike' THEN 1 END) AS total_dislikes,
                %s AS user_action
            FROM Shorts s
            LEFT JOIN Shorts_Like sl ON s.shorts_id = sl.shorts_id
            JOIN Users u ON s.user_id = u.user_id
            WHERE s.shorts_id = %s
            GROUP BY s.shorts_id, s.title, u.username, u.handle
        """, (like_type, shorts_id))
        
        result = cur.fetchone()
        
        return jsonify({
            "message": "OK",
            "shorts_id": shorts_id,
            "user_id": user_id,
            "action": like_type,
            "stats": result
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()


# ==================================================
# 4) 관심 없음
# ==================================================
@shorts_bp.route("/shorts/not_interested", methods=["POST"])
def shorts_not_interested():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        sql = """
            INSERT INTO Shorts_NotInterested (shorts_id, user_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE created_at = NOW();
        """

        cur.execute(sql, (shorts_id, user_id))
        conn.commit()
        
        # 관심없음 표시된 쇼츠 정보 조회
        cur.execute("""
            SELECT 
                s.shorts_id,
                s.title,
                s.views,
                u.username AS creator_name,
                u.handle AS creator_handle,
                sni.created_at AS marked_at
            FROM Shorts s
            JOIN Users u ON s.user_id = u.user_id
            JOIN Shorts_NotInterested sni ON s.shorts_id = sni.shorts_id
            WHERE s.shorts_id = %s AND sni.user_id = %s
        """, (shorts_id, user_id))
        
        result = cur.fetchone()
        
        return jsonify({
            "message": "Marked as not interested",
            "shorts_id": shorts_id,
            "user_id": user_id,
            "shorts_info": result
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()


# ==================================================
# 5) 조회수 증가
# ==================================================
@shorts_bp.route("/shorts/<int:shorts_id>/view", methods=["PATCH"])
def shorts_view(shorts_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        sql = """
            UPDATE Shorts
            SET views = views + 1
            WHERE shorts_id = %s;
        """

        cur.execute(sql, (shorts_id,))
        conn.commit()
        
        # 업데이트된 쇼츠 정보 조회
        cur.execute("""
            SELECT 
                s.shorts_id,
                s.title,
                s.views,
                s.duration_seconds,
                u.username AS creator_name,
                u.handle AS creator_handle,
                u.profile_img AS creator_profile
            FROM Shorts s
            JOIN Users u ON s.user_id = u.user_id
            WHERE s.shorts_id = %s
        """, (shorts_id,))
        
        result = cur.fetchone()
        
        if result:
            return jsonify({
                "message": "View count increased",
                "shorts": result
            }), 200
        else:
            return jsonify({"error": "Shorts not found"}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()


# ==================================================
# 6) 리믹스된 쇼츠 목록 조회
# ==================================================
@shorts_bp.route("/shorts/<int:shorts_id>/remix", methods=["GET"])
def shorts_remix(shorts_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    sql = """
        SELECT s.*,
            u.username,
            u.handle,
            u.profile_img,
            (SELECT COUNT(*) FROM Shorts_Like 
             WHERE shorts_id = s.shorts_id AND type='like') AS like_count,
            (SELECT COUNT(*) FROM Shorts_Comment 
             WHERE shorts_id = s.shorts_id) AS comment_count
        FROM Shorts_Remix r
        JOIN Shorts s ON r.remix_shorts_id = s.shorts_id
        JOIN Users u ON s.user_id = u.user_id
        WHERE r.original_shorts_id = %s;
    """

    cur.execute(sql, (shorts_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(rows)


# ==================================================
# 7) 댓글 등록
# ==================================================
@shorts_bp.route("/shorts/comment", methods=["POST"])
def comment_write():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")
    content = request.json.get("content")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        sql = """
            INSERT INTO Shorts_Comment (shorts_id, user_id, content)
            VALUES (%s, %s, %s);
        """

        cur.execute(sql, (shorts_id, user_id, content))
        comment_id = cur.lastrowid
        conn.commit()
        
        # 생성된 댓글 정보 조회
        cur.execute("""
            SELECT c.*, u.username, u.handle, u.profile_img
            FROM Shorts_Comment c
            JOIN Users u ON c.user_id = u.user_id
            WHERE c.comment_id = %s;
        """, (comment_id,))
        new_comment = cur.fetchone()
        
        return jsonify({
            "message": "Comment Added",
            "comment": new_comment
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()


# ==================================================
# 8) 대댓글 등록
# ==================================================
@shorts_bp.route("/shorts/reply", methods=["POST"])
def reply_write():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")
    parent_id = request.json.get("parent_id")
    content = request.json.get("content")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        sql = """
            INSERT INTO Shorts_Comment (shorts_id, user_id, parent_comment_id, content)
            VALUES (%s, %s, %s, %s);
        """

        cur.execute(sql, (shorts_id, user_id, parent_id, content))
        reply_id = cur.lastrowid
        conn.commit()
        
        # 생성된 대댓글 정보 조회
        cur.execute("""
            SELECT c.*, u.username, u.handle, u.profile_img
            FROM Shorts_Comment c
            JOIN Users u ON c.user_id = u.user_id
            WHERE c.comment_id = %s;
        """, (reply_id,))
        new_reply = cur.fetchone()
        
        return jsonify({
            "message": "Reply Added",
            "reply": new_reply
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()


# ==================================================
# 9) 댓글 삭제
# ==================================================
@shorts_bp.route("/shorts/comment/<int:comment_id>", methods=["DELETE"])
def comment_delete(comment_id):

    conn = get_db()
    cur = conn.cursor()

    try:
        # 1. 대댓글 ID들을 먼저 조회
        cur.execute("SELECT comment_id FROM Shorts_Comment WHERE parent_comment_id = %s;", (comment_id,))
        reply_ids = [row[0] for row in cur.fetchall()]
        
        # 2. 대댓글들의 좋아요 삭제
        if reply_ids:
            placeholders = ','.join(['%s'] * len(reply_ids))
            cur.execute(f"DELETE FROM Comment_Like WHERE comment_id IN ({placeholders});", reply_ids)
        
        # 3. 대댓글 삭제
        cur.execute("DELETE FROM Shorts_Comment WHERE parent_comment_id = %s;", (comment_id,))
        
        # 4. 댓글의 좋아요 삭제
        cur.execute("DELETE FROM Comment_Like WHERE comment_id = %s;", (comment_id,))
        
        # 5. 마지막으로 댓글 삭제
        cur.execute("DELETE FROM Shorts_Comment WHERE comment_id = %s;", (comment_id,))
        affected_rows = cur.rowcount
        
        conn.commit()
        
        if affected_rows > 0:
            return jsonify({
                "message": "Deleted",
                "deleted_comment_id": comment_id
            })
        else:
            return jsonify({"error": "Comment not found"}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()


# ==================================================
# 10) 특정 쇼츠 댓글수 조회
# ==================================================
@shorts_bp.route("/shorts/<int:shorts_id>/comment_count", methods=["GET"])
def comment_count(shorts_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    sql = """
        SELECT COUNT(*) AS comment_count
        FROM Shorts_Comment
        WHERE shorts_id = %s;
    """

    cur.execute(sql, (shorts_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify(row)
