import requests, os
from datetime import datetime, timedelta, timezone
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
DOHA = timezone(timedelta(hours=3))

# ترتيب البطولات - الأهم أول
PRIORITY = {
    "Europa League": 100, "Conference League": 95, "Europa": 100,
    "Copa Libertadores": 85, "Champions League": 100,
    "AFC Champions": 80, "Liga Profesional": 70,
    "Premier League": 90, "La Liga": 90, "Serie A": 90, "Bundesliga": 90,
    "Ligue 2": 30, "Reserve": 10, "U20": 15, "U17": 15, "Friendly": 5
}

def get_priority(league_name):
    for k,v in PRIORITY.items():
        if k.lower() in league_name.lower():
            return v
    return 50

def get_matches():
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    today = datetime.now(DOHA).strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    try:
        r = requests.get(url, headers=headers, timeout=20).json()
        all_fx = r.get("response", [])
        now = datetime.now(DOHA)
        upcoming = []
        for f in all_fx:
            if f["fixture"]["status"]["short"]!= "NS":
                continue
            try:
                ft = datetime.fromisoformat(f["fixture"]["date"].replace("Z","+00:00")).astimezone(DOHA)
                if ft > now - timedelta(minutes=30):
                    upcoming.append(f)
            except:
                upcoming.append(f)
        # رتب حسب الأهمية وخود 30
        upcoming = sorted(upcoming, key=lambda x: get_priority(x["league"]["name"]), reverse=True)
        return upcoming[:30]
    except Exception as e:
        print(f"Error API: {e}")
        return []

def ai_pick(fx):
    home = fx["teams"]["home"]["name"]
    away = fx["teams"]["away"]["name"]
    league = fx["league"]["name"]
    ft = datetime.fromisoformat(fx["fixture"]["date"].replace("Z","+00:00")).astimezone(DOHA)
    t = ft.strftime("%H:%M")

    prompt = f"""أنت خبير رهانات ذكي جدا. حلل هذا الماتش بذكاء:

{home} vs {away} - {league} - {t} Doha (اليوم)

اختار أقل ريسك من هذه الأسواق: 1, X, 2, 1X, X2, 12, Over 0.5/1.5/2.5/3.5, Under 1.5/2.5/3.5, Over 0.5 HT, Over 1.5 HT, Home Over 0.5/1.5, Away Over 0.5, BTTS Yes/No

فكر بمنطق:
- فريق قوي في دارو vs ضعيف => 1W
- متكافئ في دارو => 1X
- هجوم قوي => Home Over 1.5 أو Over 1.5
- دفاع حديد => Under 2.5
- يبداو قويين => Over 0.5 HT
- ما يمركيش برا => BTTS No

جاوب سطر واحد فقط: نوع الرهان - سبب ذكي قصير
مثال: 1W - السيتي يربح 90% في الاتحاد
"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 100},
            timeout=20
        )
        txt = r.json()["choices"][0]["message"]["content"].strip().replace("\n"," ")
        if "1W" in txt or "1X" in txt: risk = 13
        elif "Home Over" in txt: risk = 16
        elif "Over 1.5" in txt: risk = 18
        elif "Under" in txt: risk = 20
        elif "Over 0.5 HT" in txt: risk = 17
        else: risk = 25
        return txt, risk, t, home, away, league
    except Exception as e:
        print(e)
        return f"1X - {home} قوي في دارو", 22, t, home, away, league

def main():
    fxs = get_matches()
    print(f"Today found {len(fxs)} important matches")

    picks = []
    for fx in fxs[:20]:
        txt, risk, t, h, a, lg = ai_pick(fx)
        picks.append({"m": f"{h} vs {a}", "lg": lg, "t": t, "pick": txt, "risk": risk})
        time.sleep(1.2)

    top10 = sorted(picks, key=lambda x: x["risk"])[:10]

    msg = f"🔥 TOP 10 بذكاء - {datetime.now(DOHA).strftime('%d/%m %H:%M')} Doha\nمن {len(fxs)} ماتش اليوم (من أصل 181):\n\n"
    if not top10:
        msg += "اليوم API ما رجعش - تأكد من API_FOOTBALL_KEY أو جرب غدوة."
    else:
        for i,p in enumerate(top10,1):
            icon = "🔥" if p["risk"]<15 else "✅"
            msg += f"{i}. {icon} {p['m']}\n 🏆 {p['lg']} | 🕐 {p['t']}\n 💡 {p['pick']}\n 📊 {p['risk']}%\n\n"

    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg[:3900]}, timeout=15)
    print(msg)

if __name__ == "__main__":
    main()
