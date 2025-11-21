-- ===========================================
-- Unified YouTube Schema (FINAL, no VIEW)
--  - T_* 스키마 완전 흡수/정규화                                                          
-- ===========================================
DROP DATABASE IF EXISTS youtube_homeview;
CREATE DATABASE youtube_homeview
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE youtube_homeview;

-- 0) Lookup: VideoType (동영상/Shorts/라이브)
CREATE TABLE VideoType (
  type_id   TINYINT AUTO_INCREMENT PRIMARY KEY,
  type_code VARCHAR(20) NOT NULL UNIQUE,   -- 'video','shorts','live'
  type_name VARCHAR(40) NOT NULL
) ENGINE=InnoDB;

INSERT INTO VideoType (type_code, type_name)
VALUES ('video','동영상'),('shorts','Shorts'),('live','라이브');

-- 1) Users  (= T_account)
CREATE TABLE Users (
  user_id     INT AUTO_INCREMENT PRIMARY KEY,      -- = T_account.account_id
  username    VARCHAR(50) NOT NULL,
  handle      VARCHAR(50) UNIQUE,
  email       VARCHAR(100) UNIQUE,
  profile_img VARCHAR(200) DEFAULT 'https://cdn.example.com/default.png' ,
  join_date   DATE                                  -- T_account.join_date는 DATE였음
) ENGINE=InnoDB;

-- 2) Videos  (= T_myvideo)
CREATE TABLE Videos (
  video_id      INT AUTO_INCREMENT PRIMARY KEY,     -- = T_myvideo.video_id
  user_id       INT NOT NULL,                       -- = T_myvideo.account_id
  title         VARCHAR(150) NOT NULL,
  description   TEXT,
  category      VARCHAR(50),                        -- 주제 카테고리(자유 텍스트)
  type_id       TINYINT NOT NULL,                   -- ('video','shorts','live') → T_myvideo.category를 매핑
  visibility    ENUM('public','unlisted','private') DEFAULT 'public',
  duration      TIME NULL,                          -- = T_myvideo.duration
  thumbnail_url VARCHAR(200),
  copyright     BOOLEAN DEFAULT FALSE,
  views         INT DEFAULT 0,
  upload_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- = T_myvideo.upload_date
  CONSTRAINT fk_videos_user   FOREIGN KEY (user_id)  REFERENCES Users(user_id),
  CONSTRAINT fk_videos_vtype  FOREIGN KEY (type_id)  REFERENCES VideoType(type_id),
  INDEX (user_id), INDEX (type_id), INDEX (upload_date), INDEX (views)
) ENGINE=InnoDB;

-- 3) VideoStats  (= T_myvideo_stats)
CREATE TABLE VideoStats (
  stat_id       INT AUTO_INCREMENT PRIMARY KEY,
  video_id      INT NOT NULL,
  view_count    INT DEFAULT 0,
  like_count    INT DEFAULT 0,
  comment_count INT DEFAULT 0,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_vstats_video FOREIGN KEY (video_id) REFERENCES Videos(video_id),
  UNIQUE KEY uk_vstats_video (video_id)
) ENGINE=InnoDB;

-- 4) Subscriptions (사용자↔채널 M:N)
CREATE TABLE Subscriptions (
  sub_id        INT AUTO_INCREMENT PRIMARY KEY,
  subscriber_id INT NOT NULL,
  channel_id    INT NOT NULL,
  subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_sub_subscriber FOREIGN KEY (subscriber_id) REFERENCES Users(user_id),
  CONSTRAINT fk_sub_channel   FOREIGN KEY (channel_id)   REFERENCES Users(user_id),
  UNIQUE KEY uk_sub (subscriber_id, channel_id),
  INDEX (subscriber_id), INDEX (channel_id)
) ENGINE=InnoDB;

-- 5) WatchHistory (= T_history)
CREATE TABLE WatchHistory (
  history_id       INT AUTO_INCREMENT PRIMARY KEY,   -- = T_history.history_id
  user_id          INT NOT NULL,                     -- = T_history.account_id
  video_id         INT NOT NULL,
  watched_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- = T_history.watched_time
  duration_watched TIME NULL,                        -- = T_history.duration_watched
  device_type      VARCHAR(30),                      -- = T_history.device_type
  CONSTRAINT fk_wh_user  FOREIGN KEY (user_id)  REFERENCES Users(user_id),
  CONSTRAINT fk_wh_video FOREIGN KEY (video_id) REFERENCES Videos(video_id),
  INDEX (user_id, watched_at), INDEX (video_id)
) ENGINE=InnoDB;

-- 6) Premium (= T_premium)
CREATE TABLE Premium (
  premium_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,             -- = T_premium.account_id
  join_date  DATE,
  plan_type  VARCHAR(30),
  is_active  BOOLEAN DEFAULT TRUE,
  CONSTRAINT fk_prem_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  UNIQUE KEY uk_prem_active (user_id, is_active)
) ENGINE=InnoDB;

-- 7) PremiumUsage (= T_premium_usage)
CREATE TABLE PremiumUsage (
  usage_id     INT AUTO_INCREMENT PRIMARY KEY,
  premium_id   INT NOT NULL,
  benefit_type VARCHAR(50),
  usage_value  INT,
  last_updated TIMESTAMP,
  CONSTRAINT fk_pu_prem FOREIGN KEY (premium_id) REFERENCES Premium(premium_id),
  INDEX (premium_id)
) ENGINE=InnoDB;

-- 8) OfflineVideo (= T_offline_video)
CREATE TABLE OfflineVideo (
  offline_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,            -- = T_offline_video.account_id
  video_id     INT NOT NULL,
  save_date    TIMESTAMP,
  file_size_mb DECIMAL(6,2),
  quality      VARCHAR(20) DEFAULT '720p',
  storage_type VARCHAR(30) DEFAULT 'smart',
  is_updated   BOOLEAN DEFAULT FALSE,
  CONSTRAINT fk_ov_user  FOREIGN KEY (user_id)  REFERENCES Users(user_id),
  CONSTRAINT fk_ov_video FOREIGN KEY (video_id) REFERENCES Videos(video_id),
  UNIQUE KEY uk_offline (user_id, video_id),
  INDEX (user_id), INDEX (video_id)
) ENGINE=InnoDB;

-- 9) Movie (= T_movie)
CREATE TABLE Movie (
  movie_id      INT AUTO_INCREMENT PRIMARY KEY,
  title         VARCHAR(150),
  genre         VARCHAR(50),
  release_year  INT,
  duration      TIME,
  rating_label  VARCHAR(50),
  thumbnail_url VARCHAR(200),
  description   TEXT
) ENGINE=InnoDB;

-- 10) MoviePurchase (= T_movie_purchase)
CREATE TABLE MoviePurchase (
  purchase_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,          -- = T_movie_purchase.account_id
  movie_id      INT NOT NULL,
  purchase_type VARCHAR(20),
  purchase_date TIMESTAMP,
  expire_date   TIMESTAMP,
  price         DECIMAL(8,2),
  CONSTRAINT fk_mp_user  FOREIGN KEY (user_id)  REFERENCES Users(user_id),
  CONSTRAINT fk_mp_movie FOREIGN KEY (movie_id) REFERENCES Movie(movie_id),
  INDEX (user_id), INDEX (movie_id)
) ENGINE=InnoDB;

-- 11) WatchTime (= T_watchtime)
CREATE TABLE WatchTime (
  watchtime_id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id            INT NOT NULL,        -- = T_watchtime.account_id
  avg_daily_minutes  INT,
  total_week_minutes INT,
  compare_last_week  INT,                 -- %
  updated_at         TIMESTAMP,
  CONSTRAINT fk_wt_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  UNIQUE KEY uk_wt_user (user_id)
) ENGINE=InnoDB;

-- 12) Support (= T_support)
CREATE TABLE Support (
  support_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,               -- = T_support.account_id
  category   VARCHAR(50),
  message    TEXT,
  status     VARCHAR(20) DEFAULT 'open',
  created_at TIMESTAMP,
  CONSTRAINT fk_sup_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  INDEX (user_id), INDEX (status)
) ENGINE=InnoDB;
