# routes/offline.py
from flask import Blueprint, request, jsonify
from db import get_db

offline_bp = Blueprint("offline", __name__)

# --------------------------
# 1. 동영상 오프라인 저장
#    POST /offline/{user_id}/video/{video_id}
# --------------------------
@offline_bp.post("/<int:user_id>/video/<int:video_id>")
def save_offline(user_id, video_id):
    data = request.get_json(silent=True) or {}

    file_size_mb = data.get("file_size_mb", 0.0)
    quality = data.get("quality", "720p")
    storage_type = data.get("storage_type", "smart")

    db = get_db()
    cur = db.cursor()

    try:
        cur.execute(
            """
            INSERT INTO OfflineVideo (user_id, video_id, save_date, file_size_mb, quality, storage_type, is_updated)
            VALUES (%s, %s, NOW(), %s, %s, %s, FALSE)
            ON DUPLICATE KEY UPDATE
              save_date = NOW(),
              file_size_mb = VALUES(file_size_mb),
              quality = VALUES(quality),
              storage_type = VALUES(storage_type),
              is_updated = FALSE
            """,
            (user_id, video_id, file_size_mb, quality, storage_type)
        )
        db.commit()
        return jsonify({"success": True, "action": "saved_offline"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        cur.close()
        db.close()


# --------------------------
# 2. 오프라인 저장 삭제
#    DELETE /offline/{user_id}/video/{video_id}
# --------------------------
@offline_bp.delete("/<int:user_id>/video/<int:video_id>")
def delete_offline(user_id, video_id):
    db = get_db()
    cur = db.cursor()

    cur.execute(
        "DELETE FROM OfflineVideo WHERE user_id = %s AND video_id = %s",
        (user_id, video_id)
    )
    db.commit()

    cur.close()
    db.close()
    return jsonify({"success": True, "action": "deleted_offline"})


# --------------------------
# 3. 내 오프라인 영상 목록
#    GET /offline/{user_id}
# --------------------------
@offline_bp.get("/<int:user_id>")
def list_offline(user_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        """
        SELECT 
          ov.offline_id,
          ov.video_id,
          ov.save_date,
          ov.file_size_mb,
          ov.quality,
          v.title,
          v.thumbnail_url
        FROM OfflineVideo ov
        JOIN Videos v ON v.video_id = ov.video_id
        WHERE ov.user_id = %s
        ORDER BY ov.save_date DESC
        """,
        (user_id,)
    )
    rows = cur.fetchall()

    cur.close()
    db.close()
    return jsonify({"offline_videos": rows})
