CREATE TABLE cg_watched_videos (
    type TINYINT(1) NOT NULL,
    id   INT(11)    NOT NULL,
    count INT(11)   DEFAULT 0,
    PRIMARY KEY (type, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;