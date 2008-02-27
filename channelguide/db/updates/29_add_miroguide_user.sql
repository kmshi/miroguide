-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

-- Add a user who does automated miroguide actions.
INSERT INTO user (username, role, email, created_at, updated_at, hashed_password) VALUES ("miroguide", "A", "channels@pculture.org", NOW(), NOW(), "");
