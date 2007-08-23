CREATE TABLE cg_channel_recommendations ( 
  channel1_id INT(11) NOT NULL,
  channel2_id INT(11) NOT NULL,
  cosine FLOAT NOT NULL, 
  KEY channel1_id (channel1_id),
  CONSTRAINT fk_channel1_id FOREIGN KEY (channel1_id) REFERENCES cg_channel (id) ON DELETE CASCADE,
  KEY channel2_id (channel2_id),
  CONSTRAINT fk_channel2_id FOREIGN KEY (channel2_id) REFERENCES cg_channel (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
