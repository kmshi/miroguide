ALTER TABLE cg_channel_rating ADD COLUMN timestamp DATETIME;
UPDATE cg_channel_rating SET timestamp=NOW();
