DROP DATABASE IF EXISTS youtube_app;
CREATE DATABASE youtube_app
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE youtube_app;

-- ==========================================
-- 1. 공통 코드 및 사용자 (Base Tables)
-- ==========================================

-- 1) VideoType: 영상의 종류를 구분하는 기준 테이블
CREATE TABLE VideoType (
  type_id   TINYINT AUTO_INCREMENT PRIMARY KEY,
  type_name VARCHAR(20) NOT NULL -- 'video', 'shorts', 'live'
);

INSERT INTO VideoType (type_name) VALUES ('video'), ('shorts'), ('live');

-- 2) Users: 모든 사용자 및 채널 정보
CREATE TABLE Users (
  user_id          INT AUTO_INCREMENT PRIMARY KEY,
  username         VARCHAR(50) NOT NULL,
  handle           VARCHAR(50) UNIQUE, -- @handle
  email            VARCHAR(100) UNIQUE,
  profile_img      VARCHAR(255) DEFAULT 'https://cdn.example.com/default.png',
  subscriber_count INT DEFAULT 0, -- [반정규화] 구독자 수 캐싱
  join_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3) BlockList: 차단한 사용자 목록 (기존 Channel_Block)
CREATE TABLE BlockList (
  user_id         INT NOT NULL, -- 나
  blocked_user_id INT NOT NULL, -- 차단한 사람
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (user_id, blocked_user_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (blocked_user_id) REFERENCES Users(user_id),
  CHECK (user_id != blocked_user_id)
);

-- ==========================================
-- 2. 핵심 콘텐츠 (Content - Unified)
-- ==========================================

-- 4) Videos: 일반 영상 + 쇼츠 통합
CREATE TABLE Videos (
  video_id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  type_id       TINYINT NOT NULL, -- 1:동영상, 2:쇼츠
  title         VARCHAR(150) NOT NULL,
  description   TEXT,
  video_url     VARCHAR(255) NOT NULL,
  thumbnail_url VARCHAR(255),
  duration      INT, -- 초(seconds) 단위
  visibility    ENUM('public','unlisted','private') DEFAULT 'public',
  
  -- [반정규화] 통계 데이터 캐싱
  view_count    INT DEFAULT 0,
  like_count    INT DEFAULT 0,
  comment_count INT DEFAULT 0,
  
  upload_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (type_id) REFERENCES VideoType(type_id),
  INDEX idx_user (user_id),
  INDEX idx_type_date (type_id, upload_date DESC)
);

-- ==========================================
-- 3. 상호작용 (Interactions - Unified)
-- ==========================================

-- 5) Comments: 일반 영상과 쇼츠 댓글 통합
CREATE TABLE Comments (
  comment_id INT AUTO_INCREMENT PRIMARY KEY,
  video_id   INT NOT NULL,
  user_id    INT NOT NULL,
  content    TEXT NOT NULL,
  parent_id  INT DEFAULT NULL, -- 대댓글용
  like_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (video_id) REFERENCES Videos(video_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (parent_id) REFERENCES Comments(comment_id),
  INDEX idx_video (video_id)
);

-- 6) VideoLikes: 영상(일반/쇼츠) 좋아요 통합
CREATE TABLE VideoLikes (
  user_id    INT NOT NULL,
  video_id   INT NOT NULL,
  is_dislike BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (user_id, video_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (video_id) REFERENCES Videos(video_id)
);

-- 7) CommentLikes: 댓글 좋아요
CREATE TABLE CommentLikes (
  user_id    INT NOT NULL,
  comment_id INT NOT NULL,
  is_dislike BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (user_id, comment_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (comment_id) REFERENCES Comments(comment_id)
);

-- 8) Subscriptions: 구독 관계
CREATE TABLE Subscriptions (
  subscriber_id INT NOT NULL,
  channel_id    INT NOT NULL,
  alert_enabled BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (subscriber_id, channel_id),
  FOREIGN KEY (subscriber_id) REFERENCES Users(user_id),
  FOREIGN KEY (channel_id) REFERENCES Users(user_id),
  INDEX idx_subscriber (subscriber_id)
);

-- 9) Reports: 신고 통합 (Shorts_Report 등 통합)
-- 빠져있던 신고 기능을 추가했습니다.
CREATE TABLE Reports (
  report_id     INT AUTO_INCREMENT PRIMARY KEY,
  reporter_id   INT NOT NULL,
  target_type   ENUM('video', 'comment', 'user') NOT NULL,
  target_id     INT NOT NULL, 
  reason        ENUM('spam', 'violence', 'copyright', 'other') DEFAULT 'other',
  description   TEXT,
  status        ENUM('pending', 'resolved') DEFAULT 'pending',
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (reporter_id) REFERENCES Users(user_id)
);

-- ==========================================
-- 4. 사용자 기록 (History & Library)
-- ==========================================

-- 10) WatchHistory: 시청 기록 (통합)
CREATE TABLE WatchHistory (
  history_id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id          INT NOT NULL,
  video_id         INT NOT NULL,
  last_position    INT DEFAULT 0, -- 초 단위
  is_finished      BOOLEAN DEFAULT FALSE,
  watched_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (video_id) REFERENCES Videos(video_id),
  UNIQUE KEY uk_history (user_id, video_id)
);

-- 11) Playlists: 재생목록 (통합)
CREATE TABLE Playlists (
  playlist_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  title       VARCHAR(100) NOT NULL,
  is_public   BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- 12) PlaylistItems: 재생목록 아이템 (통합)
CREATE TABLE PlaylistItems (
  playlist_id INT NOT NULL,
  video_id    INT NOT NULL,
  position    INT NOT NULL,
  added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (playlist_id, video_id),
  FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id),
  FOREIGN KEY (video_id) REFERENCES Videos(video_id)
);

-- 13) OfflineVideo: 오프라인 저장
CREATE TABLE OfflineVideo (
  user_id      INT NOT NULL,
  video_id     INT NOT NULL,
  file_path    VARCHAR(255),
  expired_at   TIMESTAMP,
  saved_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (user_id, video_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (video_id) REFERENCES Videos(video_id)
);

-- 14) WatchTime: 시청 시간 통계 (MyPage용)
CREATE TABLE WatchTime (
  watchtime_id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id            INT NOT NULL,
  avg_daily_minutes  INT,
  total_week_minutes INT,
  compare_last_week  INT, -- 전주 대비 증감
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_wt_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  UNIQUE KEY uk_wt_user (user_id)
);

-- ==========================================
-- 5. 비즈니스 & 기타 (Business & Support)
-- ==========================================

-- 15) Premium: 프리미엄 멤버십 (PremiumUsage는 로그성이라 제외해도 무방)
CREATE TABLE Premium (
  user_id    INT PRIMARY KEY,
  plan_type  ENUM('individual', 'family') DEFAULT 'individual',
  start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  end_date   TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- 16) SupportTickets: 고객센터 + 피드백 통합 (Support, Feedback 통합)
CREATE TABLE SupportTickets (
  ticket_id     INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  type          ENUM('bug', 'feature', 'account', 'other') DEFAULT 'other',
  subject       VARCHAR(100),
  message       TEXT NOT NULL,
  status        ENUM('open', 'in_progress', 'closed') DEFAULT 'open',
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- 17) Movies: 영화 (Videos와 별도 관리)
-- 테이블명을 단수(Movie)에서 복수(Movies)로 통일했습니다.
CREATE TABLE Movies (
  movie_id      INT AUTO_INCREMENT PRIMARY KEY,
  title         VARCHAR(150) NOT NULL,
  description   TEXT,
  price         DECIMAL(10, 2),
  duration      INT,
  release_year  INT,
  thumbnail_url VARCHAR(255)
);

-- 18) MoviePurchases: 영화 구매 내역
CREATE TABLE MoviePurchases (
  purchase_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  movie_id      INT NOT NULL,
  type          ENUM('buy', 'rent') NOT NULL,
  price_paid    DECIMAL(10, 2),
  expired_at    TIMESTAMP NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (movie_id) REFERENCES Movies(movie_id)
);