import os, requests
from datetime import datetime, timedelta
BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
API_KEY=os.getenv("API_FOOTBALL_KEY")
tomorrow=(datetime.utcnow()+timedelta(hours=3,days=1)).strftime("%Y-%m-%d")
url=f"https://v3.football.api-sports.io/fixtures?date={tomorrow}"
headers={"x-apisports-key":API_KEY}
data=requests.get(url,headers=headers,timeout=20).json().get("response",[])
picks=[]
for m in data:
 if m["league"]["id"] in [39,140,135,78,61]:
  picks.append(f"⚽ {m['league']['name']}\n{m['teams']['home']['name']} vs {m['teams']['away']['name']}\n✅ Safe: Under 3.5 + 1X\n")
  if len(picks)>=5:
   break
if not picks:
 picks=["ما فماش ماتشات قوية غدوة"]
msg=f"🔐 SAFE PICKS - {tomorrow}\n00:30 Doha\n\n"+"\n".join(picks)
requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg})
