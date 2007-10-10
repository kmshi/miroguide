-- create some indicies to make queries faster
create index by_ip on cg_channel_subscription (ip_address); -- from matt
create index channel_id_4 on cg_channel_subscription (channel_id, timestamp, ip_address, ignore_for_recommendations);
