CREATE TABLE user (
  id INT(11) NOT NULL AUTO_INCREMENT,
  username VARCHAR(40) NOT NULL,
  role VARCHAR(1) NOT NULL DEFAULT 'U',
  blocked TINYINT(1) NOT NULL DEFAULT '0',
  approved TINYINT(1) NOT NULL DEFAULT '0',
  show_explicit TINYINT(1) NOT NULL DEFAULT '0',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  fname VARCHAR(45) DEFAULT NULL,
  lname VARCHAR(45) DEFAULT NULL,
  email VARCHAR(100) DEFAULT NULL,
  city VARCHAR(45) DEFAULT NULL,
  state VARCHAR(20) DEFAULT NULL,
  country VARCHAR(25) DEFAULT NULL,
  zip VARCHAR(15) DEFAULT NULL,
  im_username VARCHAR(35) DEFAULT NULL,
  im_type VARCHAR(25) DEFAULT NULL,
  hashed_password VARCHAR(40) NOT NULL,
  email_updates TINYINT(1) NOT NULL DEFAULT '0',
  PRIMARY KEY  (id),
  UNIQUE KEY username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_channel_language (
  id INT(11) NOT NULL AUTO_INCREMENT,
  name VARCHAR(40) NOT NULL,
  PRIMARY KEY  (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_channel (
  id INT(11) NOT NULL AUTO_INCREMENT,
  name VARCHAR(200) NOT NULL,
  url VARCHAR(200) NOT NULL,
  website_url VARCHAR(200) NOT NULL,
  short_description VARCHAR(255) NOT NULL,
  description text NOT NULL,
  hi_def TINYINT(1) NOT NULL DEFAULT '0',
  publisher VARCHAR(200) NOT NULL,
  state VARCHAR(1) NOT NULL DEFAULT 'N',
  featured TINYINT(1) NOT NULL DEFAULT '0',
  creation_time DATETIME NOT NULL,
  owner_id INT(11) NOT NULL,
  was_featured TINYINT(1) NOT NULL DEFAULT '0',
  cc_licence char(1) NOT NULL DEFAULT 'Z',
  primary_language_id INT(11) NOT NULL,
  PRIMARY KEY  (id),
  KEY owner_id (owner_id),
  CONSTRAINT fk_channel_owner FOREIGN KEY (owner_id) REFERENCES user (id) ON DELETE CASCADE,
  CONSTRAINT fk_channel_language FOREIGN KEY (primary_language_id) REFERENCES cg_channel_language (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_category (
  id INT(11) NOT NULL AUTO_INCREMENT,
  name VARCHAR(200) NOT NULL,
  PRIMARY KEY  (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_category_map (
  channel_id INT(11) NOT NULL,
  category_id INT(11) NOT NULL,
  PRIMARY KEY  (channel_id, category_id),
  KEY category_id (category_id),
  KEY channel_id (channel_id),
  CONSTRAINT fk_category_map_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE,
  CONSTRAINT fk_category_map_category FOREIGN KEY (category_id) REFERENCES cg_category (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_channel_item (
  id INT(11) NOT NULL AUTO_INCREMENT,
  channel_id INT(11) NOT NULL,
  url VARCHAR(200) NOT NULL,
  name VARCHAR(200) NOT NULL,
  description text NOT NULL,
  mime_type VARCHAR(50) DEFAULT NULL,
  size INT(11) DEFAULT NULL,
  date DATETIME DEFAULT NULL,
  thumbnail_url VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY  (id),
  KEY channel_id (channel_id),
  CONSTRAINT fk_item_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_channel_note (
  id INT(11) NOT NULL AUTO_INCREMENT,
  channel_id INT(11) NOT NULL,
  user_id INT(11) NOT NULL,
  type char(1) NOT NULL,
  title VARCHAR(255) NOT NULL,
  body text NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY  (id),
  KEY user_id (user_id),
  KEY channel_id (channel_id),
  CONSTRAINT fk_note_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
  CONSTRAINT fk_note_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_channel_subscription (
  channel_id INT(11) NOT NULL,
  timestamp DATETIME NOT NULL,
  KEY channel_id (channel_id),
  CONSTRAINT fk_subscription_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_moderator_action (
  id INT(11) NOT NULL AUTO_INCREMENT,
  user_id INT(11) NOT NULL,
  channel_id INT(11) NOT NULL,
  action VARCHAR(1) NOT NULL,
  timestamp DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY channel_id (channel_id),
  KEY user_id (user_id),
  CONSTRAINT fk_moderator_action_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
  CONSTRAINT fk_moderator_action_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_session (
  session_key VARCHAR(40) NOT NULL,
  data text NOT NULL,
  expires DATETIME NOT NULL,
  PRIMARY KEY  (session_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_tag (
  id INT(11) NOT NULL AUTO_INCREMENT,
  name VARCHAR(200) NOT NULL,
  PRIMARY KEY  (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_tag_map (
  channel_id INT(11) NOT NULL,
  user_id INT(11) NOT NULL,
  tag_id INT(11) NOT NULL,
  PRIMARY KEY  (user_id, tag_id, channel_id),
  KEY user_id (user_id),
  KEY tag_id (tag_id),
  KEY channel_id (channel_id),
  CONSTRAINT fk_tag_map_tag FOREIGN KEY (tag_id) REFERENCES cg_tag (id) ON DELETE CASCADE,
  CONSTRAINT fk_tag_map_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE,
  CONSTRAINT fk_tag_map_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE cg_secondary_language_map (
  channel_id INT(11) NOT NULL,
  language_id INT(11) NOT NULL,
  PRIMARY KEY  (channel_id, language_id),
  KEY fk_language (language_id),
  CONSTRAINT fk_language_map_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id),
  CONSTRAINT fk_language_map_language FOREIGN KEY (language_id) REFERENCES cg_channel_language (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
