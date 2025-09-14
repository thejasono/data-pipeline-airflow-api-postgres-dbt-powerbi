import uuid, random
from datetime import datetime, timedelta, timezone

COUNTRIES = ["US","GB","DE","FR","CA","AU","NL","SE","IT","ES"]
COUNTRY_W = [0.35,0.15,0.12,0.07,0.08,0.06,0.06,0.04,0.04,0.03]
INDUSTRIES = ["E-commerce","SaaS","Consulting","Education","Health","Finance"]
IND_W = [0.35,0.25,0.12,0.1,0.1,0.08]
PRODUCTS = ["Basic","Pro","Enterprise","Addon-Analytics","Addon-Support"]
PRICES = {"Basic":29,"Pro":99,"Enterprise":499,"Addon-Analytics":49,"Addon-Support":99}
PAYMENT_METHODS=["card","bank_transfer","paypal","apple_pay","google_pay"]
PM_W=[0.6,0.15,0.15,0.05,0.05]
STATUSES=["succeeded","failed","refunded"]
STAT_W=[0.9,0.06,0.04]
SOURCES=["google","direct","facebook","linkedin","newsletter","referral","bing"]
SRC_W=[0.45,0.18,0.12,0.08,0.07,0.06,0.04]
MEDIUMS=["organic","cpc","email","social","none","referral"]
MED_W=[0.5,0.18,0.1,0.12,0.06,0.04]
DEVICES=["desktop","mobile","tablet"]
DEV_W=[0.55,0.4,0.05]

TZ = timezone.utc

random.seed(42)

def _rand_date(days_back=180):
    now = datetime.now(TZ)
    start = now - timedelta(days=days_back)
    dt = start + timedelta(seconds=random.randint(0, days_back*24*3600))
    return dt

class DataStore:
    def __init__(self):
        self.customers=[]
        self.payments=[]
        self.sessions=[]
        self._generate()

    def _generate(self):
        # customers
        for i in range(1000):
            cid=str(uuid.uuid4())
            signup=_rand_date(360)
            ctry=random.choices(COUNTRIES,COUNTRY_W)[0]
            ind=random.choices(INDUSTRIES,IND_W)[0]
            size=random.choices(["1-10","11-50","51-200","201-500","500+"],[0.35,0.3,0.2,0.1,0.05])[0]
            churn=random.random()<0.18
            self.customers.append({
                "customer_id":cid,
                "company_name":f"Company {i:04d}",
                "country":ctry,
                "industry":ind,
                "company_size":size,
                "signup_date":signup.isoformat(),
                "updated_at":signup.isoformat(),
                "is_churned":churn
            })
        # payments
        for _ in range(10000):
            c=random.choice(self.customers)
            product=random.choices(PRODUCTS, weights={
                "E-commerce":[0.4,0.35,0.05,0.1,0.1],
                "SaaS":[0.25,0.4,0.15,0.1,0.1],
                "Consulting":[0.35,0.35,0.1,0.1,0.1],
                "Education":[0.45,0.3,0.05,0.1,0.1],
                "Health":[0.3,0.35,0.15,0.1,0.1],
                "Finance":[0.25,0.4,0.2,0.075,0.075]
            }[c["industry"]])[0]
            base=PRICES[product]
            seat=1
            if product in ["Pro","Enterprise"] and random.random()<0.25:
                seat=random.choices([2,3,4,5],[0.4,0.3,0.2,0.1])[0]
            amount=base*seat
            created=_rand_date(180)
            status=random.choices(STATUSES,STAT_W)[0]
            fee=round(amount*0.029+0.3,2)
            refunded=0.0
            if status=="refunded":
                refunded=round(amount*random.uniform(0.25,1.0),2)
            self.payments.append({
                "payment_id":str(uuid.uuid4()),
                "customer_id":c["customer_id"],
                "product":product,
                "amount":float(amount),
                "currency":"USD" if c["country"]!="DE" else "EUR",
                "status":status,
                "refunded_amount":refunded,
                "fee":fee,
                "payment_method":random.choices(PAYMENT_METHODS,PM_W)[0],
                "country":c["country"],
                "created_at":created.isoformat(),
                "updated_at":created.isoformat()
            })
        # sessions
        for _ in range(30000):
            dt=_rand_date(180)
            # downweight weekends
            if dt.weekday() in (5,6) and random.random()<0.2:
                continue
            cust=None
            if random.random()<0.35:
                cust=random.choice(self.customers)["customer_id"]
            source=random.choices(SOURCES,SRC_W)[0]
            medium=random.choices(MEDIUMS,MED_W)[0]
            device=random.choices(DEVICES,DEV_W)[0]
            pageviews=max(1,int(random.expovariate(1/2)))
            duration=int(random.gammavariate(2,45))
            bounced = 1 if (pageviews == 1 and duration < 10) else 0 # boolean
            conv_prob = (0.02 
                    + (0.02 if medium=="cpc" else 0) 
                    + (0.03 if medium=="email" else 0)
                    + (0.01 if device=="desktop" else 0) 
                    + (0.01 if pageviews>=3 else 0)
                    ) 
            converted = 1 if conv_prob > random.random() else 0 

            self.sessions.append({
                "session_id":str(uuid.uuid4()),
                "customer_id":cust or None,
                "source":source,
                "medium":medium,
                "campaign":"" if medium in ("organic","none","referral") else "product_launch",
                "device":device,
                "country":random.choices(COUNTRIES,COUNTRY_W)[0],
                "pageviews":pageviews,
                "session_duration_s":duration,
                "bounced":bounced,
                "converted":converted,
                "session_start":dt.isoformat(),
                "updated_at":dt.isoformat()
            })
