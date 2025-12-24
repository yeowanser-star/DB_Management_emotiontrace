-- 1. 视频元数据表
CREATE TABLE `videos` (
  `video_id` varchar(20) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text,
  `avg_sentiment` decimal(3,2) DEFAULT '0.50',
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`video_id`)
) ENGINE=InnoDB;

-- 2. 评论主表（含 AI 分数）
CREATE TABLE `comments` (
  `rpid` bigint NOT NULL,
  `video_id` varchar(20) NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  `uname` varchar(100) DEFAULT NULL,
  `content` text NOT NULL,
  `sentiment_score` decimal(3,2) NOT NULL,
  `relevance_score` decimal(3,2) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`rpid`),
  KEY `fk_video` (`video_id`),
  KEY `fk_parent` (`parent_id`),
  CONSTRAINT `fk_parent` FOREIGN KEY (`parent_id`) REFERENCES `comments` (`rpid`) ON DELETE CASCADE,
  CONSTRAINT `fk_video` FOREIGN KEY (`video_id`) REFERENCES `videos` (`video_id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3. 标签字典表
CREATE TABLE `tags_dict` (
  `tag_id` int NOT NULL AUTO_INCREMENT,
  `tag_name` varchar(50) NOT NULL,
  `tag_category` enum('主题','行为','特征') NOT NULL,
  PRIMARY KEY (`tag_id`),
  UNIQUE KEY `tag_name` (`tag_name`)
) ENGINE=InnoDB;

-- 4. 评论-标签关联映射表
CREATE TABLE `comment_tag_map` (
  `rpid` bigint NOT NULL,
  `tag_id` int NOT NULL,
  PRIMARY KEY (`rpid`,`tag_id`),
  KEY `comment_tag_map_ibfk_2` (`tag_id`),
  CONSTRAINT `comment_tag_map_ibfk_1` FOREIGN KEY (`rpid`) REFERENCES `comments` (`rpid`) ON DELETE CASCADE,
  CONSTRAINT `comment_tag_map_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tags_dict` (`tag_id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. 视频统计缓存表
CREATE TABLE `video_stats` (
  `video_id` bigint NOT NULL,
  `total_comments` int DEFAULT '0',
  `avg_sentiment` decimal(3,2) DEFAULT '0.00',
  `positive_count` int DEFAULT '0',
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`video_id`)
) ENGINE=InnoDB;

-- 6. 用户基础信息表
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `user_level` int DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB;

-- 7. 核心数据透视视图
CREATE VIEW `view_comment_analysis` AS
SELECT
    `c`.`rpid` AS `rpid`,
    `c`.`video_id` AS `video_id`,
    `v`.`title` AS `video_title`,
    `c`.`content` AS `content`,
    `STRETCH_SCORE`(`c`.`sentiment_score`) AS `sentiment_score`, -- 调用了自定义函数进行评分拉伸
    `c`.`relevance_score` AS `relevance_score`,
    (SELECT GROUP_CONCAT(`td`.`tag_name` SEPARATOR ',')
     FROM `comment_tag_map` `m`
     JOIN `tags_dict` `td` ON `m`.`tag_id` = `td`.`tag_id`
     WHERE `m`.`rpid` = `c`.`rpid`) AS `tags_display`,
    IF(`c`.`parent_id` IS NULL, '主评论', '回复') AS `type`
FROM `comments` `c`
JOIN `videos` `v` ON `c`.`video_id` = `v`.`video_id`;