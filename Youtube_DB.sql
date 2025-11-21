-- Unified merged schema for DB_TP (DB_TP.sql + homeview.sql + shortsview.sql)
-- Purpose: provide a single canonical schema that matches the project's API usage.

DROP DATABASE IF EXISTS youtube_homeview;
CREATE DATABASE youtube_homeview
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE youtube_homeview;

-- 0) Lookup: VideoType
CREATE TABLE VideoType (
  type_id   TINYINT AUTO_INCREMENT PRIMARY KEY,
  type_code VARCHAR(20) NOT NULL UNIQUE,
  type_name VARCHAR(40) NOT NULL
) ENGINE=InnoDB;

INSERT INTO VideoType (type_code, type_name)
VALUES ('video','동영상'),('shorts','Shorts'),('live','라이브');

-- 1) Users
CREATE TABLE Users (
  user_id     INT AUTO_INCREMENT PRIMARY KEY,
  username    VARCHAR(50) NOT NULL,
  handle      VARCHAR(50) UNIQUE,
  email       VARCHAR(100) UNIQUE,
  profile_img VARCHAR(200) DEFAULT 'https://cdn.example.com/default.png',
  join_date   DATE,
  -- legacy compatibility (some older queries might reference `name` or `profile_image`)
  name        VARCHAR(50) GENERATED ALWAYS AS (username) VIRTUAL,
  profile_image VARCHAR(200) GENERATED ALWAYS AS (profile_img) VIRTUAL
) ENGINE=InnoDB;

-- 2) Videos
CREATE TABLE Videos (
  video_id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  title         VARCHAR(150) NOT NULL,
  description   TEXT,
  category      VARCHAR(50),
  type_id       TINYINT NOT NULL,
  visibility    ENUM('public','unlisted','private') DEFAULT 'public',
  duration      TIME NULL,
  thumbnail_url VARCHAR(200),
  copyright     BOOLEAN DEFAULT FALSE,
  views         INT DEFAULT 0,
  upload_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_videos_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  CONSTRAINT fk_videos_vtype FOREIGN KEY (type_id) REFERENCES VideoType(type_id),
  INDEX (user_id), INDEX (type_id), INDEX (upload_date), INDEX (views)
) ENGINE=InnoDB;

-- 3) VideoStats
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

-- 4) Subscriptions
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

-- 5) WatchHistory
CREATE TABLE WatchHistory (
  history_id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id          INT NOT NULL,
  video_id         INT NOT NULL,
  watched_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  duration_watched TIME NULL,
  device_type      VARCHAR(30),
  CONSTRAINT fk_wh_user  FOREIGN KEY (user_id)  REFERENCES Users(user_id),
  CONSTRAINT fk_wh_video FOREIGN KEY (video_id) REFERENCES Videos(video_id),
  INDEX (user_id, watched_at), INDEX (video_id)
) ENGINE=InnoDB;

-- 6) Premium
CREATE TABLE Premium (
  premium_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  join_date  DATE,
  plan_type  VARCHAR(30),
  is_active  BOOLEAN DEFAULT TRUE,
  CONSTRAINT fk_prem_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  UNIQUE KEY uk_prem_active (user_id, is_active)
) ENGINE=InnoDB;

-- 7) PremiumUsage
CREATE TABLE PremiumUsage (
  usage_id     INT AUTO_INCREMENT PRIMARY KEY,
  premium_id   INT NOT NULL,
  benefit_type VARCHAR(50),
  usage_value  INT,
  last_updated TIMESTAMP,
  CONSTRAINT fk_pu_prem FOREIGN KEY (premium_id) REFERENCES Premium(premium_id),
  INDEX (premium_id)
) ENGINE=InnoDB;

-- 8) OfflineVideo
CREATE TABLE OfflineVideo (
  offline_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
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

-- 9) Movie
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

-- 10) MoviePurchase
CREATE TABLE MoviePurchase (
  purchase_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  movie_id      INT NOT NULL,
  purchase_type VARCHAR(20),
  purchase_date TIMESTAMP,
  expire_date   TIMESTAMP,
  price         DECIMAL(8,2),
  CONSTRAINT fk_mp_user  FOREIGN KEY (user_id)  REFERENCES Users(user_id),
  CONSTRAINT fk_mp_movie FOREIGN KEY (movie_id) REFERENCES Movie(movie_id),
  INDEX (user_id), INDEX (movie_id)
) ENGINE=InnoDB;

-- 11) WatchTime
CREATE TABLE WatchTime (
  watchtime_id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id            INT NOT NULL,
  avg_daily_minutes  INT,
  total_week_minutes INT,
  compare_last_week  INT,
  updated_at         TIMESTAMP,
  CONSTRAINT fk_wt_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  UNIQUE KEY uk_wt_user (user_id)
) ENGINE=InnoDB;

-- 12) Support
CREATE TABLE Support (
  support_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  category   VARCHAR(50),
  message    TEXT,
  status     VARCHAR(20) DEFAULT 'open',
  created_at TIMESTAMP,
  CONSTRAINT fk_sup_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  INDEX (user_id), INDEX (status)
) ENGINE=InnoDB;

-- 13) Playlists (canonical name)
CREATE TABLE Playlists (
  playlist_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  title       VARCHAR(150),
  visibility  ENUM('public','private') DEFAULT 'public',
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_playlist_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

-- 14) PlaylistVideo (mapping for Videos)
CREATE TABLE PlaylistVideo (
  playlist_id INT NOT NULL,
  video_id    INT NOT NULL,
  position    INT,
  PRIMARY KEY (playlist_id, video_id),
  CONSTRAINT fk_pv_playlist FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id),
  CONSTRAINT fk_pv_video FOREIGN KEY (video_id) REFERENCES Videos(video_id)
) ENGINE=InnoDB;

-- 15) Shorts and related tables (from shortsview.sql)
CREATE TABLE Shorts (
  shorts_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id   INT NOT NULL,
  title     VARCHAR(150) NOT NULL,
  video_url VARCHAR(255),
  thumbnail_url VARCHAR(255),
  duration_seconds INT,
  views INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_shorts_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  INDEX (user_id), INDEX (created_at), INDEX (views)
) ENGINE=InnoDB;

CREATE TABLE Shorts_Like (
  like_id INT AUTO_INCREMENT PRIMARY KEY,
  shorts_id INT NOT NULL,
  user_id INT NOT NULL,
  type ENUM('like','dislike') DEFAULT 'like',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_shorts_like (shorts_id, user_id),
  CONSTRAINT fk_shorts_like_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
  CONSTRAINT fk_shorts_like_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

CREATE TABLE Shorts_Comment (
  comment_id INT AUTO_INCREMENT PRIMARY KEY,
  shorts_id INT NOT NULL,
  user_id INT NOT NULL,
  parent_comment_id INT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_shorts_comment_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
  CONSTRAINT fk_shorts_comment_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  CONSTRAINT fk_shorts_comment_parent FOREIGN KEY (parent_comment_id) REFERENCES Shorts_Comment(comment_id)
) ENGINE=InnoDB;

CREATE TABLE Comment_Like (
  comment_like_id INT AUTO_INCREMENT PRIMARY KEY,
  comment_id INT NOT NULL,
  user_id INT NOT NULL,
  type ENUM('like','dislike') DEFAULT 'like',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(comment_id, user_id),
  CONSTRAINT fk_comment_like_comment FOREIGN KEY (comment_id) REFERENCES Shorts_Comment(comment_id),
  CONSTRAINT fk_comment_like_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

CREATE TABLE Shorts_Share (
  share_id INT AUTO_INCREMENT PRIMARY KEY,
  shorts_id INT NOT NULL,
  user_id INT NOT NULL,
  platform ENUM('link','gmail','message') DEFAULT 'link',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_shorts_share_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
  CONSTRAINT fk_shorts_share_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

CREATE TABLE Shorts_Remix (
  remix_id INT AUTO_INCREMENT PRIMARY KEY,
  original_shorts_id INT NOT NULL,
  remix_shorts_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_remix_pair (original_shorts_id, remix_shorts_id),
  CONSTRAINT fk_remix_original FOREIGN KEY (original_shorts_id) REFERENCES Shorts(shorts_id),
  CONSTRAINT fk_remix_remix FOREIGN KEY (remix_shorts_id) REFERENCES Shorts(shorts_id)
) ENGINE=InnoDB;

CREATE TABLE Shorts_ViewHistory (
  view_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  shorts_id INT NOT NULL,
  watched_seconds INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_view_user_shorts (user_id, shorts_id),
  CONSTRAINT fk_view_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  CONSTRAINT fk_view_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id)
) ENGINE=InnoDB;

CREATE TABLE Playlist_Short (
  id INT AUTO_INCREMENT PRIMARY KEY,
  playlist_id INT NOT NULL,
  shorts_id INT NOT NULL,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (playlist_id, shorts_id),
  CONSTRAINT fk_playlist_short_playlist FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id),
  CONSTRAINT fk_playlist_short_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id)
) ENGINE=InnoDB;

CREATE TABLE Shorts_NotInterested (
  id INT AUTO_INCREMENT PRIMARY KEY,
  shorts_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (shorts_id, user_id),
  CONSTRAINT fk_notinterested_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
  CONSTRAINT fk_notinterested_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

CREATE TABLE Channel_Block (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  blocked_user_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, blocked_user_id),
  CONSTRAINT fk_channel_block_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
  CONSTRAINT fk_channel_block_blocked FOREIGN KEY (blocked_user_id) REFERENCES Users(user_id),
  CHECK (user_id != blocked_user_id)
) ENGINE=InnoDB;

CREATE TABLE Shorts_Report (
  report_id INT AUTO_INCREMENT PRIMARY KEY,
  shorts_id INT NOT NULL,
  user_id INT NOT NULL,
  reason ENUM('spam','violence','copyright','other') DEFAULT 'other',
  detail TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_report_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
  CONSTRAINT fk_report_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

CREATE TABLE Feedback (
  feedback_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  message TEXT NOT NULL,
  category ENUM('bug','feature_request','feedback','other') DEFAULT 'feedback',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

-- End of merged schema
