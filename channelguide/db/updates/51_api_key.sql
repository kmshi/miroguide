CREATE TABLE cg_api_key (
    api_key CHAR(40) UNIQUE NOT NULL,
    owner_id INT(11) NOT NULL,
    active TINYINT(1) DEFAULT '1',
    created_at DATETIME NOT NULL,
    description TEXT,
    PRIMARY KEY (api_key),
    CONSTRAINT fk_apikeyowner FOREIGN KEY (owner_id) REFERENCES user (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
