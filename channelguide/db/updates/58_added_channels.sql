CREATE TABLE cg_channel_added (
       channel_id INT(11) NOT NULL,
       user_id INT(11) NOT NULL,
       timestamp DATETIME,
       PRIMARY KEY (channel_id, user_id),
       CONSTRAINT fk_channel_added_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
       CONSTRAINT fk_channel_added_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
