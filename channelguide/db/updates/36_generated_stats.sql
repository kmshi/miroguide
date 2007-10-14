create table cg_channel_generated_stats
(
    channel_id int(11) NOT NULL,
    subscription_count_total int(11) NOT NULL,
    subscription_count_month int(11) NOT NULL,
    subscription_count_today int(11) NOT NULL,
    CONSTRAINT fk_channel_stats_channel FOREIGN KEY (channel_id) REFERENCES cg_channel (id) ON DELETE CASCADE,
    PRIMARY KEY (channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
