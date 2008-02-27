-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

CREATE TABLE cg_moderator_post (
  id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT(11) NOT NULL,
  title VARCHAR(255) NOT NULL,
  body text NOT NULL,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
