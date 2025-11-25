from flask import Blueprint, jsonify, request
from db import get_db
from datetime import datetime

home_bp = Blueprint('home', __name__)

# --------------------------------------------------
# 업로드 시각 → "n분 전 / n시간 전" 같은 문자열로 변환
# --------------------------------------------------
def time_ago(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt

    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "방금 전"
    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)}분 전"
    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)}시간 전"
    days = hours // 24
    if days < 7:
        return f"{int(days)}일 전"
    weeks = days // 7
    return f"{int(weeks)}주 전"


# ==================================================
# 1) 시간대 기반 추천
# ==================================================
@home_bp.route("/time", methods=["GET"])
def home_time():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
            V.video_id,
            V.title,
            VT.type_name AS video_type,
            V.view_count,
            V.upload_date,
            U.user_id,
            U.username AS uploader_name,
            U.profile_img,
            CASE
                WHEN HOUR(NOW()) BETWEEN 18 AND 23 AND VT.type_name = 'video'  THEN 10
                WHEN HOUR(NOW()) BETWEEN  6 AND 17 AND VT.type_name = 'shorts' THEN 10
                ELSE 1
            END AS type_weight
        FROM Videos V
        JOIN Users U ON U.user_id = V.user_id
        JOIN VideoType VT ON V.type_id = VT.type_id
        WHERE V.visibility = 'public'
        ORDER BY (V.view_count * type_weight) DESC, V.upload_date DESC
        LIMIT 20;
    """

    cur.execute(query)
    rows = cur.fetchall()

    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])

    cur.close()
    conn.close()
    return jsonify(rows)


# ==================================================
# 2) 최근 본 영상 5개
# ==================================================
@home_bp.route("/watch/recent", methods=["GET"])
def recent_watch():
    user_id = request.args.get("user_id", 1)  # 기본값 1
    
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
            wh.watched_at,
            v.video_id,
            v.title,
            vt.type_name AS video_type,
            CASE
                WHEN v.view_count >= 100000000 THEN CONCAT(ROUND(v.view_count / 100000000, 1), '억')
                WHEN v.view_count >= 10000       THEN CONCAT(ROUND(v.view_count / 10000, 1), '만')
                ELSE v.view_count
            END AS pretty_views,
            v.view_count AS raw_views,
            v.upload_date,
            u.user_id AS creator_id,
            u.username AS creator_name,
            u.profile_img AS creator_profile_image
        FROM WatchHistory wh
        JOIN Videos v ON wh.video_id = v.video_id
        JOIN Users u  ON v.user_id  = u.user_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE wh.user_id = %s
        ORDER BY wh.watched_at DESC
        LIMIT 5;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()

    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])

    cur.close()
    conn.close()
    return jsonify(rows)


# ==================================================
# 3) 광고 추천 (최근 7일 시청 기록 기반)
# ==================================================
@home_bp.route("/ads/recommend", methods=["GET"])
def ads_recommend():
    user_id = request.args.get("user_id", 1)  # 기본값 1
    
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT
            top_type.type_name AS video_type,
            CASE
                WHEN top_type.type_name = 'video'  THEN '일반 동영상 광고'
                WHEN top_type.type_name = 'shorts' THEN '쇼츠 전용 광고'
                WHEN top_type.type_name = 'live'   THEN '라이브 스트리밍 광고'
                ELSE '기본 광고'
            END AS recommended_ad,
            CASE
                WHEN top_type.type_name = 'video'  THEN 'https://cdn.example.com/ad/video_banner.png'
                WHEN top_type.type_name = 'shorts' THEN 'https://cdn.example.com/ad/shorts_banner.png'
                WHEN top_type.type_name = 'live'   THEN 'https://cdn.example.com/ad/live_banner.png'
                ELSE 'https://cdn.example.com/ad/default_banner.png'
            END AS ad_image_url
        FROM (
            SELECT vt.type_name
            FROM WatchHistory wh
            JOIN Videos v    ON wh.video_id = v.video_id
            JOIN VideoType vt ON v.type_id  = vt.type_id
            WHERE wh.user_id = %s
              AND wh.watched_at >= NOW() - INTERVAL 7 DAY
            GROUP BY vt.type_name
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) AS top_type;
    """

    cur.execute(query, (user_id,))
    row = cur.fetchone()
    
    # 시청 기록이 없으면 기본 광고
    if not row:
        row = {
            "video_type": "General",
            "recommended_ad": "기본 광고",
            "ad_image_url": "https://cdn.example.com/ad/default_banner.png"
        }

    cur.close()
    conn.close()
    return jsonify(row)


# ==================================================
# 4) 크리에이터 TOP2 → 조회수 TOP4
# ==================================================
@home_bp.route("/creators/top", methods=["GET"])
def top_creators():
    user_id = request.args.get("user_id", 1)  # 기본값 1
    
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        WITH top_creators AS (
            SELECT v.user_id AS creator_id
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = %s
            GROUP BY v.user_id
            ORDER BY COUNT(*) DESC
            LIMIT 2
        )
        SELECT 
            v.video_id,
            v.user_id AS creator_id,
            u.username AS creator_name,
            u.profile_img AS creator_profile_image,
            v.title,
            vt.type_name AS video_type,
            CASE
                WHEN v.view_count >= 100000000 THEN CONCAT(ROUND(v.view_count / 100000000, 1), '억')
                WHEN v.view_count >= 10000       THEN CONCAT(ROUND(v.view_count / 10000, 1), '만')
                ELSE v.view_count
            END AS pretty_views,
            v.view_count AS raw_views,
            v.upload_date
        FROM Videos v
        JOIN top_creators tc ON v.user_id = tc.creator_id
        JOIN Users u         ON v.user_id = u.user_id
        JOIN VideoType vt    ON v.type_id = vt.type_id
        ORDER BY v.view_count DESC, v.upload_date DESC
        LIMIT 4;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify(rows)


# ==================================================
# 5) 랜덤 게시물 + 베스트 댓글 1개
# ==================================================
@home_bp.route("/post/random", methods=["GET"])
def post_random():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Videos 테이블에서 일반 영상 1개 랜덤 선택 + 베스트 댓글
    query_post = """
        SELECT 
            p.video_id AS post_id,
            p.title,
            p.description AS post_text,
            p.upload_date,
            p.view_count AS views,
            u.user_id AS author_id,
            u.username AS author_name,
            u.profile_img AS author_profile_url,
            c_top.content AS top_comment,
            c_top.like_count AS top_comment_likes,
            u_top.username AS top_comment_user,
            u_top.profile_img AS top_comment_user_profile
        FROM Videos p
        JOIN Users u ON p.user_id = u.user_id
        LEFT JOIN Comments c_top
          ON c_top.comment_id = (
            SELECT c2.comment_id
            FROM Comments c2
            WHERE c2.video_id = p.video_id
              AND c2.parent_id IS NULL
            ORDER BY c2.like_count DESC, c2.created_at ASC
            LIMIT 1
          )
        LEFT JOIN Users u_top ON c_top.user_id = u_top.user_id
        WHERE p.visibility = 'public'
        ORDER BY RAND()
        LIMIT 1;
    """
    cur.execute(query_post)
    post = cur.fetchone()

    if not post:
        cur.close()
        conn.close()
        return jsonify({"error": "No video found"}), 404

    post["uploaded_before"] = time_ago(post["upload_date"])

    cur.close()
    conn.close()
    return jsonify(post)


# ==================================================
# 6) 랜덤 숏츠 (VideoType 기반)
# ==================================================
@home_bp.route("/shorts/random", methods=["GET"])
def shorts_random():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Videos 테이블에서 type_name='shorts'인 영상 조회
    query = """
        SELECT
            v.video_id AS short_id,
            v.thumbnail_url AS short_thumbnail,
            CASE
                WHEN CHAR_LENGTH(v.title) > 12 THEN CONCAT(LEFT(v.title, 12), '…')
                ELSE v.title
            END AS short_title,
            v.view_count AS views,
            u.username,
            u.profile_img
        FROM Videos v
        JOIN Users u ON v.user_id = u.user_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE vt.type_name = 'shorts'
          AND v.visibility = 'public'
        ORDER BY RAND()
        LIMIT 6;
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify(rows)


# ==================================================
# 7) 홈뷰 풀 세트
# ==================================================
@home_bp.route("/full", methods=["GET"])
def home_full():
    user_id = request.args.get("user_id", 1)  # 기본값 1
    
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    result = {}

    # ----------------------
    # 시간대 기반 추천
    cur.execute("""
        SELECT 
            V.video_id,
            V.title,
            VT.type_name AS video_type,
            V.view_count,
            V.upload_date,
            U.user_id,
            U.username AS uploader_name,
            U.profile_img,
            CASE
                WHEN HOUR(NOW()) BETWEEN 18 AND 23 AND VT.type_name = 'video'  THEN 10
                WHEN HOUR(NOW()) BETWEEN  6 AND 17 AND VT.type_name = 'shorts' THEN 10
                ELSE 1
            END AS type_weight
        FROM Videos V
        JOIN Users U ON U.user_id = V.user_id
        JOIN VideoType VT ON V.type_id = VT.type_id
        WHERE V.visibility = 'public'
        ORDER BY (V.view_count * type_weight) DESC, V.upload_date DESC
        LIMIT 20;
    """)
    rows = cur.fetchall()
    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])
    result["time_based"] = rows

    # ----------------------
    # 최근 본 영상 5개
    query = """
        SELECT 
            wh.watched_at,
            v.video_id,
            v.title,
            vt.type_name AS video_type,
            CASE
                WHEN v.view_count >= 100000000 THEN CONCAT(ROUND(v.view_count / 100000000, 1), '억')
                WHEN v.view_count >= 10000       THEN CONCAT(ROUND(v.view_count / 10000, 1), '만')
                ELSE v.view_count
            END AS pretty_views,
            v.view_count AS raw_views,
            v.upload_date,
            u.user_id AS creator_id,
            u.username AS creator_name,
            u.profile_img AS creator_profile_image
        FROM WatchHistory wh
        JOIN Videos v ON wh.video_id = v.video_id
        JOIN Users u  ON v.user_id  = u.user_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE wh.user_id = %s
        ORDER BY wh.watched_at DESC
        LIMIT 5;
    """
    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])
    result["recent_watched"] = rows

    # ----------------------
    # 광고 (최근 7일 시청 기록 기반)
    cur.execute("""
        SELECT
            top_type.type_name AS video_type,
            CASE
                WHEN top_type.type_name = 'video'  THEN '일반 동영상 광고'
                WHEN top_type.type_name = 'shorts' THEN '쇼츠 전용 광고'
                WHEN top_type.type_name = 'live'   THEN '라이브 스트리밍 광고'
                ELSE '기본 광고'
            END AS recommended_ad,
            CASE
                WHEN top_type.type_name = 'video'  THEN 'https://cdn.example.com/ad/video_banner.png'
                WHEN top_type.type_name = 'shorts' THEN 'https://cdn.example.com/ad/shorts_banner.png'
                WHEN top_type.type_name = 'live'   THEN 'https://cdn.example.com/ad/live_banner.png'
                ELSE 'https://cdn.example.com/ad/default_banner.png'
            END AS ad_image_url
        FROM (
            SELECT vt.type_name
            FROM WatchHistory wh
            JOIN Videos v    ON wh.video_id = v.video_id
            JOIN VideoType vt ON v.type_id  = vt.type_id
            WHERE wh.user_id = %s
              AND wh.watched_at >= NOW() - INTERVAL 7 DAY
            GROUP BY vt.type_name
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) AS top_type;
    """, (user_id,))
    ad_row = cur.fetchone()
    if not ad_row:
        ad_row = {
            "video_type": "General",
            "recommended_ad": "기본 광고",
            "ad_image_url": "https://cdn.example.com/ad/default_banner.png"
        }
    result["ads"] = ad_row

    # ----------------------
    # TOP2 → 조회수 TOP4
    query = """
        WITH top_creators AS (
            SELECT v.user_id AS creator_id
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = %s
            GROUP BY v.user_id
            ORDER BY COUNT(*) DESC
            LIMIT 2
        )
        SELECT 
            v.video_id,
            v.user_id AS creator_id,
            u.username AS creator_name,
            u.profile_img AS creator_profile_image,
            v.title,
            vt.type_name AS video_type,
            CASE
                WHEN v.view_count >= 100000000 THEN CONCAT(ROUND(v.view_count / 100000000, 1), '억')
                WHEN v.view_count >= 10000       THEN CONCAT(ROUND(v.view_count / 10000, 1), '만')
                ELSE v.view_count
            END AS pretty_views,
            v.view_count AS raw_views,
            v.upload_date
        FROM Videos v
        JOIN top_creators tc ON v.user_id = tc.creator_id
        JOIN Users u         ON v.user_id = u.user_id
        JOIN VideoType vt    ON v.type_id = vt.type_id
        ORDER BY v.view_count DESC, v.upload_date DESC
        LIMIT 4;
    """
    cur.execute(query, (user_id,))
    result["top_creators"] = cur.fetchall()

    # ----------------------
    # 랜덤 영상 (type_name='video') + 베스트 댓글
    cur.execute("""
        SELECT 
            p.video_id AS post_id,
            p.title,
            p.description AS post_text,
            p.upload_date,
            p.view_count AS views,
            u.user_id AS author_id,
            u.username AS author_name,
            u.profile_img AS author_profile_url,
            c_top.content AS top_comment,
            c_top.like_count AS top_comment_likes,
            u_top.username AS top_comment_user,
            u_top.profile_img AS top_comment_user_profile
        FROM Videos p
        JOIN Users u ON p.user_id = u.user_id
        LEFT JOIN Comments c_top
          ON c_top.comment_id = (
            SELECT c2.comment_id
            FROM Comments c2
            WHERE c2.video_id = p.video_id
              AND c2.parent_id IS NULL
            ORDER BY c2.like_count DESC, c2.created_at ASC
            LIMIT 1
          )
        LEFT JOIN Users u_top ON c_top.user_id = u_top.user_id
        WHERE p.visibility = 'public'
        ORDER BY RAND()
        LIMIT 1;
    """)
    post = cur.fetchone()
    if post:
        post["uploaded_before"] = time_ago(post["upload_date"])
    result["random_post"] = post

    # ----------------------
    # 랜덤 숏츠 (Videos 테이블에서 type_name='shorts')
    cur.execute("""
        SELECT
            v.video_id AS short_id,
            v.thumbnail_url AS short_thumbnail,
            CASE
                WHEN CHAR_LENGTH(v.title) > 12 THEN CONCAT(LEFT(v.title, 12), '…')
                ELSE v.title
            END AS short_title,
            v.view_count AS views,
            u.username,
            u.profile_img
        FROM Videos v
        JOIN Users u ON v.user_id = u.user_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE vt.type_name = 'shorts'
          AND v.visibility = 'public'
        ORDER BY RAND()
        LIMIT 6;
    """)
    result["random_shorts"] = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify(result)

