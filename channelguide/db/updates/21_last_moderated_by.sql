ALTER TABLE cg_channel ADD COLUMN last_moderated_by_id INT(11) NULL;
ALTER TABLE cg_channel ADD CONSTRAINT fk_last_moderated_by_id FOREIGN KEY (last_moderated_by_id) REFERENCES user (id) ON DELETE SET NULL;
UPDATE cg_channel SET last_moderated_by_id=(SELECT user_id 
        FROM cg_moderator_action
        WHERE channel_id=cg_channel.id
        ORDER BY timestamp
        DESC LIMIT 1);
