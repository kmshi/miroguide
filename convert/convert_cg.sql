-- Set up the language, category and tags tables
INSERT INTO cg_channel_language(id, name) SELECT language_id, language
    FROM channel_languages;
INSERT INTO cg_category(id, name) SELECT category_id, category 
    FROM channel_categories;
INSERT INTO cg_tag(id, name) SELECT tag_id, tag FROM tags;
-- Delete bogus users
DELETE FROM users where name='';
DELETE FROM users where name='???';
-- Set up users table
INSERT INTO user(id, username, email, hashed_password, created_at, updated_at)
    SELECT uid, name, mail, pass,
        IF(created!=0,FROM_UNIXTIME(created),NULL),
        IF(changed!=0,FROM_UNIXTIME(changed),NULL)
    FROM users;
-- Set Up moderators
UPDATE user SET ROLE='M' WHERE id in (SELECT uid FROM users_roles WHERE rid=4);
-- Set up channel table
INSERT INTO cg_channel (id, state, name, owner_id, url, website_url,
  publisher, short_description, description, hi_def, creation_time, modified,
  primary_language_id)
    SELECT node.nid, 'A', title, uid, subscription_url, related_website_url, 
        publisher_name, short_desc, long_desc, is_hd, 
        IF(created!=0,FROM_UNIXTIME(created),NULL),
        IF(changed!=0,FROM_UNIXTIME(changed),NULL),
        IF(language_1 != 0, language_1, 
                (SELECT id FROM cg_channel_language WHERE name='English'))
    FROM channel_info, node
    WHERE channel_info.nid = node.nid;
UPDATE cg_channel SET approved_at=creation_time WHERE state='A';
-- Assign secondary languages
INSERT INTO cg_secondary_language_map(channel_id, language_id)
    SELECT nid, language_2 FROM channel_info
    WHERE language_2 NOT IN (SELECT primary_language_id from cg_channel) AND
        language_2 != 0;
INSERT INTO cg_secondary_language_map(channel_id, language_id)
    SELECT nid, language_3 FROM channel_info
    WHERE language_3 NOT IN (SELECT primary_language_id from cg_channel) AND
        language_3 NOT IN (SELECT language_id from cg_secondary_language_map) AND
        language_3 != 0;
UPDATE cg_channel SET featured=1
    WHERE id in (select nid from channel_featured);
-- Assaign tags
INSERT INTO cg_tag_map(tag_id, channel_id, user_id)
    SELECT DISTINCT tag_id, nid, owner_id
    FROM channel_tags, cg_channel
    WHERE cg_channel.id = channel_tags.nid;
DELETE FROM cg_tag where name ='';
-- Assign Categories
INSERT INTO cg_category_map(category_id, channel_id)
    SELECT category_1, nid FROM channel_info WHERE category_1 != 0;
INSERT INTO cg_category_map(category_id, channel_id)
    SELECT category_2, nid FROM channel_info 
    WHERE category_2 != 0 AND category_2 NOT IN 
        (SELECT category_id FROM cg_category_map);
INSERT INTO cg_category_map(category_id, channel_id)
    SELECT category_3, nid FROM channel_info 
    WHERE category_3 != 0 AND category_3 NOT IN 
        (SELECT category_id FROM cg_category_map);
