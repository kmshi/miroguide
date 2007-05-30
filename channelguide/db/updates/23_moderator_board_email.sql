-- changes how much email moderators get.  Possible values:
-- S - "some" - receieve posts marked "Email moderators"
-- A - "all" - recieve all posts
-- N - "None" - recieve no emails
ALTER TABLE user ADD COLUMN moderator_board_email VARCHAR(1) NOT NULL DEFAULT
'S';
UPDATE user SET moderator_board_email='N' WHERE moderator_board_emails=0;
ALTER TABLE user DROP COLUMN moderator_board_emails;
