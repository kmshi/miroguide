-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE user ADD COLUMN moderator_board_emails tinyint(1) NOT NULL DEFAULT 1;
ALTER TABLE user ADD COLUMN status_emails tinyint(1) NOT NULL DEFAULT 1;
