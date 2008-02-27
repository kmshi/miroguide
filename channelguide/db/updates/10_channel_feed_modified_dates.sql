-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE cg_channel ADD COLUMN feed_modified DATETIME DEFAULT NULL;
ALTER TABLE cg_channel ADD COLUMN feed_etag VARCHAR(255) DEFAULT NULL;
