from flask import Blueprint, request, jsonify
from db import get_db
import datetime

bp = Blueprint("subscriptions", __name__)

# --------------------------
# 1. 상단 사용자 헤더
# --------------------------
@bp.get("/<int:user_id>/header")
def get_header(user_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
    SELECT 
        u.user_id AS channel_id,
        u.username AS channel_name,
        u.profile_img AS channel_profile,
        MAX(v.upload_date) AS latest_upload,
        (
            SELECT v2.thumbnail_url 
            FROM Videos v2 
            WHERE v2.user_id = u.user_id 
            ORDER BY v2.upload_date DESC 
            LIMIT 1
        ) AS latest_thumbnail
    FROM Subscriptions s
    JOIN Users u ON s.channel_id = u.user_id
    LEFT JOIN Videos v ON v.user_id = u.user_id
    WHERE s.subscriber_id = %s
    GROUP BY u.user_id, u.username, u.profile_img
    ORDER BY latest_upload DESC;
    """
    
    cur.execute(query, (user_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify({"headers": rows})


# --------------------------
# 2. 카테고리 필터 리스트 (게시물 제거)
# --------------------------
@bp.get("/filters")
def get_filters():
    return jsonify({
        "filters": [
            "전체",
            "오늘",
            "동영상",
            "shorts",
            "라이브",
            "이어서시청하기",
            "시청하지않음"
        ]
    })


# --------------------------
# 3. 구독 피드
# --------------------------
@bp.get("/<int:user_id>/feed")
def get_feed(user_id):
    filter_type = request.args.get("type")    # ex) video / shorts / live
    filter_opt  = request.args.get("filter")  # ex) today / continue / unwatched / all

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
    SELECT 
        v.video_id,
        v.title,
        v.thumbnail_url,
        v.duration,
        v.upload_date,
        TIMESTAMPDIFF(MINUTE, v.upload_date, NOW()) AS minutes_diff,
                vt.type_name,
        u.user_id AS channel_id,
        u.username AS channel_name,
        u.profile_img AS channel_profile,
                COALESCE(v.view_count, 0) AS view_count
    FROM Subscriptions s
    JOIN Videos v ON s.channel_id = v.user_id
    JOIN Users u ON u.user_id = v.user_id
    JOIN VideoType vt ON vt.type_id = v.type_id
    WHERE s.subscriber_id = %s
      AND v.visibility = 'public'
    """

    params = [user_id]

    # 타입 필터
    if filter_type and filter_type != "all":
        query += " AND vt.type_name = %s "
        params.append(filter_type)

    # 오늘 업로드
    if filter_opt == "today":
        query += " AND DATE(v.upload_date) = CURDATE() "

    # 시청하지 않은 영상
    if filter_opt == "unwatched":
        query += """
        AND v.video_id NOT IN (
            SELECT video_id FROM WatchHistory WHERE user_id = %s
        )
        """
        params.append(user_id)

    # 이어서 시청하기
    if filter_opt == "continue":
        query += """
        AND v.video_id IN (
            SELECT wh.video_id
            FROM WatchHistory wh
            WHERE wh.user_id = %s
                            AND wh.last_position IS NOT NULL
                            AND wh.last_position > 0
                            AND wh.last_position < v.duration
        )
        """
        params.append(user_id)

    query += " ORDER BY v.upload_date DESC LIMIT 20;"

    cur.execute(query, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    # minutes_diff -> time_ago
    for row in rows:
        minutes = row.pop("minutes_diff", None)
        if minutes is None:
            row["time_ago"] = None
            continue

        m = int(minutes)
        if m < 1:
            row["time_ago"] = "방금 전"
        elif m < 60:
            row["time_ago"] = f"{m}분 전"
        elif m < 60 * 24:
            row["time_ago"] = f"{m // 60}시간 전"
        elif m < 60 * 24 * 7:
            row["time_ago"] = f"{m // (60 * 24)}일 전"
        elif m < 60 * 24 * 30:
            row["time_ago"] = f"{m // (60 * 24 * 7)}주 전"
        elif m < 60 * 24 * 365:
            row["time_ago"] = f"{m // (60 * 24 * 30)}개월 전"
        else:
            row["time_ago"] = f"{m // (60 * 24 * 365)}년 전"

    # Convert non-JSON-serializable types to strings (datetime, date, timedelta)
    for row in rows:
        for k, v in list(row.items()):
            if isinstance(v, datetime.datetime):
                row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(v, datetime.date):
                row[k] = v.strftime("%Y-%m-%d")
            elif isinstance(v, datetime.timedelta):
                total = int(v.total_seconds())
                hh = total // 3600
                mm = (total % 3600) // 60
                ss = total % 60
                row[k] = f"{hh:02d}:{mm:02d}:{ss:02d}"

    return jsonify({"feed": rows})


# --------------------------
# 4. 구독하기
#    POST /subscriptions/{user_id}/channel/{channel_id}
# --------------------------
@bp.post("/<int:user_id>/channel/<int:channel_id>")
def subscribe_channel(user_id, channel_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            """
            INSERT INTO Subscriptions (subscriber_id, channel_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE created_at = CURRENT_TIMESTAMP
            """,
            (user_id, channel_id)
        )
        conn.commit()
        
        # 구독 정보 조회
        cur.execute("""
            SELECT 
                s.subscriber_id,
                u1.username AS subscriber_name,
                u1.handle AS subscriber_handle,
                s.channel_id,
                u2.username AS channel_name,
                u2.handle AS channel_handle,
                s.created_at
            FROM Subscriptions s
            JOIN Users u1 ON s.subscriber_id = u1.user_id
            JOIN Users u2 ON s.channel_id = u2.user_id
            WHERE s.subscriber_id = %s AND s.channel_id = %s
        """, (user_id, channel_id))
        
        subscription = cur.fetchone()
        
        return jsonify({
            "success": True, 
            "action": "subscribed",
            "subscription": subscription
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()


# --------------------------
# 5. 구독 취소
#    DELETE /subscriptions/{user_id}/channel/{channel_id}
# --------------------------
@bp.delete("/<int:user_id>/channel/<int:channel_id>")
def unsubscribe_channel(user_id, channel_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # 삭제 전 정보 조회
    cur.execute("""
        SELECT 
            u1.username AS subscriber_name,
            u1.handle AS subscriber_handle,
            u2.username AS channel_name,
            u2.handle AS channel_handle
        FROM Subscriptions s
        JOIN Users u1 ON s.subscriber_id = u1.user_id
        JOIN Users u2 ON s.channel_id = u2.user_id
        WHERE s.subscriber_id = %s AND s.channel_id = %s
    """, (user_id, channel_id))
    
    subscription_info = cur.fetchone()

    cur.execute(
        "DELETE FROM Subscriptions WHERE subscriber_id = %s AND channel_id = %s",
        (user_id, channel_id)
    )
    affected_rows = cur.rowcount
    conn.commit()

    cur.close()
    conn.close()
    
    if affected_rows > 0 and subscription_info:
        return jsonify({
            "success": True, 
            "action": "unsubscribed",
            "subscriber_id": user_id,
            "subscriber_name": subscription_info["subscriber_name"],
            "subscriber_handle": subscription_info["subscriber_handle"],
            "channel_id": channel_id,
            "channel_name": subscription_info["channel_name"],
            "channel_handle": subscription_info["channel_handle"]
        })
    else:
        return jsonify({"success": False, "error": "Subscription not found"}), 404


# --------------------------
# 6. 구독 채널 목록 (사용자 관점)
#    GET /<user_id>/subscriptions?limit=20&offset=0
#    반환: channel_id, channel_name, channel_profile, subscribed_at
# --------------------------
@bp.get("/<int:user_id>/subscriptions")
def get_subscriptions(user_id):
    # pagination params
    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400

    # bounds
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # total count
    count_q = "SELECT COUNT(*) AS total FROM Subscriptions WHERE subscriber_id = %s"
    cur.execute(count_q, (user_id,))
    total_row = cur.fetchone()
    total = total_row["total"] if total_row else 0

    # list: 유튜브 앱 기준 — 사용자가 구독한 채널의 채널명과 프로필 이미지만 반환
    query = """
    SELECT
        DISTINCT u.user_id AS channel_id,
        u.username AS channel_name,
        u.profile_img AS channel_profile
    FROM Subscriptions s
    JOIN Users u ON s.channel_id = u.user_id
    WHERE s.subscriber_id = %s
    ORDER BY u.username ASC
    LIMIT %s OFFSET %s
    """

    cur.execute(query, (user_id, limit, offset))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "subscriptions": rows,
        "total": total,
        "limit": limit,
        "offset": offset
    })
