from flask import Blueprint, request, jsonify
from db import get_db

shorts_bp = Blueprint("shorts", __name__)


# ----------------------------
# 1) Shorts 리스트 (GET)
#    GET /shorts/list?user_id=3&offset=0&limit=20
# ----------------------------
@shorts_bp.route("/shorts/list", methods=["GET"])
def shorts_list():
    try:
        user_id = request.args.get("user_id", type=int)  # optional but recommended
        offset = request.args.get("offset", default=0, type=int)
        limit = request.args.get("limit", default=20, type=int)

        conn = get_db()
        cur = conn.cursor(dictionary=True)

        sql = """
        SELECT 
            v.video_id AS shorts_id,
            v.user_id AS channel_id,
            u.username AS channel_name,
            v.title,
            v.video_url,
            v.thumbnail_url,
            v.duration,
            v.view_count,
            v.like_count,
            v.comment_count,
            v.upload_date
        FROM Videos v
        JOIN Users u ON v.user_id = u.user_id
        WHERE v.type_id = 2
          AND (%s IS NULL OR v.user_id NOT IN (
                SELECT blocked_user_id FROM BlockList WHERE user_id = %s
          ))
        ORDER BY v.view_count DESC, v.upload_date DESC
        LIMIT %s OFFSET %s;
        """
        # pass user_id twice for the subquery; if user_id is None, the WHERE clause becomes true due to (%s IS NULL OR ...)
        cur.execute(sql, (user_id, user_id, limit, offset))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 2) Shorts 상세 (GET)
#    GET /shorts/detail/<shorts_id>?user_id=3
# ----------------------------
@shorts_bp.route("/shorts/detail/<int:shorts_id>", methods=["GET"])
def shorts_detail(shorts_id):
    user_id = request.args.get("user_id", type=int)  # optional
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
    SELECT
        v.*,
        u.username AS channel_name,
        IFNULL(l.like_count, 0) AS like_count,
        IF(vl.user_id IS NULL, 0, 1) AS is_liked
    FROM Videos v
    JOIN Users u ON u.user_id = v.user_id
    LEFT JOIN (
        SELECT video_id, COUNT(*) AS like_count
        FROM VideoLikes
        WHERE is_dislike = 0
        GROUP BY video_id
    ) l ON l.video_id = v.video_id
    LEFT JOIN VideoLikes vl ON vl.video_id = v.video_id AND vl.user_id = %s
    WHERE v.video_id = %s AND v.type_id = 2
    LIMIT 1;
    """
    try:
        cur.execute(sql, (user_id, shorts_id))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Shorts not found"}), 404
        return jsonify(row)
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 3) Shorts Mix 추천 (GET)
#    GET /shorts/mix?shorts_id=1&user_id=3
# ----------------------------
@shorts_bp.route("/shorts/mix", methods=["GET"])
def shorts_mix():
    shorts_id = request.args.get("shorts_id", type=int)
    user_id = request.args.get("user_id", type=int)  # optional
    if shorts_id is None:
        return jsonify({"error": "shorts_id required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
    SELECT
        v.video_id AS shorts_id,
        v.user_id AS channel_id,
        u.username AS channel_name,
        v.title,
        v.video_url,
        v.thumbnail_url,
        v.duration,
        v.view_count
    FROM Videos v
    JOIN Users u ON u.user_id = v.user_id
    WHERE v.type_id = 2
      AND v.video_id != %s
      AND (%s IS NULL OR v.user_id NOT IN (SELECT blocked_user_id FROM BlockList WHERE user_id = %s))
    ORDER BY RAND()
    LIMIT 20;
    """
    try:
        cur.execute(sql, (shorts_id, user_id, user_id))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 4) 댓글 리스트 조회 (GET)
#    GET /shorts/comments/<shorts_id>
# ----------------------------
@shorts_bp.route("/shorts/comments/<int:shorts_id>", methods=["GET"])
def get_comments(shorts_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
    SELECT
        c.comment_id,
        c.user_id,
        u.username,
        c.content,
        c.parent_id,
        c.created_at
    FROM Comments c
    JOIN Users u ON u.user_id = c.user_id
    WHERE c.video_id = %s
    ORDER BY c.created_at ASC;
    """
    try:
        cur.execute(sql, (shorts_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 5) 댓글 작성 (POST)
#    POST /shorts/comments
#    body: { "shorts_id": 1, "user_id": 3, "content": "..." }
# ----------------------------
@shorts_bp.route("/shorts/comments", methods=["POST"])
def comment_write():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")
    content = request.json.get("content")
    parent_id = request.json.get("parent_id")  # optional for reply

    if None in (shorts_id, user_id, content):
        return jsonify({"error": "shorts_id, user_id and content required"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        if parent_id:
            sql = """
            INSERT INTO Comments (video_id, user_id, parent_id, content)
            VALUES (%s, %s, %s, %s);
            """
            cur.execute(sql, (shorts_id, user_id, parent_id, content))
        else:
            sql = """
            INSERT INTO Comments (video_id, user_id, content)
            VALUES (%s, %s, %s);
            """
            cur.execute(sql, (shorts_id, user_id, content))
        conn.commit()

        # Recalculate and update Videos.comment_count (cache consistency)
        cur.execute("""
            UPDATE Videos v
            SET v.comment_count = (
                SELECT COUNT(*) FROM Comments c WHERE c.video_id = v.video_id
            )
            WHERE v.video_id = %s;
        """, (shorts_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "Comment Added"}), 201


# ----------------------------
# 6) 댓글 삭제 (DELETE)
#    DELETE /shorts/comments/<comment_id>?user_id=3
# ----------------------------
@shorts_bp.route("/shorts/comments/<int:comment_id>", methods=["DELETE"])
def comment_delete(comment_id):
    user_id = request.args.get("user_id", type=int)
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        # 확인: 댓글 소유자인지 가져오기
        cur.execute("SELECT video_id, user_id FROM Comments WHERE comment_id = %s;", (comment_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Comment not found"}), 404

        if row["user_id"] != user_id:
            cur.close()
            conn.close()
            return jsonify({"error": "Unauthorized"}), 403

        video_id = row["video_id"]

        # 삭제
        cur.execute("DELETE FROM Comments WHERE comment_id = %s;", (comment_id,))
        conn.commit()

        # 갱신: 댓글 카운트
        cur.execute("""
            UPDATE Videos v
            SET v.comment_count = (
                SELECT COUNT(*) FROM Comments c WHERE c.video_id = v.video_id
            )
            WHERE v.video_id = %s;
        """, (video_id,))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "Deleted"})
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 7) 좋아요 / 싫어요 조회 (GET)
#    GET /shorts/likes/<shorts_id>?user_id=3
# ----------------------------
@shorts_bp.route("/shorts/likes/<int:shorts_id>", methods=["GET"])
def likes_info(shorts_id):
    user_id = request.args.get("user_id", type=int)
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        # like_count (is_dislike = 0)
        cur.execute("SELECT COUNT(*) AS like_count FROM VideoLikes WHERE video_id = %s AND is_dislike = 0;", (shorts_id,))
        like_row = cur.fetchone()
        like_count = like_row["like_count"] if like_row else 0

        # dislike_count (optional)
        cur.execute("SELECT COUNT(*) AS dislike_count FROM VideoLikes WHERE video_id = %s AND is_dislike = 1;", (shorts_id,))
        dis_row = cur.fetchone()
        dislike_count = dis_row["dislike_count"] if dis_row else 0

        is_liked = 0
        is_disliked = 0
        if user_id:
            cur.execute("SELECT is_dislike FROM VideoLikes WHERE video_id = %s AND user_id = %s;", (shorts_id, user_id))
            r = cur.fetchone()
            if r:
                if r.get("is_dislike") in (1, True):
                    is_disliked = 1
                else:
                    is_liked = 1

        cur.close()
        conn.close()
        return jsonify({
            "like_count": like_count,
            "dislike_count": dislike_count,
            "is_liked": is_liked,
            "is_disliked": is_disliked
        })
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 8) 좋아요/싫어요 추가 (POST)
#    POST /shorts/likes/<shorts_id>
#    body: { "user_id": 3, "type": "like" } # type: "like" or "dislike"
# ----------------------------
@shorts_bp.route("/shorts/likes/<int:shorts_id>", methods=["POST"])
def like_action(shorts_id):
    user_id = request.json.get("user_id")
    like_type = request.json.get("type", "like")  # default to like

    if None in (shorts_id, user_id, like_type):
        return jsonify({"error": "shorts_id, user_id and type required"}), 400

    is_dislike = 1 if like_type == "dislike" else 0

    conn = get_db()
    cur = conn.cursor()

    try:
        # upsert pattern: if exists update, else insert
        sql = """
        INSERT INTO VideoLikes (video_id, user_id, is_dislike, created_at)
        VALUES (%s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE is_dislike = VALUES(is_dislike), created_at = NOW();
        """
        cur.execute(sql, (shorts_id, user_id, is_dislike))
        conn.commit()

        # Recalculate and update Videos.like_count (only non-dislike)
        cur.execute("""
            UPDATE Videos v
            SET v.like_count = (
                SELECT COUNT(*) FROM VideoLikes vl WHERE vl.video_id = v.video_id AND vl.is_dislike = 0
            )
            WHERE v.video_id = %s;
        """, (shorts_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "OK"})


# ----------------------------
# 9) 좋아요/싫어요 취소 (DELETE)
#    DELETE /shorts/likes/<shorts_id>?user_id=3
# ----------------------------
@shorts_bp.route("/shorts/likes/<int:shorts_id>", methods=["DELETE"])
def unlike_action(shorts_id):
    user_id = request.args.get("user_id", type=int)
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM VideoLikes WHERE video_id = %s AND user_id = %s;", (shorts_id, user_id))
        conn.commit()

        # Recalculate and update Videos.like_count
        cur.execute("""
            UPDATE Videos v
            SET v.like_count = (
                SELECT COUNT(*) FROM VideoLikes vl WHERE vl.video_id = v.video_id AND vl.is_dislike = 0
            )
            WHERE v.video_id = %s;
        """, (shorts_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "Deleted"})
