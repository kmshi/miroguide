-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE cg_channel ADD COLUMN moderator_shared_by_id INT(11) NULL;
ALTER TABLE cg_channel ADD CONSTRAINT fk_moderator_shared_by_id FOREIGN KEY (moderator_shared_by_id) REFERENCES user (id) ON DELETE SET NULL;
