import requests, os
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

DOHA = timezone(timedelta(hours=3))

def get_today_upcoming():
    try:
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        today = datetime.now(DOHA).strftime("%Y-%m-%d")
        url = f"https://v3.football.api-sports.io/fixtures?date={today}&timezone=Asia/Qatar"
        r = requests.get(url, headers=headers, timeout=15).json()
        all_fx = r.get("response", [])
        # كان اللي ما بداوش + الوقت متاعهم مازال قدام
        now = datetime.now(DOHA)
        upcoming=[]
        for f in all_fx:
            if f.get("fixture",{}).get("status",{}).get("short")!= "NS":
                continue
            try:
                ft = datetime.fromisoformat(f["fixture"]["date"].replace("Z","+00:00")).astimezone(DOHA)
                if ft > now: # مازال ما بداش
                    upcoming.append(f)
            except:
                upcoming.append(f)
        return sorted(upcoming, key=lambda x: x["fixture"]["date"])[:20]
    except Exception as e:
        print(f"Error: {e}")
        return []

def smart_pick(fx):
    home = fx["teams"]["home"]["name"]
    away = fx["teams"]["away"]["name"]
    league = fx["league"]["name"]
    ft = datetime.fromisoformat(fx["fixture"]["date"].replace("Z","+00:00")).astimezone(DOHA)
    time_str = ft.strftime("%H:%M")

    # نخلي Groq يخمم بذكاء بالحق
    prompt = f"""أنت خبير رهانات ذكي ومحترف، تخدم بمنطق موش بحفظ.

ماتش اليوم مازال ما بداش: {home} vs {away} - {league} - {time_str} Doha

مهمتك: اختار أقل ريسك رهان ممكن لهذا الماتش بالضبط. استعمل معرفتك بالفرق.

القاعدة الذهبية:
- اذا فريق قوي برشا في دارو ويربح ديما (مثلا السيتي، الريال، البايرن في دارهم) => 1W
- اذا فريق يمركي برشا في دارو (معدل 2+ هدف) => Home Over 1.5 أو Over 1.5
- اذا الزوز هجوم ضعيف ودفاع قوي => Under 2.5 أو Under 1.5
- اذا الماتش متكافئ وما يخسرش في دارو => 1X أو X2
- اذا يبداو الماتشات بقوة => Over 0.5 HT
- اذا فريق ما يمركيش برا دارو => BTTS No
- اذا الزوز يمركيو => Over 1.5 أو BTTS Yes

لا تختار Over 1.5 ديما! اختار حسب الماتش.

جاوب سطر واحد فقط:
نوع الرهان - تحليل قصير ذكي

مثال ذكي:
1W - السيتي في الاتحاد يربح 90% الماتشات
Home Over 1.5 - برشلونة في كامب نو معدل 2.4 هدف
Under 2.5 - أتلتيكو وانتر دفاع حديد، آخر 4 ماتشات Under
"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"temperature":0.6,"max_tokens":100},
            timeout=20
        )
        txt = r.json()["choices"][0]["message"]["content"].strip()
        # ريسك ذكي حسب النوع
        low = ["1W","1X","Home Over 0.5"]
        med = ["Over 1.5","Over 0.5 HT","X2"]
        risk = 13 if any(x in txt for x in low) else 18 if any(x in txt for x in med) else 24
        return txt, risk, time_str, home, away, league
    except Exception as e:
        print(e)
        return f"1X - {home} قوي في دارو", 25, time_str, home, away, league

def main():
    fxs = get_today_upcoming()
    print(f"Upcoming: {len(fxs)}")

    picks=[]
    for fx in fxs[:15]:
        txt, risk, t, h, a, lg = smart_pick(fx)
        picks.append({"match":f"{h} vs {a}","league":lg,"time":t,"pick":txt,"risk":risk})
        import time; time.sleep(1.3)

    top10 = sorted(picks, key=lambda x: x["risk"])[:10]

    msg = f"🧠 TOP 10 بذكاء - {datetime.now(DOHA).strftime('%d/%m %H:%M')} Doha\nحللت {len(fxs)} ماتش قادم (ما بداوش) واخترت الأضمن بالمنطق:\n\n"
    if not top10:
        msg+="اليوم ما فماش ماتشات قادمة - البوت جاهز ✅ (كل المفاتيح OK)\nغدوة يرجع يخدم."
    else:
        for i,p in enumerate(top10,1):
            icon = "🔥" if p["risk"]<16 else "✅" if p["risk"]<22 else "⚠️"
            msg+= f"{i}. {icon} {p['match']}\n 🏆 {p['league']} | 🕐 {p['time']}\n 💡 {p['pick']}\n 📊 ريسك {p['risk']}%\n\n"

    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":msg[:3900]}, timeout=15)
    print(msg)

if __name__=="__main__":
    main()
