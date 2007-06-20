ALTER TABLE cg_channel ADD COLUMN waiting_for_reply_date DATETIME NULL;
UPDATE cg_channel SET waiting_for_reply_date=NOW(), state='R' WHERE state='W';
