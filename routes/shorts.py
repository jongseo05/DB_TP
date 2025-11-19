from flask import Blueprint, request, jsonify
from db import get_db

shorts_bp = Blueprint("shorts", __name__)


@shorts_bp.route("/detail", methods=["POST"])
def shorts_detail():
    shorts_id = request.json.get("shorts_id")
    if shorts_id is None:
        return jsonify({"error": "shorts_id required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
    SELECT 
        s.*,
        (SELECT COUNT(*) FROM Shorts_Comment WHERE shorts_id = s.shorts_id) AS comment_count
    FROM Shorts s
    WHERE s.shorts_id = %s
    LIMIT 1;
    """

    cur.execute(sql, (shorts_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Shorts not found"}), 404

    return jsonify(row)


@shorts_bp.route("/recommend", methods=["POST"])
def shorts_recommend():
    user_id = request.json.get("user_id")
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
    SELECT s.*,
           (SELECT COUNT(*) FROM Shorts_Like WHERE shorts_id = s.shorts_id AND `type`='like') AS like_count,
           (SELECT COUNT(*) FROM Shorts_Comment WHERE shorts_id = s.shorts_id) AS comment_count
    FROM Shorts s
    WHERE s.shorts_id NOT IN (SELECT shorts_id FROM Shorts_NotInterested WHERE user_id = %s)
      AND s.user_id NOT IN (SELECT blocked_user_id FROM Channel_Block WHERE user_id = %s)
    ORDER BY s.views DESC, s.created_at DESC
    LIMIT 50;
    """

    cur.execute(sql, (user_id, user_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(rows)


@shorts_bp.route("/like", methods=["POST"])
def shorts_like():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")
    like_type = request.json.get("type")  # 'like' or 'dislike'

    if None in (shorts_id, user_id, like_type):
        return jsonify({"error": "shorts_id, user_id and type required"}), 400

    conn = get_db()
    cur = conn.cursor()

    sql = """
    INSERT INTO Shorts_Like (shorts_id, user_id, `type`)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE `type` = %s;
    """

    try:
        cur.execute(sql, (shorts_id, user_id, like_type, like_type))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "OK"})


@shorts_bp.route("/not_interested", methods=["POST"])
def shorts_not_interested():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")

    if None in (shorts_id, user_id):
        return jsonify({"error": "shorts_id and user_id required"}), 400

    conn = get_db()
    cur = conn.cursor()

    sql = """
    INSERT INTO Shorts_NotInterested (shorts_id, user_id)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE created_at = NOW();
    """

    try:
        cur.execute(sql, (shorts_id, user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "OK"})


@shorts_bp.route("/view", methods=["POST"])
def shorts_view():
    shorts_id = request.json.get("shorts_id")
    if shorts_id is None:
        return jsonify({"error": "shorts_id required"}), 400

    conn = get_db()
    cur = conn.cursor()

    sql = """
    UPDATE Shorts
    SET views = views + 1
    WHERE shorts_id = %s;
    """

    try:
        cur.execute(sql, (shorts_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "OK"})


@shorts_bp.route("/remix", methods=["POST"])
def shorts_remix():
    shorts_id = request.json.get("shorts_id")
    if shorts_id is None:
        return jsonify({"error": "shorts_id required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
    SELECT s.*
    FROM Shorts_Remix r
    JOIN Shorts s ON r.remix_shorts_id = s.shorts_id
    WHERE r.original_shorts_id = %s;
    """

    cur.execute(sql, (shorts_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(rows)


@shorts_bp.route("/comment", methods=["POST"])
def comment_write():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")
    content = request.json.get("content")

    if None in (shorts_id, user_id, content):
        return jsonify({"error": "shorts_id, user_id and content required"}), 400

    conn = get_db()
    cur = conn.cursor()

    sql = """
    INSERT INTO Shorts_Comment (shorts_id, user_id, content)
    VALUES (%s, %s, %s);
    """

    try:
        cur.execute(sql, (shorts_id, user_id, content))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "Comment Added"}), 201


@shorts_bp.route("/reply", methods=["POST"])
def reply_write():
    shorts_id = request.json.get("shorts_id")
    user_id = request.json.get("user_id")
    parent_id = request.json.get("parent_id")
    content = request.json.get("content")

    if None in (shorts_id, user_id, parent_id, content):
        return jsonify({"error": "shorts_id, user_id, parent_id and content required"}), 400

    conn = get_db()
    cur = conn.cursor()

    sql = """
    INSERT INTO Shorts_Comment (shorts_id, user_id, parent_id, content)
    VALUES (%s, %s, %s, %s);
    """

    try:
        cur.execute(sql, (shorts_id, user_id, parent_id, content))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "Reply Added"}), 201


@shorts_bp.route("/comment/delete", methods=["POST"])
def comment_delete():
    comment_id = request.json.get("comment_id")
    if comment_id is None:
        return jsonify({"error": "comment_id required"}), 400

    conn = get_db()
    cur = conn.cursor()

    sql = "DELETE FROM Shorts_Comment WHERE comment_id = %s;"

    try:
        cur.execute(sql, (comment_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"message": "Deleted"})


@shorts_bp.route("/comment_count", methods=["POST"])
def comment_count():
    shorts_id = request.json.get("shorts_id")
    if shorts_id is None:
        return jsonify({"error": "shorts_id required"}), 400

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

    return jsonify(row or {"comment_count": 0})
