CREATE TABLE cg_user_auth_token (
  user_id INT(11) NOT NULL PRIMARY KEY,
  token VARCHAR(255) NOT NULL,
  expires DATETIME NOT NULL,
  CONSTRAINT fk_auth_token_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
  INDEX (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
