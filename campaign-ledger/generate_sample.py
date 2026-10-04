"""Create deterministic fictional campaign exports. No customer identities or live accounts."""
import csv,random
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def write(name,fields,rows):
 with (ROOT/'data'/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def generate():
 rng=random.Random(20261003)
 campaigns=[dict(campaign_id='meta_prospect',name='New season discovery',channel='Meta'),
 dict(campaign_id='meta_return',name='Collection retargeting',channel='Meta'),
 dict(campaign_id='google_brand',name='Brand search',channel='Google'),
 dict(campaign_id='google_shop',name='Everyday essentials',channel='Google')]
 spend=[];customers=[];orders=[];start=date(2026,9,19)
 for k,c in enumerate(campaigns):
  for n in range(14):
   day=start+timedelta(days=n);budget=[22000,12000,9000,18000][k]+rng.randrange(-1000,1000)
   new_count=[5,3,4,4][k]+rng.randrange(-1,2)
   if k==0 and n>=7: budget=int(budget*1.45);new_count=max(1,new_count-2)
   impressions=budget//2+rng.randrange(1000)
   spend.append(dict(campaign_id=c['campaign_id'],day=str(day),ad_spend_cents=budget,other_acquisition_cents=budget//8,impressions=impressions,clicks=impressions//30))
   for i in range(new_count):
    cid=f'customer_{len(customers)+1:04d}'
    customers.append(dict(customer_id=cid,campaign_id=c['campaign_id'],acquired_day=str(day)))
    orders.append(dict(order_id=f'order_{len(orders)+1:04d}',customer_id=cid,campaign_id=c['campaign_id'],day=str(day),revenue_cents=rng.choice([7900,9900,12900,15900])))
    if n<8 and i==0:
     orders.append(dict(order_id=f'order_{len(orders)+1:04d}',customer_id=cid,campaign_id=c['campaign_id'],day=str(day+timedelta(days=6)),revenue_cents=7900))
 write('campaigns.csv',['campaign_id','name','channel'],campaigns)
 write('daily_spend.csv',['campaign_id','day','ad_spend_cents','other_acquisition_cents','impressions','clicks'],spend)
 write('customers.csv',['customer_id','campaign_id','acquired_day'],customers)
 write('orders.csv',['order_id','customer_id','campaign_id','day','revenue_cents'],orders)
 print(f'Generated 4 fictional campaigns, {len(spend)} daily rows, {len(customers)} customers, {len(orders)} orders.')
if __name__=='__main__':generate()
