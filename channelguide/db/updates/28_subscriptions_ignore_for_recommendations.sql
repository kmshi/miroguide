-- Mark some subscriptions as not to be included in the recommendations
ALTER TABLE cg_channel_subscription ADD COLUMN ignore_for_recommendations TINYINT NOT NULL DEFAULT 0;