create table cg_channel_last_approved
(
    timestamp DATETIME,
    PRIMARY KEY (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8; 
-- can't do DEFAULT NOW()
INSERT INTO cg_channel_last_approved VALUES (NOW());
