CREATE TABLE cg_channel_flags (
       channel_id INT(11) NOT NULL,
       user_id INT(11) NULL,
       flag SMALLINT NOT NULL,
       CONSTRAINT fk_cg_channel_flags_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
       CONSTRAINT fk_cg_channel_flags_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE,
       INDEX (channel_id),
       INDEX (channel_id, flag),
       INDEX (channel_id, user_id, flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
