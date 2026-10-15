import requests, os
from datetime import datetime, timedelta, timezone
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
DOHA = timezone(timedelta(hours=3))

def get_from_api_football():
    try:
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        today = datetime.now(DOHA).strftime("%Y-%m-%d")
        url = f"https://v3.football.api-sports.io/fixtures?date={today}"
        r = requests.get(url, headers=headers, timeout=15).json()
        all_fx = r.get("response", [])
        if len(all_fx)==0:
            print("API Football returned 0 - quota maybe finished")
            return []
        now = datetime.now(DOHA)
        up=[]
        for f in all_fx:
            if f["fixture"]["status"]["short"]!="NS": continue
            try:
                ft = datetime.fromisoformat(f["fixture"]["date"].replace("Z","+00:00")).astimezone(DOHA)
                if ft > now - timedelta(minutes=30):
                    up.append({"home": f["teams"]["home"]["name"], "away": f["teams"]["away"]["name"], "league": f["league"]["name"], "time": ft.strftime("%H:%M"), "date": f["fixture"]["date"]})
            except: pass
        return up[:35]
    except Exception as e:
        print(f"API Football error: {e}")
        return []

def get_from_espn_fallback():
    # خطة B - مجاني وما يوفاش
    try:
        today = datetime.now(DOHA).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
        r = requests.get(url, timeout=15).json()
        events = r.get("events", [])
        up=[]
        now = datetime.now(DOHA)
        for ev in events:
            status = ev.get("status",{}).get("type",{}).get("state","")
            if status in ["final","in"]: continue # كان اللي ما بداوش
            comp = ev.get("competitions",[{}])[0]
            teams = comp.get("competitors",[])
            if len(teams)<2: continue
            h = next((t for t in teams if t.get("homeAway")=="home"), teams[0])
            a = next((t for t in teams if t.get("homeAway")=="away"), teams[1])
            home = h.get("team",{}).get("displayName","Home")
            away = a.get("team",{}).get("displayName","Away")
            league = ev.get("leagues",[{}])[0].get("name","League") if ev.get("leagues") else "League"
            try:
                dt = datetime.fromisoformat(ev.get("date","").replace("Z","+00:00")).astimezone(DOHA)
                if dt < now - timedelta(minutes=30): continue
                t = dt.strftime("%H:%M")
            except:
                t = "?"
            up.append({"home": home, "away": away, "league": league, "time": t, "date": ev.get("date")})
        print(f"ESPN fallback returned {len(up)}")
        return up[:35]
    except Exception as e:
        print(f"ESPN error: {e}")
        return []

def get_matches():
    # جرب API-Football أول، كان 0 جرب ESPN
    matches = get_from_api_football()
    if len(matches)==0:
        print("Trying ESPN fallback...")
        matches = get_from_espn_fallback()
    return matches

def ai_pick(m):
    home=m["home"]; away=m["away"]; league=m["league"]; t=m["time"]
    prompt = f"""خبير رهانات ذكي. ماتش: {home} vs {away} - {league} - {t} Doha

اختار أقل ريسك من: 1, X, 2, 1X, X2, Over 0.5/1.5/2.5/3.5, Under 1.5/2.5/3.5, Over 0.5 HT, Home Over 0.5/1.5, BTTS Yes/No

جاوب سطر واحد: نوع الرهان - سبب ذكي قصير
"""
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":90}, timeout=20)
        txt = r.json()["choices"][0]["message"]["content"].strip()
        risk = 13 if "1W" in txt or "1X" in txt else 16 if "Home Over" in txt else 18 if "Over 1.5" in txt else 20 if "Under" in txt else 25
        return txt, risk
    except:
        return f"1X - {home} قوي في دارو", 22

def main():
    fxs = get_matches()
    print(f"Final matches: {len(fxs)}")

    picks=[]
    for m in fxs[:25]:
        txt, risk = ai_pick(m)
        picks.append({"m": f"{m['home']} vs {m['away']}", "lg": m["league"], "t": m["time"], "pick": txt, "risk": risk})
        time.sleep(1.1)

    top10 = sorted(picks, key=lambda x: x["risk"])[:10]
    msg = f"🔥 TOP 10 - أي بطولة - {datetime.now(DOHA).strftime('%d/%m %H:%M')} Doha\nمن {len(fxs)} ماتش اليوم:\n\n"
    if not top10:
        msg+="اليوم ما فماش ماتشات قادمة - جرب بعد شوية. API_FOOTBALL_KEY يرجع 03:00 الفجر."
    else:
        for i,p in enumerate(top10,1):
            icon="🔥" if p["risk"]<15 else "✅"
            msg+=f"{i}. {icon} {p['m']}\n 🏆 {p['lg']} | 🕐 {p['t']}\n 💡 {p['pick']}\n 📊 {p['risk']}%\n\n"

    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg[:3900]}, timeout=15)
    print(msg)

if __name__=="__main__":
    main()
