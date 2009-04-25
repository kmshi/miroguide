CREATE TABLE aether_channel_item_delta (
  id INT(11) NOT NULL AUTO_INCREMENT,
  channel_id INT(11) NOT NULL,
  item_id INT(11) NOT NULL,
  mod_type TINYINT(2) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL,

  PRIMARY KEY (id),

  INDEX (item_id),
  INDEX (created_at),
  INDEX (mod_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE aether_channel_subscription (
  user_id INT(11) NOT NULL,
  channel_id INT(11) NOT NULL,
  created_at TIMESTAMP NOT NULL,

  PRIMARY KEY (user_id, channel_id),
  KEY user_id (user_id),
  KEY channel_id (channel_id),

  CONSTRAINT fk_subscription_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,

  INDEX (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE aether_channel_subscription_delta (
  id INT(11) NOT NULL AUTO_INCREMENT,
  user_id INT(11) NOT NULL,
  channel_id INT(11) NOT NULL,
  mod_type TINYINT(2) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL,

  PRIMARY KEY (id),
  CONSTRAINT fk_sub_delta_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,

  INDEX (channel_id),
  INDEX (created_at),
  INDEX (mod_type),
  INDEX (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE aether_download_request (
  user_id INT(11) NOT NULL,
  item_id INT(11) NOT NULL,
  created_at TIMESTAMP NOT NULL,
  imparted_on TIMESTAMP,

  PRIMARY KEY (user_id, item_id),
  KEY user_id (user_id),
  KEY item_id (item_id),

  CONSTRAINT fk_item_download_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,

  INDEX (created_at),
  INDEX (imparted_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE aether_download_request_delta (
  id INT(11) NOT NULL AUTO_INCREMENT,
  user_id INT(11) NOT NULL,
  item_id INT(11) NOT NULL,
  mod_type TINYINT(2) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL,

  PRIMARY KEY (id),
  CONSTRAINT fk_download_delta_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,

  INDEX (created_at),
  INDEX (item_id),
  INDEX (mod_type),
  INDEX (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;