-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE cg_channel_subscription ADD COLUMN ip_address VARCHAR(16) NOT NULL;
UPDATE cg_channel_subscription SET ip_address='0.0.0.0';
ALTER TABLE cg_channel_subscription ADD INDEX (channel_id, timestamp);
ALTER TABLE cg_channel_subscription ADD INDEX (channel_id, ip_address, timestamp);
