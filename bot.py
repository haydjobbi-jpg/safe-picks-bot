import requests, os
from datetime import datetime, timezone, timedelta

BOT = os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("CHAT_ID")
GROQ = os.environ.get("GROQ_API_KEY")
DOHA = timezone(timedelta(hours=3))

# 1. يجيب ماتشات اليوم - قد ما كان عددهم وأي بطولة
def get_today():
    today = datetime.now(DOHA).strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    r = requests.get(url, timeout=15).json()
    matches = []
    for ev in r.get("events", []):
        if ev["status"]["type"]["state"]!= "pre": continue
        comp = ev["competitions"][0]
        home = comp["competitors"][0]["team"]["displayName"] if comp["competitors"][0]["homeAway"]=="home" else comp["competitors"][1]["team"]["displayName"]
        away = comp["competitors"][1]["team"]["displayName"] if comp["competitors"][0]["homeAway"]=="home" else comp["competitors"][0]["team"]["displayName"]
        league = ev.get("leagues", [{}])[0].get("name", "League") if ev.get("leagues") else comp.get("notes", [{}])[0].get("headline", "League")
        dt = datetime.fromisoformat(ev["date"].replace("Z","+00:00")).astimezone(DOHA)
        matches.append({"m": f"{home} vs {away}", "lg": league, "t": dt.strftime("%H:%M"), "home": home, "away": away})
    return matches[:30]

# 2. يخمم بذكاء
def think(m):
    prompt = f"ماتش: {m['home']} vs {m['away']} - {m['lg']}. اختار أقل ريسك: 1, 1X, X2, Over 1.5, Under 2.5, Home Over 0.5. جاوب: الرهان - سبب قصير"
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ}", "Content-Type": "application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":60}, timeout=15)
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return f"1X - {m['home']} ما يخسرش في دارو"

# 3. يبعث TOP 10
def main():
    games = get_today()
    msg = f"🔥 TOP 10 - {datetime.now(DOHA).strftime('%d/%m %H:%M')} Doha\nمن {len(games)} ماتش اليوم:\n\n"
    for i,g in enumerate(games[:10],1):
        pick = think(g)
        msg += f"{i}. {g['m']}\n 🏆 {g['lg']} | 🕐 {g['t']}\n 💡 {pick}\n\n"
        import time; time.sleep(1)

    requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", json={"chat_id":CHAT,"text":msg[:3500]})
    print(msg)

if __name__=="__main__":
    main()
