-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

CREATE TABLE cg_channel_rating (
    user_id INT(11) NOT NULL,
    channel_id INT(11) NOT NULL,
    rating INT(1),
    PRIMARY KEY (user_id, channel_id),
    CONSTRAINT fk_channel_rating_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_channel_rating_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
