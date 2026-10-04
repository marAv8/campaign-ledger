-- Aggregate each source before joining to prevent duplicated spend or revenue.
-- Dates are inclusive. This fixture uses mutually exclusive, single-touch attribution.
WITH spend AS (
 SELECT campaign_id, SUM(ad_spend_cents) AS ad_spend_cents,
 SUM(other_acquisition_cents) AS other_acquisition_cents,
 SUM(impressions) AS impressions,SUM(clicks) AS clicks
 FROM daily_spend WHERE day BETWEEN :start AND :end GROUP BY campaign_id
), acquisition AS (
 SELECT campaign_id,COUNT(*) AS new_customers FROM customers
 WHERE acquired_day BETWEEN :start AND :end GROUP BY campaign_id
), revenue AS (
 SELECT campaign_id,SUM(revenue_cents) AS revenue_cents,COUNT(*) AS order_count
 FROM orders WHERE day BETWEEN :start AND :end GROUP BY campaign_id
)
SELECT c.campaign_id,c.name,c.channel,
 COALESCE(s.ad_spend_cents,0) AS ad_spend_cents,
 COALESCE(s.other_acquisition_cents,0) AS other_acquisition_cents,
 COALESCE(a.new_customers,0) AS new_customers,
 COALESCE(r.revenue_cents,0) AS revenue_cents,
 COALESCE(r.order_count,0) AS order_count,
 COALESCE(s.impressions,0) AS impressions,COALESCE(s.clicks,0) AS clicks,
 (COALESCE(s.ad_spend_cents,0)+COALESCE(s.other_acquisition_cents,0))/100.0
 /NULLIF(a.new_customers,0) AS cac,
 r.revenue_cents*1.0/NULLIF(s.ad_spend_cents,0) AS roas,
 r.revenue_cents/100.0/NULLIF(r.order_count,0) AS average_order_value
FROM campaigns c LEFT JOIN spend s USING(campaign_id)
LEFT JOIN acquisition a USING(campaign_id) LEFT JOIN revenue r USING(campaign_id)
ORDER BY c.channel,c.name;
