-- true if the category should appear on the front page
ALTER TABLE cg_category ADD COLUMN on_frontpage TINYINT(1) DEFAULT 1;