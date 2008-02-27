-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE robot ADD COLUMN laser_beams int;
UPDATE robot set laser_beams=2;
