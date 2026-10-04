-- Fictional customers classified by observed orders in the full sample window.
-- A customer may qualify for more than one segment; segments must not be summed.
WITH purchases AS (
 SELECT customer_id, COUNT(*) AS order_count,SUM(revenue_cents) AS revenue_cents
 FROM orders WHERE day BETWEEN :start AND :end GROUP BY customer_id
)
SELECT c.customer_id,c.campaign_id,k.channel,c.acquired_day,
 COALESCE(p.order_count,0) AS order_count,
 COALESCE(p.revenue_cents,0) AS revenue_cents
FROM customers c JOIN campaigns k USING(campaign_id)
LEFT JOIN purchases p USING(customer_id)
WHERE c.acquired_day BETWEEN :start AND :end
ORDER BY c.customer_id;
