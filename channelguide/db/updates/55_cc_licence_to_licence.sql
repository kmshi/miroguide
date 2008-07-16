ALTER TABLE cg_channel DROP COLUMN cc_licence;
ALTER TABLE cg_channel ADD COLUMN license VARCHAR(40) NOT NULL default '';
