from flask import Blueprint, jsonify, request
from db import get_db
import datetime

yt_bp = Blueprint("yt", __name__)

# --------------------------------------------------
# 상대 시간 변환 함수 (“3일 전”, “2개월 전”)
# --------------------------------------------------
def time_ago(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            # 가능하면 문자열도 datetime으로 변환
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return dt

    now = datetime.datetime.now()
    delta = now - dt

    if delta.days < 1:
        return "오늘"
    elif delta.days < 30:
        return f"{delta.days}일 전"
    elif delta.days < 365:
        return f"{delta.days // 30}개월 전"
    else:
        return f"{delta.days // 365}년 전"


# ============================================================
# 1) 프로필 + 요약
#    POST /yt_profile
# ============================================================
@yt_bp.route("/yt_profile/<int:user_id>", methods=["GET"])
def yt_profile(user_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
            u.user_id, u.username, u.handle, u.profile_img, u.join_date,
            (SELECT COUNT(*) FROM WatchHistory h WHERE h.user_id = u.user_id) AS history_count,
            (SELECT COUNT(*) FROM Playlists p WHERE p.user_id = u.user_id) AS playlist_count,
            (SELECT COUNT(*) FROM Videos v WHERE v.user_id = u.user_id) AS upload_count,
            (SELECT COUNT(*) FROM OfflineVideo o WHERE o.user_id = u.user_id) AS offline_count,
            (SELECT COUNT(*) FROM MoviePurchase mp WHERE mp.user_id = u.user_id) AS movie_count,
            (SELECT COUNT(*) FROM Premium pr WHERE pr.user_id = u.user_id AND pr.is_active = TRUE) AS premium_active,
            (SELECT COUNT(*) FROM Support s WHERE s.user_id = u.user_id AND s.status='open') AS open_support
        FROM Users u
        WHERE u.user_id = %s;
    """

    cur.execute(query, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        if isinstance(row.get("join_date"), (datetime.date, datetime.datetime)):
            row["join_date"] = str(row["join_date"])

    return jsonify(row)


# ============================================================
# 2) 시청 기록 (동영상/쇼츠/라이브 필터)
#    POST /yt_history
# ============================================================
@yt_bp.route("/yt_history", methods=["GET"])
def yt_history():
    user_id = request.args.get("user_id")
    type_code = request.args.get("type_code", "all")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    filter_sql = "" if type_code == "all" else f"AND vt.type_code = '{type_code}'"

    query = f"""
        SELECT
            v.video_id,
            v.title,
            v.category,
            vt.type_code,
            vt.type_name,
            v.thumbnail_url,
            h.watched_at,
            h.duration_watched,
            h.device_type
        FROM WatchHistory h
        JOIN Videos v ON h.video_id = v.video_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE h.user_id = %s
        {filter_sql}
        ORDER BY h.watched_at DESC;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if isinstance(r.get("watched_at"), (datetime.date, datetime.datetime)):
            r["watched_at"] = str(r["watched_at"])
        if r.get("duration_watched") is not None:
            r["duration_watched"] = str(r["duration_watched"])

    return jsonify(rows)


# ============================================================
# 3) 재생목록 목록
#    POST /yt_playlists
# ============================================================
@yt_bp.route("/yt_playlists/<int:user_id>", methods=["GET"])
def yt_playlists(user_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
            p.playlist_id,
            p.title,
            p.visibility,
            p.created_at,
            COUNT(pv.video_id) AS video_count
        FROM Playlists p
        LEFT JOIN PlaylistVideo pv ON p.playlist_id = pv.playlist_id
        WHERE p.user_id = %s
        GROUP BY p.playlist_id, p.title, p.visibility, p.created_at
        ORDER BY p.created_at DESC;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if isinstance(r.get("created_at"), (datetime.date, datetime.datetime)):
            r["created_at"] = str(r["created_at"])

    return jsonify(rows)


# ============================================================
# 4) 내 동영상 (video / shorts / live 구분)
#    POST /yt_myvideos
# ============================================================
@yt_bp.route("/yt_myvideos", methods=["GET"])
def yt_myvideos():
    user_id = request.args.get("user_id")
    type_code = request.args.get("type_code", "all")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    filter_sql = "" if type_code == "all" else "AND vt.type_code = %s"

    query = f"""
        SELECT
            v.video_id,
            v.title,
            v.category,
            vt.type_code,
            vt.type_name,
            v.visibility,
            v.upload_date,
            IFNULL(s.view_count, v.views) AS views,
            IFNULL(s.like_count, 0) AS likes,
            IFNULL(s.comment_count, 0) AS comments,
            v.duration
        FROM Videos v
        JOIN VideoType vt ON v.type_id = vt.type_id
        LEFT JOIN VideoStats s ON v.video_id = s.video_id
        WHERE v.user_id = %s
        {filter_sql}
        ORDER BY v.upload_date DESC;
    """

    params = (user_id,) if type_code == "all" else (user_id, type_code)
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if isinstance(r.get("upload_date"), (datetime.date, datetime.datetime)):
            r["upload_date"] = str(r["upload_date"])
        if r.get("duration") is not None:
            r["duration"] = str(r["duration"])

    return jsonify(rows)


# ============================================================
# 5) 오프라인 저장 동영상
#    POST /yt_offline
# ============================================================
@yt_bp.route("/yt_offline/<int:user_id>", methods=["GET"])
def yt_offline(user_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT
            o.offline_id,
            v.video_id,
            v.title,
            vt.type_code,
            vt.type_name,
            v.thumbnail_url,
            o.save_date,
            o.file_size_mb,
            o.quality,
            o.storage_type,
            o.is_updated
        FROM OfflineVideo o
        JOIN Videos v ON o.video_id = v.video_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE o.user_id = %s
        ORDER BY o.save_date DESC;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if isinstance(r.get("save_date"), (datetime.date, datetime.datetime)):
            r["save_date"] = str(r["save_date"])

    return jsonify(rows)


# ============================================================
# 6) 영화 구매/대여 목록
#    POST /yt_movies
# ============================================================
@yt_bp.route("/yt_movies/<int:user_id>", methods=["GET"])
def yt_movies(user_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT
            m.movie_id,
            m.title,
            m.genre,
            m.release_year,
            m.duration,
            m.rating_label,
            m.thumbnail_url,
            mp.purchase_type,
            mp.purchase_date,
            mp.expire_date,
            mp.price
        FROM MoviePurchase mp
        JOIN Movie m ON mp.movie_id = m.movie_id
        WHERE mp.user_id = %s
        ORDER BY mp.purchase_date DESC;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if isinstance(r.get("purchase_date"), (datetime.date, datetime.datetime)):
            r["purchase_date"] = str(r["purchase_date"])
        if r.get("expire_date") is not None and isinstance(
            r.get("expire_date"), (datetime.date, datetime.datetime)
        ):
            r["expire_date"] = str(r["expire_date"])
        if r.get("duration") is not None:
            r["duration"] = str(r["duration"])

    return jsonify(rows)


# ============================================================
# 7) Premium 정보 + 사용량
#    POST /yt_premium
# ============================================================
@yt_bp.route("/yt_premium/<int:user_id>", methods=["GET"])
def yt_premium(user_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Premium 가입 정보
    cur.execute(
        """
        SELECT premium_id, join_date, plan_type, is_active
        FROM Premium
        WHERE user_id = %s;
        """,
        (user_id,),
    )
    info = cur.fetchall()

    # Premium 사용 내역
    cur.execute(
        """
        SELECT pu.benefit_type, pu.usage_value, pu.last_updated
        FROM PremiumUsage pu
        WHERE pu.premium_id IN (
            SELECT premium_id FROM Premium WHERE user_id = %s
        );
        """,
        (user_id,),
    )
    usage = cur.fetchall()

    cur.close()
    conn.close()

    for p in info:
        if isinstance(p.get("join_date"), (datetime.date, datetime.datetime)):
            p["join_date"] = str(p["join_date"])

    for u in usage:
        if isinstance(u.get("last_updated"), (datetime.date, datetime.datetime)):
            u["last_updated"] = str(u["last_updated"])

    return jsonify({"premium": info, "usage": usage})


# ============================================================
# 8) 시청 시간
#    POST /yt_watchtime
# ============================================================
@yt_bp.route("/yt_watchtime/<int:user_id>", methods=["GET"])
def yt_watchtime(user_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT avg_daily_minutes, total_week_minutes,
               compare_last_week, updated_at
        FROM WatchTime
        WHERE user_id = %s;
        """,
        (user_id,),
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        if isinstance(row.get("updated_at"), (datetime.date, datetime.datetime)):
            row["updated_at"] = str(row["updated_at"])

    return jsonify(row)


# ============================================================
# 9) 고객센터(내 문의)
#    POST /yt_support
# ============================================================
@yt_bp.route("/yt_support/<int:user_id>", methods=["GET"])
def yt_support(user_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT support_id, category, message, status, created_at
        FROM Support
        WHERE user_id = %s
        ORDER BY created_at DESC;
        """,
        (user_id,),
    )
    rows = cur.fetchall()

    cur.close()
    conn.close()

    for r in rows:
        if isinstance(r.get("created_at"), (datetime.date, datetime.datetime)):
            r["created_at"] = str(r["created_at"])

    return jsonify(rows)
