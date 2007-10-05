ALTER TABLE cg_channel ADD COLUMN featured_by_id INT(11) NULL;
ALTER TABLE cg_channel ADD CONSTRAINT fk_featured_by_id FOREIGN KEY (last_moderated_by_id) REFERENCES user (id) ON DELETE SET NULL;
   
