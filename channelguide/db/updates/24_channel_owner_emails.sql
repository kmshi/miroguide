-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE user ADD COLUMN channel_owner_emails TINYINT(1) NOT NULL DEFAULT 1;
