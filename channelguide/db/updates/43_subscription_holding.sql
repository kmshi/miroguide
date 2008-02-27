-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

CREATE TABLE cg_channel_subscription_holding (
  channel_id INT(11) NOT NULL,
  timestamp DATETIME NOT NULL,
  ip_address VARCHAR(16) NOT NULL,
  ignore_for_recommendations TINYINT(4) NOT NULL,
  KEY channel_id (channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

