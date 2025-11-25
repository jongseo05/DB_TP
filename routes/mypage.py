from flask import Blueprint, request, jsonify
from db import get_db
from datetime import datetime

yt_bp = Blueprint("yt", __name__)


# ============================================================
# 1) Profile + Summary
#    GET /yt_profile/<user_id>
# ============================================================
@yt_bp.route("/yt_profile/<int:user_id>", methods=["GET"])
def yt_profile(user_id):
    """프로필 정보 + 각종 요약 통계"""
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # 프로필 정보
    cur.execute("""
        SELECT 
            user_id, 
            username, 
            handle, 
            profile_img, 
            subscriber_count, 
            join_date
        FROM Users
        WHERE user_id = %s
    """, (user_id,))
    profile = cur.fetchone()

    if not profile:
        cur.close()
        conn.close()
        return jsonify({"success": False, "error": "User not found"}), 404

    # 요약 정보
    summary = {}

    # 시청 기록 수
    cur.execute("""
        SELECT COUNT(*) AS cnt 
        FROM WatchHistory 
        WHERE user_id = %s
    """, (user_id,))
    summary["watch_history_count"] = cur.fetchone()["cnt"]

    # 재생목록 수
    cur.execute("""
        SELECT COUNT(*) AS cnt 
        FROM Playlists 
        WHERE user_id = %s
    """, (user_id,))
    summary["playlist_count"] = cur.fetchone()["cnt"]

    # 업로드 영상 수
    cur.execute("""
        SELECT COUNT(*) AS cnt 
        FROM Videos 
        WHERE user_id = %s
    """, (user_id,))
    summary["uploaded_count"] = cur.fetchone()["cnt"]

    # 오프라인 저장 수
    cur.execute("""
        SELECT COUNT(*) AS cnt 
        FROM OfflineVideo 
        WHERE user_id = %s
    """, (user_id,))
    summary["offline_count"] = cur.fetchone()["cnt"]

    # 영화 구매 수
    cur.execute("""
        SELECT COUNT(*) AS cnt 
        FROM MoviePurchases 
        WHERE user_id = %s
    """, (user_id,))
    summary["movie_purchase_count"] = cur.fetchone()["cnt"]

    # Premium 여부
    cur.execute("""
        SELECT 
            plan_type, 
            start_date, 
            end_date
        FROM Premium 
        WHERE user_id = %s
    """, (user_id,))
    premium_info = cur.fetchone()
    if premium_info:
        # is_active를 Python에서 계산 (end_date > 현재 시간)
        if premium_info.get("end_date"):
            premium_info["is_active"] = premium_info["end_date"] > datetime.now()
        else:
            premium_info["is_active"] = False
    summary["premium"] = premium_info if premium_info else None

    # 고객센터 문의 수
    cur.execute("""
        SELECT COUNT(*) AS cnt 
        FROM SupportTickets 
        WHERE user_id = %s
    """, (user_id,))
    summary["support_ticket_count"] = cur.fetchone()["cnt"]

    cur.close()
    conn.close()

    # datetime 변환
    if profile.get("join_date"):
        profile["join_date"] = profile["join_date"].strftime('%Y-%m-%d %H:%M:%S')
    
    if summary["premium"]:
        if summary["premium"].get("start_date"):
            summary["premium"]["start_date"] = summary["premium"]["start_date"].strftime('%Y-%m-%d %H:%M:%S')
        if summary["premium"].get("end_date"):
            summary["premium"]["end_date"] = summary["premium"]["end_date"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "profile": profile,
        "summary": summary
    })


# ============================================================
# 2) Watch History (Videos + Shorts + Live)
#    GET /yt_history?user_id=<user_id>&type=<all|video|shorts|live>
# ============================================================
@yt_bp.route("/yt_history", methods=["GET"])
def yt_history():
    """시청 기록 조회 (필터: video/shorts/live/all)"""
    user_id = request.args.get("user_id")
    type_filter = request.args.get("type", "all")

    if not user_id:
        return jsonify({"success": False, "error": "user_id is required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
        SELECT 
            h.history_id,
            h.video_id,
            v.title,
            v.thumbnail_url,
            v.duration,
            v.type_id,
            vt.type_name,
            h.last_position,
            h.is_finished,
            h.watched_at,
            v.view_count,
            v.like_count,
            v.comment_count,
            u.user_id AS creator_id,
            u.username AS creator_name,
            u.handle AS creator_handle,
            u.profile_img AS creator_profile
        FROM WatchHistory h
        JOIN Videos v ON h.video_id = v.video_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        JOIN Users u ON v.user_id = u.user_id
        WHERE h.user_id = %s
    """
    params = [user_id]

    if type_filter != "all":
        sql += " AND vt.type_name = %s"
        params.append(type_filter)

    sql += " ORDER BY h.watched_at DESC"

    cur.execute(sql, tuple(params))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    # datetime 변환
    for row in rows:
        if row.get("watched_at"):
            row["watched_at"] = row["watched_at"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "count": len(rows),
        "history": rows
    })


# ============================================================
# 3) Playlists (재생목록 목록)
#    GET /yt_playlists/<user_id>
# ============================================================
@yt_bp.route("/yt_playlists/<int:user_id>", methods=["GET"])
def yt_playlists(user_id):
    """사용자의 재생목록 조회"""
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            p.playlist_id,
            p.title,
            p.is_public,
            p.created_at,
            COUNT(pi.video_id) AS item_count
        FROM Playlists p
        LEFT JOIN PlaylistItems pi ON p.playlist_id = pi.playlist_id
        WHERE p.user_id = %s
        GROUP BY p.playlist_id, p.title, p.is_public, p.created_at
        ORDER BY p.created_at DESC
    """, (user_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # datetime 변환
    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "count": len(rows),
        "playlists": rows
    })


# ============================================================
# 4) My Videos (업로드한 영상)
#    GET /yt_myvideos?user_id=<user_id>&type=<all|video|shorts|live>
# ============================================================
@yt_bp.route("/yt_myvideos", methods=["GET"])
def yt_myvideos():
    """사용자가 업로드한 영상 조회"""
    user_id = request.args.get("user_id")
    type_filter = request.args.get("type", "all")

    if not user_id:
        return jsonify({"success": False, "error": "user_id is required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    sql = """
        SELECT
            v.video_id,
            v.title,
            v.thumbnail_url,
            v.duration,
            v.visibility,
            vt.type_id,
            vt.type_name,
            v.view_count,
            v.like_count,
            v.comment_count,
            v.upload_date
        FROM Videos v
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE v.user_id = %s
    """
    params = [user_id]

    if type_filter != "all":
        sql += " AND vt.type_name = %s"
        params.append(type_filter)

    sql += " ORDER BY v.upload_date DESC"

    cur.execute(sql, tuple(params))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    # datetime 변환
    for row in rows:
        if row.get("upload_date"):
            row["upload_date"] = row["upload_date"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "count": len(rows),
        "videos": rows
    })


# ============================================================
# 5) Offline Saved Videos (오프라인 저장 영상)
#    GET /yt_offline/<user_id>
# ============================================================
@yt_bp.route("/yt_offline/<int:user_id>", methods=["GET"])
def yt_offline(user_id):
    """오프라인 저장 영상 조회"""
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT
            o.user_id,
            o.video_id,
            v.title,
            v.thumbnail_url,
            v.duration,
            vt.type_name,
            o.file_path,
            o.saved_at,
            o.expired_at,
            u.username AS creator_name,
            u.handle AS creator_handle
        FROM OfflineVideo o
        JOIN Videos v ON o.video_id = v.video_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        JOIN Users u ON v.user_id = u.user_id
        WHERE o.user_id = %s
        ORDER BY o.saved_at DESC
    """, (user_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # datetime 변환
    for row in rows:
        if row.get("saved_at"):
            row["saved_at"] = row["saved_at"].strftime('%Y-%m-%d %H:%M:%S')
        if row.get("expired_at"):
            row["expired_at"] = row["expired_at"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "count": len(rows),
        "offline_videos": rows
    })


# ============================================================
# 6) Movie Purchases (영화 구매/대여 내역)
#    GET /yt_movies/<user_id>
# ============================================================
@yt_bp.route("/yt_movies/<int:user_id>", methods=["GET"])
def yt_movies(user_id):
    """영화 구매/대여 내역 조회"""
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            mp.purchase_id,
            mp.movie_id,
            m.title,
            m.thumbnail_url,
            m.duration,
            m.release_year,
            mp.type,
            mp.price_paid,
            mp.expired_at,
            mp.created_at
        FROM MoviePurchases mp
        JOIN Movies m ON mp.movie_id = m.movie_id
        WHERE mp.user_id = %s
        ORDER BY mp.created_at DESC
    """, (user_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # datetime 및 decimal 변환
    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].strftime('%Y-%m-%d %H:%M:%S')
        if row.get("expired_at"):
            row["expired_at"] = row["expired_at"].strftime('%Y-%m-%d %H:%M:%S')
        if row.get("price_paid"):
            row["price_paid"] = float(row["price_paid"])

    return jsonify({
        "success": True,
        "count": len(rows),
        "purchases": rows
    })


# ============================================================
# 7) Premium Info (프리미엄 정보)
#    GET /yt_premium/<user_id>
# ============================================================
@yt_bp.route("/yt_premium/<int:user_id>", methods=["GET"])
def yt_premium(user_id):
    """프리미엄 멤버십 정보 조회"""
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            user_id,
            plan_type, 
            start_date, 
            end_date
        FROM Premium
        WHERE user_id = %s
    """, (user_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return jsonify({
            "success": False,
            "message": "No premium subscription found"
        })

    # is_active를 Python에서 계산 (end_date > 현재 시간)
    if row.get("end_date"):
        is_active = row["end_date"] > datetime.now()
        row["is_active"] = is_active
    else:
        row["is_active"] = False

    # datetime 변환
    if row.get("start_date"):
        row["start_date"] = row["start_date"].strftime('%Y-%m-%d %H:%M:%S')
    if row.get("end_date"):
        row["end_date"] = row["end_date"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "premium": row
    })


# ============================================================
# 8) Watch Time Statistics (시청 시간 통계)
#    GET /yt_watchtime/<user_id>
# ============================================================
@yt_bp.route("/yt_watchtime/<int:user_id>", methods=["GET"])
def yt_watchtime(user_id):
    """시청 시간 통계 조회"""
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            watchtime_id,
            user_id,
            avg_daily_minutes,
            total_week_minutes,
            compare_last_week,
            updated_at
        FROM WatchTime
        WHERE user_id = %s
    """, (user_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return jsonify({
            "success": False,
            "message": "No watch time statistics found"
        })

    # datetime 변환
    if row.get("updated_at"):
        row["updated_at"] = row["updated_at"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "watchtime": row
    })


# ============================================================
# 9) Support Tickets (고객센터 문의 내역)
#    GET /yt_support/<user_id>
# ============================================================
@yt_bp.route("/yt_support/<int:user_id>", methods=["GET"])
def yt_support(user_id):
    """고객센터 문의 내역 조회"""
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            ticket_id,
            user_id,
            type,
            subject,
            message,
            status,
            created_at
        FROM SupportTickets
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # datetime 변환
    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "success": True,
        "count": len(rows),
        "tickets": rows
    })
