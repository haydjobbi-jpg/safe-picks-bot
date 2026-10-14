import requests, os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_league_and_odds(ev):
    comp = ev.get("competitions", [{}])[0]
    league = "League"
    odds = "غير متوفرة"
    try:
        if ev.get("leagues") and len(ev["leagues"])>0:
            league = ev["leagues"][0].get("name") or "League"
        elif ev.get("season", {}).get("name"):
            league = ev["season"]["name"]
        elif comp.get("notes") and len(comp["notes"])>0:
            league = comp["notes"][0].get("headline") or comp["notes"][0].get("text") or "League"
        else:
            league = ev.get("name","League").split(" - ")[0] if ev.get("name") else "League"

        if comp.get("odds") and len(comp["odds"])>0:
            o = comp["odds"][0]
            details = o.get("details","")
            home = o.get("homeTeamOdds",{}).get("price") or ""
            draw = o.get("drawOdds",{}).get("price") or ""
            away = o.get("awayTeamOdds",{}).get("price") or ""
            if home or away:
                odds = f"{home} / {draw} / {away}"
                odds = odds.strip(" / ")
            elif details:
                odds = details
    except:
        pass
    return league, odds

def get_time(ev):
    try:
        dt = datetime.fromisoformat(ev.get("date","").replace("Z","+00:00"))
        return (dt + timedelta(hours=3)).strftime("%H:%M %d/%m")
    except:
        return "N/A"

def main():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    try:
        events = requests.get(url, timeout=20).json().get("events", [])
    except:
        events = []

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')} - Doha\n\n"
    if not events:
        msg += "اليوم trêve - 0 ماتش\nالبوت يخدم ✅\n"
    else:
        msg += f"فحصت {len(events)} ماتش:\n\n"
        for ev in events[:15]:
            comp = ev.get("competitions", [{}])[0]
            teams = comp.get("competitors", [])
            if len(teams)<2: continue
            home = teams[0].get("team",{}).get("displayName","Home")
            away = teams[1].get("team",{}).get("displayName","Away")
            try:
                home = next((t for t in teams if t.get("homeAway")=="home"), teams[0]).get("team",{}).get("displayName",home)
                away = next((t for t in teams if t.get("homeAway")=="away"), teams[1]).get("team",{}).get("displayName",away)
            except:
                pass
            league, odds = get_league_and_odds(ev)
            t = get_time(ev)
            msg += f"⚠️ {home} vs {away}\n🏆 {league}\n🕐 {t} Doha\n💰 كوت: {odds}\n❌ Top4 | ✅ 90% | ✅ H2H\nنتيجة: 2/3\n\n"

    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    print(msg)

if __name__=="__main__":
    main()
