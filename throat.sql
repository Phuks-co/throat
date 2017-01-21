DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
  `uid` varchar(40) NOT NULL,
  `name` varchar(64) DEFAULT NULL,
  `email` varchar(128) DEFAULT NULL,
  `crypto` int(11) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  `joindate` datetime DEFAULT NULL,
  `score` int(11) DEFAULT NULL,
  PRIMARY KEY (`uid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `client`;

CREATE TABLE `client` (
  `name` varchar(40) DEFAULT NULL,
  `user_id` varchar(40) DEFAULT NULL,
  `client_id` varchar(40) NOT NULL,
  `client_secret` varchar(55) NOT NULL,
  `is_confidential` tinyint(1) DEFAULT NULL,
  `_redirect_uris` text,
  `_default_scopes` text,
  PRIMARY KEY (`client_id`),
  UNIQUE KEY `ix_client_client_secret` (`client_secret`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `client_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `grant`;

CREATE TABLE `grant` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` varchar(40) DEFAULT NULL,
  `client_id` varchar(40) NOT NULL,
  `code` varchar(255) NOT NULL,
  `redirect_uri` varchar(255) DEFAULT NULL,
  `expires` datetime DEFAULT NULL,
  `_scopes` text,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `client_id` (`client_id`),
  KEY `ix_grant_code` (`code`),
  CONSTRAINT `grant_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`uid`),
  CONSTRAINT `grant_ibfk_2` FOREIGN KEY (`client_id`) REFERENCES `client` (`client_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `message`;

CREATE TABLE `message` (
  `mid` int(11) NOT NULL AUTO_INCREMENT,
  `sentby` varchar(40) DEFAULT NULL,
  `receivedby` varchar(40) DEFAULT NULL,
  `subject` varchar(128) DEFAULT NULL,
  `content` text,
  `posted` datetime DEFAULT NULL,
  `read` datetime DEFAULT NULL,
  `mtype` int(11) DEFAULT NULL,
  `mlink` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`mid`),
  KEY `sentby` (`sentby`),
  KEY `receivedby` (`receivedby`),
  CONSTRAINT `message_ibfk_1` FOREIGN KEY (`sentby`) REFERENCES `user` (`uid`),
  CONSTRAINT `message_ibfk_2` FOREIGN KEY (`receivedby`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `site_log`;
CREATE TABLE `site_log` (
  `lid` int(11) NOT NULL AUTO_INCREMENT,
  `time` datetime DEFAULT NULL,
  `action` int(11) DEFAULT NULL,
  `desc` varchar(255) DEFAULT NULL,
  `link` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`lid`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `site_metadata`;

CREATE TABLE `site_metadata` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `key` varchar(255) DEFAULT NULL,
  `value` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`xid`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub`;

CREATE TABLE `sub` (
  `sid` varchar(40) NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  `title` varchar(128) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  `sidebar` text,
  `nsfw` int(11) DEFAULT NULL,
  PRIMARY KEY (`sid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_flair`;

CREATE TABLE `sub_flair` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `sid` varchar(40) DEFAULT NULL,
  `text` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`xid`),
  KEY `sid` (`sid`),
  CONSTRAINT `sub_flair_ibfk_1` FOREIGN KEY (`sid`) REFERENCES `sub` (`sid`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_log`;

CREATE TABLE `sub_log` (
  `lid` int(11) NOT NULL AUTO_INCREMENT,
  `sid` varchar(40) DEFAULT NULL,
  `time` datetime DEFAULT NULL,
  `action` int(11) DEFAULT NULL,
  `desc` varchar(255) DEFAULT NULL,
  `link` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`lid`),
  KEY `sid` (`sid`),
  CONSTRAINT `sub_log_ibfk_1` FOREIGN KEY (`sid`) REFERENCES `sub` (`sid`)
) ENGINE=InnoDB AUTO_INCREMENT=46 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_metadata`;

CREATE TABLE `sub_metadata` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `sid` varchar(40) DEFAULT NULL,
  `key` varchar(255) DEFAULT NULL,
  `value` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`xid`),
  KEY `sid` (`sid`),
  CONSTRAINT `sub_metadata_ibfk_1` FOREIGN KEY (`sid`) REFERENCES `sub` (`sid`)
) ENGINE=InnoDB AUTO_INCREMENT=314 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_post`;

CREATE TABLE `sub_post` (
  `pid` int(11) NOT NULL AUTO_INCREMENT,
  `sid` varchar(40) DEFAULT NULL,
  `uid` varchar(40) DEFAULT NULL,
  `title` varchar(256) DEFAULT NULL,
  `link` varchar(256) DEFAULT NULL,
  `content` text,
  `posted` datetime DEFAULT NULL,
  `ptype` int(11) DEFAULT NULL,
  `score` int(11) DEFAULT NULL,
  `thumbnail` varchar(128) DEFAULT NULL,
  `deleted` int(11) DEFAULT NULL,
  `nsfw` int(11) DEFAULT NULL,
  PRIMARY KEY (`pid`),
  KEY `sid` (`sid`),
  KEY `uid` (`uid`),
  CONSTRAINT `sub_post_ibfk_1` FOREIGN KEY (`sid`) REFERENCES `sub` (`sid`),
  CONSTRAINT `sub_post_ibfk_2` FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=255 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_post_comment`;

CREATE TABLE `sub_post_comment` (
  `cid` varchar(64) NOT NULL,
  `pid` int(11) DEFAULT NULL,
  `uid` varchar(40) DEFAULT NULL,
  `time` datetime DEFAULT NULL,
  `lastedit` datetime DEFAULT NULL,
  `content` text,
  `status` int(11) DEFAULT NULL,
  `score` int(11) DEFAULT NULL,
  `parentcid` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`cid`),
  KEY `pid` (`pid`),
  KEY `uid` (`uid`),
  KEY `parentcid` (`parentcid`),
  CONSTRAINT `sub_post_comment_ibfk_1` FOREIGN KEY (`pid`) REFERENCES `sub_post` (`pid`),
  CONSTRAINT `sub_post_comment_ibfk_2` FOREIGN KEY (`uid`) REFERENCES `user` (`uid`),
  CONSTRAINT `sub_post_comment_ibfk_3` FOREIGN KEY (`parentcid`) REFERENCES `sub_post_comment` (`cid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_post_comment_vote`;

CREATE TABLE `sub_post_comment_vote` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `cid` varchar(64) DEFAULT NULL,
  `uid` varchar(40) DEFAULT NULL,
  `positive` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`xid`),
  KEY `uid` (`uid`),
  CONSTRAINT `sub_post_comment_vote_ibfk_1` FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_post_metadata`;

CREATE TABLE `sub_post_metadata` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `pid` int(11) DEFAULT NULL,
  `key` varchar(255) DEFAULT NULL,
  `value` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`xid`),
  KEY `pid` (`pid`),
  CONSTRAINT `sub_post_metadata_ibfk_1` FOREIGN KEY (`pid`) REFERENCES `sub_post` (`pid`)
) ENGINE=InnoDB AUTO_INCREMENT=382 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_post_vote`;

CREATE TABLE `sub_post_vote` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `pid` int(11) DEFAULT NULL,
  `uid` varchar(40) DEFAULT NULL,
  `positive` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`xid`),
  KEY `pid` (`pid`),
  KEY `uid` (`uid`),
  CONSTRAINT `sub_post_vote_ibfk_1` FOREIGN KEY (`pid`) REFERENCES `sub_post` (`pid`),
  CONSTRAINT `sub_post_vote_ibfk_2` FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_stylesheet`;

CREATE TABLE `sub_stylesheet` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `sid` varchar(40) DEFAULT NULL,
  `content` text,
  PRIMARY KEY (`xid`),
  KEY `sid` (`sid`),
  CONSTRAINT `sub_stylesheet_ibfk_1` FOREIGN KEY (`sid`) REFERENCES `sub` (`sid`)
) ENGINE=InnoDB AUTO_INCREMENT=55 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `sub_subscriber`;

CREATE TABLE `sub_subscriber` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `sid` varchar(40) DEFAULT NULL,
  `uid` varchar(40) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  `time` datetime DEFAULT NULL,
  `order` int(11) DEFAULT NULL,
  PRIMARY KEY (`xid`),
  KEY `sid` (`sid`),
  KEY `uid` (`uid`),
  CONSTRAINT `sub_subscriber_ibfk_1` FOREIGN KEY (`sid`) REFERENCES `sub` (`sid`),
  CONSTRAINT `sub_subscriber_ibfk_2` FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `token`;

CREATE TABLE `token` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` varchar(40) NOT NULL,
  `user_id` varchar(40) DEFAULT NULL,
  `token_type` varchar(40) DEFAULT NULL,
  `access_token` varchar(255) DEFAULT NULL,
  `refresh_token` varchar(255) DEFAULT NULL,
  `expires` datetime DEFAULT NULL,
  `_scopes` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `access_token` (`access_token`),
  UNIQUE KEY `refresh_token` (`refresh_token`),
  KEY `client_id` (`client_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `token_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `client` (`client_id`),
  CONSTRAINT `token_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `user_badge`;

CREATE TABLE `user_badge` (
  `bid` varchar(40) NOT NULL,
  `badge` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `text` varchar(255) DEFAULT NULL,
  `value` int(128) DEFAULT 100,
  PRIMARY KEY (`bid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `user_metadata`;

CREATE TABLE `user_metadata` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `uid` varchar(40) DEFAULT NULL,
  `key` varchar(255) DEFAULT NULL,
  `value` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`xid`),
  KEY `uid` (`uid`),
  CONSTRAINT `user_metadata_ibfk_1` FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `user_saved`;

CREATE TABLE `user_saved` (
  `xid` int(11) NOT NULL AUTO_INCREMENT,
  `uid` varchar(40) DEFAULT NULL,
  `pid` int(128) DEFAULT NULL,
  PRIMARY KEY (`xid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
