CREATE TABLE cg_channel_review (
    user_id INT(11) NOT NULL,
    channel_id INT(11) NOT NULL,
    review TEXT UNICODE,
    timestamp DATETIME NOT NULL,
    is_public TINYINT DEFAULT 1,
    PRIMARY KEY (user_id, channel_id),
    CONSTRAINT fk_channel_review_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_channel_review_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
