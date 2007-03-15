INSERT INTO user(username, email, hashed_password, updated_at, created_at)
    SELECT users.username, email, hashed_password, updated_at,
        IF(created_at IS NULL, NOW(), created_at)
        FROM users, user_cache
        WHERE users.username = user_cache.username AND
            users.username NOT IN (SELECT username FROM user);
UPDATE user 
    SET email_updates=(SELECT email_updatesP FROM user_cache 
            WHERE user_cache.username=user.username),
        fname=(SELECT fname FROM user_cache
            WHERE user_cache.username=user.username),
        lname=(SELECT lname FROM user_cache
            WHERE user_cache.username=user.username),
        email=(SELECT email FROM user_cache
            WHERE user_cache.username=user.username),
        city=(SELECT city FROM user_cache
            WHERE user_cache.username=user.username),
        state=(SELECT state FROM user_cache
            WHERE user_cache.username=user.username),
        country=(SELECT country FROM user_cache
            WHERE user_cache.username=user.username),
        zip=(SELECT zip FROM user_cache
            WHERE user_cache.username=user.username),
        im_username=(SELECT im_username FROM user_cache
            WHERE user_cache.username=user.username),
        im_type=(SELECT im_type FROM user_cache
        WHERE user_cache.username=user.username)
    WHERE username IN (SELECT username FROM user_cache);
UPDATE user
    SET blocked=(SELECT blocked FROM users
        WHERE users.username=user.username),
        approved=(SELECT approved FROM users
        WHERE users.username=user.username),
    	show_explicit=(SELECT show_explicit FROM users
        WHERE users.username=user.username)
    WHERE username IN (SELECT username FROM users);
UPDATE user SET role='A' WHERE username in
        (SELECT username FROM users WHERE admin=1);
