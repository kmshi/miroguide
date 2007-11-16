create table cg_channel_generated_ratings
(
    channel_id int(11) NOT NULL,
    average FLOAT (2, 1),
    count INT,
    total BIGINT,
    CONSTRAINT FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE,
    PRIMARY KEY (channel_id),
    KEY (average, count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8; 
INSERT INTO cg_channel_generated_ratings SELECT id,
    (SELECT IFNULL(ROUND(AVG(rating), 1), 0) FROM cg_channel_rating
        JOIN user ON user.id=cg_channel_rating.user_id
        WHERE cg_channel_rating.channel_id=cg_channel.id AND user.approved=1),
    (SELECT COUNT(rating) FROM cg_channel_rating
        JOIN user ON user.id=cg_channel_rating.user_id
        WHERE cg_channel_rating.channel_id=cg_channel.id AND user.approved=1),
    (SELECT IFNULL(SUM(rating), 0) FROM cg_channel_rating
        JOIN user ON user.id=cg_channel_rating.user_id
        WHERE cg_channel_rating.channel_id=cg_channel.id AND user.approved=1)
    FROM cg_channel WHERE state='A';
