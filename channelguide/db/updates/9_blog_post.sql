-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

CREATE TABLE cg_pcf_blog_post (
  id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  body text NOT NULL,
  url VARCHAR(200) NOT NULL,
  position INT(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
