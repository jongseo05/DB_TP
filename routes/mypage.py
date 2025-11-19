from flask import Blueprint, request, jsonify
from db import get_db
import datetime

mypage_bp = Blueprint("mypage", __name__)


def time_ago(dt):
    if dt is None:
        return None
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


@mypage_bp.route('/yt_profile', methods=['POST'])
def yt_profile():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

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

    if row and row.get('join_date') is not None:
        row['join_date'] = str(row['join_date'])

    return jsonify(row)


@mypage_bp.route('/yt_history', methods=['POST'])
def yt_history():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    type_code = req.get('type_code', 'all')

    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    filter_sql = '' if type_code == 'all' else f"AND vt.type_code = %s"

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

    params = [user_id]
    if type_code != 'all':
        params.append(type_code)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if r.get('watched_at') is not None:
            r['watched_at'] = str(r['watched_at'])
        if r.get('duration_watched') is not None:
            r['duration_watched'] = str(r['duration_watched'])

    return jsonify(rows)


@mypage_bp.route('/yt_playlists', methods=['POST'])
def yt_playlists():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

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
        if r.get('created_at') is not None:
            r['created_at'] = str(r['created_at'])

    return jsonify(rows)


@mypage_bp.route('/yt_myvideos', methods=['POST'])
def yt_myvideos():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    type_code = req.get('type_code', 'all')

    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    filter_sql = '' if type_code == 'all' else f"AND vt.type_code = %s"

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

    params = [user_id]
    if type_code != 'all':
        params.append(type_code)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if r.get('upload_date') is not None:
            r['upload_date'] = str(r['upload_date'])
        if r.get('duration') is not None:
            r['duration'] = str(r['duration'])

    return jsonify(rows)


@mypage_bp.route('/yt_offline', methods=['POST'])
def yt_offline():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

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
        if r.get('save_date') is not None:
            r['save_date'] = str(r['save_date'])

    return jsonify(rows)


@mypage_bp.route('/yt_movies', methods=['POST'])
def yt_movies():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

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
        if r.get('purchase_date') is not None:
            r['purchase_date'] = str(r['purchase_date'])
        if r.get('expire_date') is not None:
            r['expire_date'] = str(r['expire_date'])
        if r.get('duration') is not None:
            r['duration'] = str(r['duration'])

    return jsonify(rows)


@mypage_bp.route('/yt_premium', methods=['POST'])
def yt_premium():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT premium_id, join_date, plan_type, is_active
        FROM Premium
        WHERE user_id = %s;
    """, (user_id,))
    info = cur.fetchall()

    cur.execute("""
        SELECT pu.benefit_type, pu.usage_value, pu.last_updated
        FROM PremiumUsage pu
        WHERE pu.premium_id IN (
            SELECT premium_id FROM Premium WHERE user_id = %s
        );
    """, (user_id,))
    usage = cur.fetchall()

    cur.close()
    conn.close()

    for p in info:
        if p.get('join_date') is not None:
            p['join_date'] = str(p['join_date'])
    for u in usage:
        if u.get('last_updated') is not None:
            u['last_updated'] = str(u['last_updated'])

    return jsonify({"premium": info, "usage": usage})


@mypage_bp.route('/yt_watchtime', methods=['POST'])
def yt_watchtime():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT avg_daily_minutes, total_week_minutes,
               compare_last_week, updated_at
        FROM WatchTime
        WHERE user_id = %s;
    """, (user_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row and row.get('updated_at') is not None:
        row['updated_at'] = str(row['updated_at'])

    return jsonify(row)


@mypage_bp.route('/yt_support', methods=['POST'])
def yt_support():
    req = request.get_json() or {}
    user_id = req.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT support_id, category, message, status, created_at
        FROM Support
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """, (user_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    for r in rows:
        if r.get('created_at') is not None:
            r['created_at'] = str(r['created_at'])

    return jsonify(rows)
