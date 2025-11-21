DROP DATABASE IF EXISTS youtube_homeview;
CREATE DATABASE youtube_homeview
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE youtube_homeview;

-- 0) Lookup: VideoType (동영상/Shorts/라이브)
CREATE TABLE VideoType (
type_id TINYINT AUTO_INCREMENT PRIMARY KEY,
type_code VARCHAR(20) NOT NULL UNIQUE, -- 'video','shorts','live'
type_name VARCHAR(40) NOT NULL
) ENGINE=InnoDB;

INSERT INTO VideoType (type_code, type_name)
VALUES ('video','동영상'),('shorts','Shorts'),('live','라이브');

-- 1) Users
CREATE TABLE Users (
user_id INT AUTO_INCREMENT PRIMARY KEY,
username VARCHAR(50) NOT NULL,
handle VARCHAR(50) UNIQUE,
email VARCHAR(100) UNIQUE,
profile_img VARCHAR(200) DEFAULT 'https://cdn.example.com/default.png',
join_date DATE
) ENGINE=InnoDB;

-- 2) Videos
CREATE TABLE Videos (
video_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
title VARCHAR(150) NOT NULL,
description TEXT,
category VARCHAR(50),
type_id TINYINT NOT NULL,
visibility ENUM('public','unlisted','private') DEFAULT 'public',
duration TIME NULL,
thumbnail_url VARCHAR(200),
copyright BOOLEAN DEFAULT FALSE,
views INT DEFAULT 0,
upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_videos_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
CONSTRAINT fk_videos_vtype FOREIGN KEY (type_id) REFERENCES VideoType(type_id),
INDEX (user_id), INDEX (type_id), INDEX (upload_date), INDEX (views)
) ENGINE=InnoDB;

-- 3) VideoStats
CREATE TABLE VideoStats (
stat_id INT AUTO_INCREMENT PRIMARY KEY,
video_id INT NOT NULL,
view_count INT DEFAULT 0,
like_count INT DEFAULT 0,
comment_count INT DEFAULT 0,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
CONSTRAINT fk_vstats_video FOREIGN KEY (video_id) REFERENCES Videos(video_id),
UNIQUE KEY uk_vstats_video (video_id)
) ENGINE=InnoDB;

-- 4) Subscriptions
CREATE TABLE Subscriptions (
sub_id INT AUTO_INCREMENT PRIMARY KEY,
subscriber_id INT NOT NULL,
channel_id INT NOT NULL,
subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_sub_subscriber FOREIGN KEY (subscriber_id) REFERENCES Users(user_id),
CONSTRAINT fk_sub_channel FOREIGN KEY (channel_id) REFERENCES Users(user_id),
UNIQUE KEY uk_sub (subscriber_id, channel_id),
INDEX (subscriber_id), INDEX (channel_id)
) ENGINE=InnoDB;

-- 5) WatchHistory
CREATE TABLE WatchHistory (
history_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
video_id INT NOT NULL,
watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
duration_watched TIME NULL,
device_type VARCHAR(30),
CONSTRAINT fk_wh_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
CONSTRAINT fk_wh_video FOREIGN KEY (video_id) REFERENCES Videos(video_id),
INDEX (user_id, watched_at), INDEX (video_id)
) ENGINE=InnoDB;

-- 6) Premium
CREATE TABLE Premium (
premium_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
join_date DATE,
plan_type VARCHAR(30),
is_active BOOLEAN,
CONSTRAINT fk_premium_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- 7) Shorts
CREATE TABLE Shorts (
shorts_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
title VARCHAR(150) NOT NULL,
video_url VARCHAR(255),
thumbnail_url VARCHAR(255),
duration_seconds INT,
views INT DEFAULT 0,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_shorts_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Shorts_Like (
like_id INT AUTO_INCREMENT PRIMARY KEY,
shorts_id INT NOT NULL,
user_id INT NOT NULL,
type ENUM('like','dislike') DEFAULT 'like',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE KEY uk_shorts_like (shorts_id, user_id),
CONSTRAINT fk_shorts_like_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
CONSTRAINT fk_shorts_like_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

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
);

CREATE TABLE Comment_Like (
comment_like_id INT AUTO_INCREMENT PRIMARY KEY,
comment_id INT NOT NULL,
user_id INT NOT NULL,
type ENUM('like','dislike') DEFAULT 'like',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE(comment_id, user_id),
CONSTRAINT fk_comment_like_comment FOREIGN KEY (comment_id) REFERENCES Shorts_Comment(comment_id),
CONSTRAINT fk_comment_like_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Shorts_Share (
share_id INT AUTO_INCREMENT PRIMARY KEY,
shorts_id INT NOT NULL,
user_id INT NOT NULL,
platform ENUM('link','gmail','message') DEFAULT 'link',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_shorts_share_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
CONSTRAINT fk_shorts_share_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Shorts_Remix (
remix_id INT AUTO_INCREMENT PRIMARY KEY,
original_shorts_id INT NOT NULL,
remix_shorts_id INT NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE KEY uk_remix_pair (original_shorts_id, remix_shorts_id),
CONSTRAINT fk_remix_original FOREIGN KEY (original_shorts_id) REFERENCES Shorts(shorts_id),
CONSTRAINT fk_remix_remix FOREIGN KEY (remix_shorts_id) REFERENCES Shorts(shorts_id)
);

CREATE TABLE Shorts_ViewHistory (
view_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
shorts_id INT NOT NULL,
watched_seconds INT DEFAULT 0,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE KEY uk_view_user_shorts (user_id, shorts_id),
CONSTRAINT fk_view_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
CONSTRAINT fk_view_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id)
);

CREATE TABLE Playlist (
playlist_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
name VARCHAR(100) NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_playlist_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Playlist_Short (
id INT AUTO_INCREMENT PRIMARY KEY,
playlist_id INT NOT NULL,
shorts_id INT NOT NULL,
added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE (playlist_id, shorts_id),
CONSTRAINT fk_playlist_short_playlist FOREIGN KEY (playlist_id) REFERENCES Playlist(playlist_id),
CONSTRAINT fk_playlist_short_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id)
);

CREATE TABLE Shorts_NotInterested (
id INT AUTO_INCREMENT PRIMARY KEY,
shorts_id INT NOT NULL,
user_id INT NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE (shorts_id, user_id),
CONSTRAINT fk_notinterested_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
CONSTRAINT fk_notinterested_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Channel_Block (
id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
blocked_user_id INT NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE (user_id, blocked_user_id),
CONSTRAINT fk_channel_block_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
CONSTRAINT fk_channel_block_blocked FOREIGN KEY (blocked_user_id) REFERENCES Users(user_id),
CHECK (user_id != blocked_user_id)
);

CREATE TABLE Shorts_Report (
report_id INT AUTO_INCREMENT PRIMARY KEY,
shorts_id INT NOT NULL,
user_id INT NOT NULL,
reason ENUM('spam','violence','copyright','other') DEFAULT 'other',
detail TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_report_shorts FOREIGN KEY (shorts_id) REFERENCES Shorts(shorts_id),
CONSTRAINT fk_report_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Feedback (
feedback_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT,
message TEXT NOT NULL,
category ENUM('bug','feature_request','feedback','other') DEFAULT 'feedback',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
-- 데이터 셋 --
-- 1) Users 샘플 10행
INSERT INTO Users (username, handle, email, profile_img, join_date) VALUES
('Alice', 'alice01', 'alice@example.com', 'https://cdn.example.com/alice.png', '2023-01-01'),
('Bob', 'bob02', 'bob@example.com', 'https://cdn.example.com/bob.png', '2023-01-05'),
('Charlie', 'charlie03', 'charlie@example.com', 'https://cdn.example.com/charlie.png', '2023-02-10'),
('David', 'david04', 'david@example.com', 'https://cdn.example.com/david.png', '2023-03-12'),
('Eve', 'eve05', 'eve@example.com', 'https://cdn.example.com/eve.png', '2023-04-01'),
('Frank', 'frank06', 'frank@example.com', 'https://cdn.example.com/frank.png', '2023-05-08'),
('Grace', 'grace07', 'grace@example.com', 'https://cdn.example.com/grace.png', '2023-06-20'),
('Heidi', 'heidi08', 'heidi@example.com', 'https://cdn.example.com/heidi.png', '2023-07-15'),
('Ivan', 'ivan09', 'ivan@example.com', 'https://cdn.example.com/ivan.png', '2023-08-30'),
('Judy', 'judy10', 'judy@example.com', 'https://cdn.example.com/judy.png', '2023-09-05');

-- 2) Shorts 샘플 10행
INSERT INTO Shorts (user_id, title, video_url, thumbnail_url, duration_seconds, views) VALUES
(1, 'Funny Cat Video', 'https://video.example.com/1', 'https://thumb.example.com/1', 15, 120),
(2, 'Amazing Trick Shot', 'https://video.example.com/2', 'https://thumb.example.com/2', 20, 340),
(3, 'Daily Vlog', 'https://video.example.com/3', 'https://thumb.example.com/3', 30, 560),
(4, 'DIY Crafts', 'https://video.example.com/4', 'https://thumb.example.com/4', 25, 230),
(5, 'Gaming Highlights', 'https://video.example.com/5', 'https://thumb.example.com/5', 40, 410),
(6, 'Travel Tips', 'https://video.example.com/6', 'https://thumb.example.com/6', 18, 150),
(7, 'Cooking Tutorial', 'https://video.example.com/7', 'https://thumb.example.com/7', 35, 290),
(8, 'Workout Routine', 'https://video.example.com/8', 'https://thumb.example.com/8', 22, 380),
(9, 'Tech Review', 'https://video.example.com/9', 'https://thumb.example.com/9', 28, 450),
(10, 'Music Cover', 'https://video.example.com/10', 'https://thumb.example.com/10', 33, 310);

-- 3) Shorts_Like 샘플 10행
INSERT INTO Shorts_Like (shorts_id, user_id, type) VALUES
(1, 2, 'like'), (1, 3, 'like'), (2, 1, 'like'), (2, 3, 'dislike'),
(3, 4, 'like'), (3, 5, 'like'), (4, 6, 'like'), (5, 1, 'like'),
(6, 2, 'dislike'), (7, 3, 'like');

-- 4) Shorts_Comment 샘플 10행
INSERT INTO Shorts_Comment (shorts_id, user_id, content) VALUES
(1, 2, 'So cute!'), (1, 3, 'Loved this!'), (2, 1, 'Amazing trick!'),
(3, 4, 'Nice vlog'), (3, 5, 'Great content!'), (4, 6, 'Cool DIY'),
(5, 1, 'Awesome highlights'), (6, 2, 'Thanks for tips'), (7, 3, 'Yummy!'), (8, 4, 'Great workout');

-- 5) Comment_Like 샘플 10행
INSERT INTO Comment_Like (comment_id, user_id, type) VALUES
(1, 1, 'like'), (2, 1, 'like'), (3, 2, 'like'), (4, 3, 'dislike'),
(5, 4, 'like'), (6, 5, 'like'), (7, 6, 'like'), (8, 7, 'like'),
(9, 8, 'like'), (10, 9, 'dislike');

-- 6) Shorts_Share 샘플 10행
INSERT INTO Shorts_Share (shorts_id, user_id, platform) VALUES
(1, 2, 'link'), (2, 3, 'gmail'), (3, 4, 'message'), (4, 5, 'link'),
(5, 6, 'gmail'), (6, 7, 'message'), (7, 8, 'link'), (8, 9, 'gmail'),
(9, 10, 'message'), (10, 1, 'link');

-- 7) Shorts_Remix 샘플 5행
INSERT INTO Shorts_Remix (original_shorts_id, remix_shorts_id) VALUES
(1, 2), (1, 3), (2, 4), (3, 5), (4, 6);

-- 8) Shorts_ViewHistory 샘플 10행
INSERT INTO Shorts_ViewHistory (user_id, shorts_id, watched_seconds) VALUES
(1, 1, 15), (2, 1, 12), (3, 2, 20), (4, 3, 30), (5, 4, 25),
(6, 5, 40), (7, 6, 18), (8, 7, 35), (9, 8, 22), (10, 9, 28);

-- 9) Playlist 샘플 5행
INSERT INTO Playlist (user_id, name) VALUES
(1, 'My Favorites'), (2, 'Workout Videos'), (3, 'Funny Clips'),
(4, 'DIY Projects'), (5, 'Music Covers');

-- 10) Playlist_Short 샘플 10행
INSERT INTO Playlist_Short (playlist_id, shorts_id) VALUES
(1, 1), (1, 2), (2, 3), (2, 4), (3, 5), (3, 6), (4, 7), (4, 8), (5, 9), (5, 10);

-- 11) Shorts_NotInterested 샘플 5행
INSERT INTO Shorts_NotInterested (shorts_id, user_id) VALUES
(1, 4), (2, 5), (3, 6), (4, 7), (5, 8);

-- 12) Channel_Block 샘플 5행
INSERT INTO Channel_Block (user_id, blocked_user_id) VALUES
(1, 2), (2, 3), (3, 4), (4, 5), (5, 6);

-- 13) Shorts_Report 샘플 5행
INSERT INTO Shorts_Report (shorts_id, user_id, reason, detail) VALUES
(1, 2, 'spam', 'Repeated content'), (2, 3, 'copyright', 'Music issue'),
(3, 4, 'violence', 'Harmful content'), (4, 5, 'other', 'Offensive'), (5, 6, 'spam', 'Clickbait');

-- 14) Subscriptions 샘플 10행
INSERT INTO Subscriptions (subscriber_id, channel_id) VALUES
(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 1);

-- 1) 쇼츠 상세 조회
SELECT
s.shorts_id,
s.title,
s.video_url,
s.thumbnail_url,
s.views,
s.created_at,
(SELECT COUNT(*) FROM Shorts_Comment WHERE shorts_id = s.shorts_id) AS comment_count
FROM Shorts s
WHERE s.shorts_id = %s;

-- 2) 추천 쇼츠 조회
SELECT s.,
(SELECT COUNT() FROM Shorts_Like WHERE shorts_id = s.shorts_id AND type='like') AS like_count,
(SELECT COUNT(*) FROM Shorts_Comment WHERE shorts_id = s.shorts_id) AS comment_count
FROM Shorts s
WHERE s.shorts_id NOT IN (SELECT shorts_id FROM Shorts_NotInterested WHERE user_id = %s)
AND s.user_id NOT IN (SELECT blocked_user_id FROM Channel_Block WHERE user_id = %s)
ORDER BY s.views DESC, s.created_at DESC
LIMIT 50;

-- 3) 좋아요 / 싫어요 등록 또는 업데이트
INSERT INTO Shorts_Like (shorts_id, user_id, type)
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE type=%s;

-- 4) 관심없음 등록
INSERT INTO Shorts_NotInterested (shorts_id, user_id)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE created_at = NOW();

-- 5) 쇼츠 조회수 증가
UPDATE Shorts
SET views = views + 1
WHERE shorts_id = %s;

-- 6) 리믹스된 쇼츠 조회
SELECT s.*
FROM Shorts_Remix r
JOIN Shorts s ON r.remix_shorts_id = s.shorts_id
WHERE r.original_shorts_id = %s;

-- 7) 댓글 등록
INSERT INTO Shorts_Comment (shorts_id, user_id, content)
VALUES (%s, %s, %s);

-- 8) 대댓글 등록
INSERT INTO Shorts_Comment (shorts_id, user_id, parent_id, content)
VALUES (%s, %s, %s, %s);

-- 9) 댓글 삭제
DELETE FROM Shorts_Comment
WHERE comment_id = %s;

-- 10) 특정 쇼츠 댓글수 조회
SELECT COUNT(*) AS comment_count
FROM Shorts_Comment
WHERE shorts_id = %s;