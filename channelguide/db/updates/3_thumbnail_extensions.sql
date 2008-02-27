-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE cg_channel ADD COLUMN thumbnail_extension VARCHAR(8) DEFAULT NULL;
ALTER TABLE cg_channel_item ADD COLUMN thumbnail_extension VARCHAR(8) DEFAULT NULL;
