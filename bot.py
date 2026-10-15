import requests, os
from datetime import datetime, timezone, timedelta
import time

BOT = os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("CHAT_ID")
GROQ = os.environ.get("GROQ_API_KEY")
DOHA = timezone(timedelta(hours=3))

def get_today():
    today = datetime.now(DOHA).strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    r = requests.get(url, timeout=15).json()
    matches = []
    for ev in r.get("events", []):
        if ev.get("status",{}).get("type",{}).get("state","")!= "pre":
            continue
        comp = ev.get("competitions", [{}])[0]
        comps = comp.get("competitors", [])
        if len(comps) < 2: continue

        # آمن 100%
        home = comps[0].get("team",{}).get("displayName","Home")
        away = comps[1].get("team",{}).get("displayName","Away")
        # احتياط إذا home/away مقلوبين
        if comps[0].get("homeAway") == "away":
            home, away = away, home

        # league آمن - ما يطيحش
        league = "League"
        try:
            if ev.get("leagues") and len(ev.get("leagues"))>0:
                league = ev["leagues"][0].get("name","League")
            elif comp.get("notes") and len(comp.get("notes"))>0:
                league = comp["notes"][0].get("headline","League")
            else:
                league = comp.get("type",{}).get("abbreviation","League")
        except:
            league = "League"

        dt = datetime.fromisoformat(ev["date"].replace("Z","+00:00")).astimezone(DOHA)
        matches.append({"m": f"{home} vs {away}", "lg": league, "t": dt.strftime("%H:%M"), "home": home, "away": away})
    return matches[:30]

def think(m):
    prompt = f"ماتش: {m['home']} vs {m['away']} - {m['lg']}. اختار أقل ريسك: 1, 1X, X2, Over 1.5, Under 2.5, Home Over 0.5. جاوب: الرهان - سبب قصير"
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ}", "Content-Type": "application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":60}, timeout=15)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return f"1X - {m['home']} ما يخسرش في دارو"

def main():
    games = get_today()
    print(f"Found {len(games)} games")
    msg = f"🔥 TOP 10 - {datetime.now(DOHA).strftime('%d/%m %H:%M')} Doha\nمن {len(games)} ماتش اليوم:\n\n"
    if not games:
        msg += "ما فماش ماتشات اليوم - API فاضي"
    else:
        for i,g in enumerate(games[:10],1):
            pick = think(g)
            msg += f"{i}. {g['m']}\n 🏆 {g['lg']} | 🕐 {g['t']}\n 💡 {pick}\n\n"
            time.sleep(1.1)

    if BOT and CHAT:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", json={"chat_id":CHAT,"text":msg[:3500]}, timeout=15)
    print(msg)

if __name__=="__main__":
    main()
