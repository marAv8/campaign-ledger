PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS campaigns (
 campaign_id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 channel TEXT NOT NULL CHECK(channel IN ('Meta','Google'))
);
CREATE TABLE IF NOT EXISTS daily_spend (
 campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
 day TEXT NOT NULL,
 ad_spend_cents INTEGER NOT NULL CHECK(ad_spend_cents>=0),
 other_acquisition_cents INTEGER NOT NULL CHECK(other_acquisition_cents>=0),
 impressions INTEGER NOT NULL CHECK(impressions>=0),
 clicks INTEGER NOT NULL CHECK(clicks>=0 AND clicks<=impressions),
 PRIMARY KEY(campaign_id,day)
);
CREATE TABLE IF NOT EXISTS customers (
 customer_id TEXT PRIMARY KEY,
 campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
 acquired_day TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
 order_id TEXT PRIMARY KEY,
 customer_id TEXT NOT NULL REFERENCES customers(customer_id),
 campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
 day TEXT NOT NULL,
 revenue_cents INTEGER NOT NULL CHECK(revenue_cents>=0)
);
CREATE INDEX IF NOT EXISTS orders_campaign_day ON orders(campaign_id,day);
CREATE INDEX IF NOT EXISTS customers_campaign_day ON customers(campaign_id,acquired_day);
