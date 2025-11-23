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
            V.category,
            V.views,
            V.upload_date,
            U.user_id,
            U.username AS uploader_name,   -- name → username
            U.profile_img,                 -- profile_image → profile_img
            CASE 
                WHEN HOUR(NOW()) BETWEEN 18 AND 23 AND V.category = '게임' THEN 10
                WHEN HOUR(NOW()) BETWEEN 6 AND 17 AND V.category = '뉴스' THEN 10
                ELSE 1
            END AS category_weight
        FROM Videos V
        JOIN Users U ON U.user_id = V.user_id
        ORDER BY (V.views * category_weight) DESC, V.upload_date DESC
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
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000       THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date,
            u.user_id AS creator_id,
            u.username AS creator_name,              -- name → username
            u.profile_img AS creator_profile_image   -- profile_image → profile_img
        FROM WatchHistory wh
        JOIN Videos v ON wh.video_id = v.video_id
        JOIN Users u  ON v.user_id  = u.user_id
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
# 3) 광고 추천
# ==================================================
@home_bp.route("/ads/recommend", methods=["GET"])
def ads_recommend():
    user_id = request.args.get("user_id", 1)  # 기본값 1
    
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
          COALESCE(topcat.category, 'General') AS category,
          CASE COALESCE(topcat.category, 'General')
            WHEN '게임' THEN '🔥 요즘 뜨는 신작 게임 광고!'
            WHEN '음식' THEN '🍜 지금 가장 핫한 맛집 할인 광고!'
            WHEN 'IT'   THEN '💻 최신 전자제품 신상 광고!'
            WHEN '지식' THEN '📘 똑똑해지는 지식 콘텐츠 광고!'
            WHEN '운동' THEN '🏋️ 헬스 용품 광고!'
            ELSE '📢 맞춤형 광고가 준비되어 있습니다!'
          END AS recommended_ad,
          CASE COALESCE(topcat.category, 'General')
            WHEN '게임' THEN 'https://cdn.example.com/ad/game_banner.png'
            WHEN '음식' THEN 'https://cdn.example.com/ad/food_banner.jpg'
            WHEN 'IT'   THEN 'https://cdn.example.com/ad/tech_banner.png'
            WHEN '지식' THEN 'https://cdn.example.com/ad/knowledge_banner.jpg'
            WHEN '운동' THEN 'https://cdn.example.com/ad/workout_banner.png'
            ELSE 'https://cdn.example.com/ad/default_banner.png'
          END AS ad_image_url
        FROM (
            SELECT v.category
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = %s
              AND wh.watched_at >= NOW() - INTERVAL 7 DAY
            GROUP BY v.category
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) AS topcat
        UNION ALL
        SELECT 'General', '📢 맞춤형 광고가 준비되어 있습니다!', 'https://cdn.example.com/ad/default_banner.png'
        LIMIT 1;
    """

    cur.execute(query, (user_id,))
    row = cur.fetchone()

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
            u.username AS creator_name,              -- name → username
            u.profile_img AS creator_profile_image,  -- profile_image → profile_img
            v.title,
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000       THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date
        FROM Videos v
        JOIN top_creators tc ON v.user_id = tc.creator_id
        JOIN Users u         ON v.user_id = u.user_id
        ORDER BY v.views DESC
        LIMIT 4;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify(rows)


# ==================================================
# 5) 랜덤 게시물 + 댓글 1개
# ==================================================
@home_bp.route("/post/random", methods=["GET"])
def post_random():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Videos 테이블에서 일반 영상 1개 랜덤 선택 (type_code='video')
    query_post = """
        SELECT 
            v.video_id AS post_id,
            v.title,
            v.description AS post_text,
            v.upload_date,
            v.views,
            u.username AS author_name,
            u.profile_img AS author_profile_url
        FROM Videos v
        JOIN Users u ON v.user_id = u.user_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE vt.type_code = 'video'
          AND v.visibility = 'public'
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
    post["top_comment"] = None  # 댓글은 별도 테이블이 없으므로 null

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

    # Shorts 테이블에서 랜덤 쇼츠 조회
    query = """
        SELECT
            s.shorts_id AS short_id,
            s.thumbnail_url,
            CASE
                WHEN CHAR_LENGTH(s.title) > 12 THEN CONCAT(LEFT(s.title, 12), '…')
                ELSE s.title
            END AS short_title,
            s.views,
            u.username,
            u.profile_img
        FROM Shorts s
        JOIN Users u ON s.user_id = u.user_id
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
            V.category,
            V.views,
            V.upload_date,
            U.user_id,
            U.username AS uploader_name,
            U.profile_img,
            CASE 
                WHEN HOUR(NOW()) BETWEEN 18 AND 23 AND V.category = '게임' THEN 10
                WHEN HOUR(NOW()) BETWEEN 6 AND 17 AND V.category = '뉴스' THEN 10
                ELSE 1
            END AS category_weight
        FROM Videos V
        JOIN Users U ON U.user_id = V.user_id
        ORDER BY (V.views * category_weight) DESC, V.upload_date DESC
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
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000       THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date,
            u.user_id AS creator_id,
            u.username AS creator_name,
            u.profile_img AS creator_profile_image
        FROM WatchHistory wh
        JOIN Videos v ON wh.video_id = v.video_id
        JOIN Users u  ON v.user_id  = u.user_id
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
    # 광고
    query = """
        SELECT 
          COALESCE(topcat.category, 'General') AS category,
          CASE COALESCE(topcat.category, 'General')
            WHEN '게임' THEN '🔥 요즘 뜨는 신작 게임 광고!'
            WHEN '음식' THEN '🍜 지금 가장 핫한 맛집 할인 광고!'
            WHEN 'IT'   THEN '💻 최신 전자제품 신상 광고!'
            WHEN '지식' THEN '📘 똑똑해지는 지식 콘텐츠 광고!'
            WHEN '운동' THEN '🏋️ 헬스 용품 광고!'
            ELSE '📢 맞춤형 광고가 준비되어 있습니다!'
          END AS recommended_ad,
          CASE COALESCE(topcat.category, 'General')
            WHEN '게임' THEN 'https://cdn.example.com/ad/game_banner.png'
            WHEN '음식' THEN 'https://cdn.example.com/ad/food_banner.jpg'
            WHEN 'IT'   THEN 'https://cdn.example.com/ad/tech_banner.png'
            WHEN '지식' THEN 'https://cdn.example.com/ad/knowledge_banner.jpg'
            WHEN '운동' THEN 'https://cdn.example.com/ad/workout_banner.png'
            ELSE 'https://cdn.example.com/ad/default_banner.png'
          END AS ad_image_url
        FROM (
            SELECT v.category
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = %s
              AND wh.watched_at >= NOW() - INTERVAL 7 DAY
            GROUP BY v.category
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) AS topcat
        UNION ALL
        SELECT 'General', '📢 맞춤형 광고가 준비되어 있습니다!', 'https://cdn.example.com/ad/default_banner.png'
        LIMIT 1;
    """
    cur.execute(query, (user_id,))
    result["ads"] = cur.fetchone()

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
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000       THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date
        FROM Videos v
        JOIN top_creators tc ON v.user_id = tc.creator_id
        JOIN Users u         ON v.user_id = u.user_id
        ORDER BY v.views DESC
        LIMIT 4;
    """
    cur.execute(query, (user_id,))
    result["top_creators"] = cur.fetchall()

    # ----------------------
    # 랜덤 영상 (type_code='video')
    cur.execute("""
        SELECT 
            v.video_id AS post_id,
            v.title,
            v.description AS post_text,
            v.upload_date,
            v.views,
            u.username AS author_name,
            u.profile_img AS author_profile_url
        FROM Videos v
        JOIN Users u ON v.user_id = u.user_id
        JOIN VideoType vt ON v.type_id = vt.type_id
        WHERE vt.type_code = 'video'
          AND v.visibility = 'public'
        ORDER BY RAND()
        LIMIT 1;
    """)
    post = cur.fetchone()
    if post:
        post["uploaded_before"] = time_ago(post["upload_date"])
        post["top_comment"] = None
    result["random_post"] = post

    # ----------------------
    # 랜덤 숏츠 (Shorts 테이블)
    cur.execute("""
        SELECT
            s.shorts_id AS short_id,
            s.thumbnail_url,
            CASE
                WHEN CHAR_LENGTH(s.title) > 12 THEN CONCAT(LEFT(s.title, 12), '…')
                ELSE s.title
            END AS short_title,
            s.views,
            u.username,
            u.profile_img
        FROM Shorts s
        JOIN Users u ON s.user_id = u.user_id
        ORDER BY RAND()
        LIMIT 6;
    """)
    result["random_shorts"] = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify(result)

