-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

CREATE TABLE cg_cobranding (
    name VARCHAR(40) UNIQUE NOT NULL,
    long_title VARCHAR(100) NOT NULL,
    short_title VARCHAR(30) NOT NULL,
    url VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    link1_url VARCHAR(100),
    link1_text VARCHAR(100), 
    link2_url VARCHAR(100),
    link2_text VARCHAR(100), 
    link3_url VARCHAR(100),
    link3_text VARCHAR(100), 
    PRIMARY KEY (name),
    CONSTRAINT fk_cobranduser FOREIGN KEY (name) REFERENCES user (username) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8; 
