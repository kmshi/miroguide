CREATE TABLE cg_channel_featured_queue (
    channel_id INT(11) NOT NULL PRIMARY KEY,
    state TINYINT(1) NOT NULL DEFAULT 0,
    featured_by_id INT(11) NOT NULL,
    featured_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8; 
