-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

CREATE TABLE cg_channel_featured_email (
    sender_id INT(11) NOT NULL,
    channel_id INT(11) NOT NULL,
    email VARCHAR(100) NOT NULL,
    title VARCHAR(100) NOT NULL,
    body TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    CONSTRAINT fk_sender FOREIGN KEY (sender_id) REFERENCES user (id) ON DELETE CASCADE,
  CONSTRAINT fk_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE,
    PRIMARY KEY (channel_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8; 

