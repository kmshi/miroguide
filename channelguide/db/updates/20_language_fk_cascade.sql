ALTER TABLE cg_secondary_language_map DROP FOREIGN KEY fk_language_map_channel;
ALTER TABLE cg_secondary_language_map ADD CONSTRAINT fk_language_map_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE;
ALTER TABLE cg_secondary_language_map DROP FOREIGN KEY fk_language_map_language;
ALTER TABLE cg_secondary_language_map ADD CONSTRAINT fk_language_map_language FOREIGN KEY (language_id) REFERENCES cg_channel_language (id) ON DELETE CASCADE;
