from flask import Blueprint, jsonify
from db import get_db
import datetime

home_bp = Blueprint("home", __name__)

# DB 연결은 프로젝트의 `db.get_db()`를 사용합니다.
def get_conn():
    """호출 호환성을 위해 `db.get_db()`를 감싼 래퍼.

    기존 코드가 `get_conn()`을 사용하므로 내부적으로 `get_db()`를 호출합니다.
    """
    return get_db()

# -----------------------------
# 상대시간 계산 함수
# -----------------------------
def time_ago(d):
    now = datetime.datetime.now()
    delta = now - d

    if delta.days < 1:
        return "오늘"
    elif delta.days < 30:
        return f"{delta.days}일 전"
    elif delta.days < 365:
        return f"{delta.days // 30}개월 전"
    else:
        return f"{delta.days // 365}년 전"

# ============================================================
# 1) 시간대 기반 추천
# ============================================================
@home_bp.route("/home/time", methods=["GET"])
def home_time():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
            V.video_id,
            V.title,
            V.category,
            V.views,
            V.upload_date,
            U.user_id,
            U.name AS uploader_name,
            U.profile_image,
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
    cur.close()
    conn.close()

    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])

    return jsonify(rows)

# ============================================================
# 2) 최근 본 영상 5개
# ============================================================
@home_bp.route("/watch/recent", methods=["GET"])
def recent_watch():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
            wh.watched_at,
            v.video_id,
            v.title,
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000 THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date,
            u.user_id AS creator_id,
            u.name AS creator_name,
            u.profile_image AS creator_profile_image
        FROM WatchHistory wh
        JOIN Videos v ON wh.video_id = v.video_id
        JOIN Users u ON v.user_id = u.user_id
        WHERE wh.user_id = 1
        ORDER BY wh.watched_at DESC
        LIMIT 5;
    """

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])

    return jsonify(rows)

# ============================================================
# 3) 광고 추천
# ============================================================
@home_bp.route("/ads/recommend", methods=["GET"])
def ads_recommend():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT 
          topcat.category,
          CASE topcat.category
            WHEN '게임' THEN '🔥 요즘 뜨는 신작 게임 광고!'
            WHEN '음식' THEN '🍜 지금 가장 핫한 맛집 할인 광고!'
            WHEN 'IT' THEN '💻 최신 전자제품 신상 광고!'
            WHEN '지식' THEN '📘 똑똑해지는 지식 콘텐츠 광고!'
            WHEN '운동' THEN '🏋️ 헬스 용품 광고!'
            ELSE '📢 맞춤형 광고가 준비되어 있습니다!'
          END AS recommended_ad,
          CASE topcat.category
            WHEN '게임' THEN 'https://cdn.example.com/ad/game_banner.png'
            WHEN '음식' THEN 'https://cdn.example.com/ad/food_banner.jpg'
            WHEN 'IT' THEN 'https://cdn.example.com/ad/tech_banner.png'
            WHEN '지식' THEN 'https://cdn.example.com/ad/knowledge_banner.jpg'
            WHEN '운동' THEN 'https://cdn.example.com/ad/workout_banner.png'
            ELSE 'https://cdn.example.com/ad/default_banner.png'
          END AS ad_image_url
        FROM (
            SELECT v.category
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = 1
              AND wh.watched_at >= NOW() - INTERVAL 7 DAY
            GROUP BY v.category
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) AS topcat;
    """

    cur.execute(query)
    row = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify(row)

# ============================================================
# 4) 크리에이터 TOP2 → 조회수 TOP4
# ============================================================
@home_bp.route("/creators/top", methods=["GET"])
def top_creators():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    query = """
        WITH top_creators AS (
            SELECT v.user_id AS creator_id
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = 1
            GROUP BY v.user_id
            ORDER BY COUNT(*) DESC
            LIMIT 2
        )
        SELECT 
            v.video_id,
            v.user_id AS creator_id,
            u.name AS creator_name,
            u.profile_image AS creator_profile_image,
            v.title,
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000 THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date
        FROM Videos v
        JOIN top_creators tc ON v.user_id = tc.creator_id
        JOIN Users u ON v.user_id = u.user_id
        ORDER BY v.views DESC
        LIMIT 4;
    """

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])

    return jsonify(rows)

# ============================================================
# 5) 랜덤 게시물 + 댓글 1개
# ============================================================
@home_bp.route("/post/random", methods=["GET"])
def post_random():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    # 게시물 1개 랜덤 선택
    query_post = """
        SELECT 
            p.video_id AS post_id,
            p.title,
            p.description AS post_text,
            p.upload_date,
            u.name AS author_name,
            u.profile_image AS author_profile_url
        FROM Videos p
        JOIN Users u ON p.user_id = u.user_id
        WHERE p.category = '게시물'
        ORDER BY RAND()
        LIMIT 1;
    """
    cur.execute(query_post)
    post = cur.fetchone()

    if post:
        post["uploaded_before"] = time_ago(post["upload_date"])

        # ---- 댓글 TOP 1 ----
        query_comment = """
            SELECT 
                v2.description AS comment_text,
                v2.views AS likes,
                u2.name AS commenter_name,
                u2.profile_image AS commenter_profile
            FROM Videos v2
            JOIN Users u2 ON v2.user_id = u2.user_id
            WHERE v2.category = '댓글'
              AND v2.description LIKE CONCAT('parent=', %s, '%')
            ORDER BY v2.views DESC
            LIMIT 1;
        """
        cur.execute(query_comment, (post["post_id"],))
        post["top_comment"] = cur.fetchone()

    cur.close()
    conn.close()

    return jsonify(post)

# ============================================================
# 6) 랜덤 숏츠
# ============================================================
@home_bp.route("/shorts/random", methods=["GET"])
def shorts_random():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT
            s.short_id,
            s.thumbnail_url,
            CASE
                WHEN CHAR_LENGTH(s.title) > 12 THEN CONCAT(LEFT(s.title, 12), '…')
                ELSE s.title
            END AS short_title
        FROM Shorts s
        ORDER BY RAND()
        LIMIT 6;
    """

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(rows)

# ============================================================
# 7) 홈뷰 풀 세트
# ============================================================
@home_bp.route("/home/full", methods=["GET"])
def home_full():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    result = {}

    # ----------------------
    # 시간대 기반 추천
    cur.execute("""
        SELECT 
            V.video_id, V.title, V.category, V.views, V.upload_date,
            U.user_id, U.name AS uploader_name, U.profile_image,
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
    # 최근 본 영상
    cur.execute("""
        SELECT 
            wh.watched_at,
            v.video_id,
            v.title,
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000 THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date,
            u.user_id AS creator_id,
            u.name AS creator_name,
            u.profile_image AS creator_profile_image
        FROM WatchHistory wh
        JOIN Videos v ON wh.video_id = v.video_id
        JOIN Users u ON v.user_id = u.user_id
        WHERE wh.user_id = 1
        ORDER BY wh.watched_at DESC
        LIMIT 5;
    """)
    rows = cur.fetchall()
    for r in rows:
        r["uploaded_before"] = time_ago(r["upload_date"])
    result["recent_watched"] = rows

    # ----------------------
    # 광고
    cur.execute("""
        SELECT 
          topcat.category,
          CASE topcat.category
            WHEN '게임' THEN '🔥 요즘 뜨는 신작 게임 광고!'
            WHEN '음식' THEN '🍜 지금 가장 핫한 맛집 할인 광고!'
            WHEN 'IT' THEN '💻 최신 전자제품 신상 광고!'
            WHEN '지식' THEN '📘 똑똑해지는 지식 콘텐츠 광고!'
            WHEN '운동' THEN '🏋️ 헬스 용품 광고!'
            ELSE '📢 맞춤형 광고가 준비되어 있습니다!'
          END AS recommended_ad,
          CASE topcat.category
            WHEN '게임' THEN 'https://cdn.example.com/ad/game_banner.png'
            WHEN '음식' THEN 'https://cdn.example.com/ad/food_banner.jpg'
            WHEN 'IT' THEN 'https://cdn.example.com/ad/tech_banner.png'
            WHEN '지식' THEN 'https://cdn.example.com/ad/knowledge_banner.jpg'
            WHEN '운동' THEN 'https://cdn.example.com/ad/workout_banner.png'
            ELSE 'https://cdn.example.com/ad/default_banner.png'
          END AS ad_image_url
        FROM (
            SELECT v.category
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = 1
              AND wh.watched_at >= NOW() - INTERVAL 7 DAY
            GROUP BY v.category
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) AS topcat;
    """)
    result["ads"] = cur.fetchone()

    # ----------------------
    # TOP2 → 조회수 TOP4
    cur.execute("""
        WITH top_creators AS (
            SELECT v.user_id AS creator_id
            FROM WatchHistory wh
            JOIN Videos v ON wh.video_id = v.video_id
            WHERE wh.user_id = 1
            GROUP BY v.user_id
            ORDER BY COUNT(*) DESC
            LIMIT 2
        )
        SELECT 
            v.video_id,
            v.user_id AS creator_id,
            u.name AS creator_name,
            u.profile_image AS creator_profile_image,
            v.title,
            v.category,
            CASE
                WHEN v.views >= 100000000 THEN CONCAT(ROUND(v.views / 100000000, 1), '억')
                WHEN v.views >= 10000 THEN CONCAT(ROUND(v.views / 10000, 1), '만')
                ELSE v.views
            END AS pretty_views,
            v.views AS raw_views,
            v.upload_date
        FROM Videos v
        JOIN top_creators tc ON v.user_id = tc.creator_id
        JOIN Users u ON v.user_id = u.user_id
        ORDER BY v.views DESC
        LIMIT 4;
    """)
    result["top_creators"] = cur.fetchall()

    # ----------------------
    # 랜덤 게시물
    cur.execute("""
        SELECT 
            p.video_id AS post_id,
            p.title,
            p.description AS post_text,
            p.upload_date,
            u.name AS author_name,
            u.profile_image AS author_profile_url
        FROM Videos p
        JOIN Users u ON p.user_id = u.user_id
        WHERE p.category = '게시물'
        ORDER BY RAND()
        LIMIT 1;
    """)
    post = cur.fetchone()
    if post:
        post["uploaded_before"] = time_ago(post["upload_date"])

        # 댓글 TOP 1
        cur.execute("""
            SELECT 
                v2.description AS comment_text,
                v2.views AS likes,
                u2.name AS commenter_name,
                u2.profile_image AS commenter_profile
            FROM Videos v2
            JOIN Users u2 ON v2.user_id = u2.user_id
            WHERE v2.category = '댓글'
              AND v2.description LIKE CONCAT('parent=', %s, '%')
            ORDER BY v2.views DESC
            LIMIT 1;
        """, (post["post_id"],))
        post["top_comment"] = cur.fetchone()

    result["random_post"] = post

    # ----------------------
    # 랜덤 숏츠
    cur.execute("""
        SELECT
            s.short_id,
            s.thumbnail_url,
            CASE
                WHEN CHAR_LENGTH(s.title) > 12 THEN CONCAT(LEFT(s.title, 12), '…')
                ELSE s.title
            END AS short_title
        FROM Shorts s
        ORDER BY RAND()
        LIMIT 6;
    """)
    result["random_shorts"] = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(result)
