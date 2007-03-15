-- Replace "check this out" with "share with moderators". 
-- Make it remembers the time.
ALTER TABLE cg_channel DROP COLUMN check_this_out;
ALTER TABLE cg_channel ADD COLUMN moderator_shared_at DATETIME NULL;
