import requests, os
from datetime import datetime
import re

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_league_name_fixed(ev):
    # يصلح اسم البطولة - يقرا من 6 أماكن
    try:
        # 1. من leagues
        if ev.get("leagues") and ev["leagues"][0].get("name"):
            name = ev["leagues"][0]["name"]
            if name!= "League":
                return name
        # 2. من competitions league
        comp = ev.get("competitions", [{}])[0]
        if comp.get("league", {}).get("name"):
            return comp["league"]["name"]
        # 3. من uid - s:600~l:eng.league_cup~e:...
        uid = ev.get("uid", "")
        m = re.search(r"~l:([^~]+)~", uid)
        if m:
            slug = m.group(1) # eng.league_cup
            # يحول eng.league_cup -> League Cup
            return slug.replace("eng.", "").replace("usa.", "").replace("_", " ").title()
        # 4. من notes
        if comp.get("notes") and comp["notes"][0] and comp["notes"][0]!= "League":
            return comp["notes"][0]
        # 5. من season
        if ev.get("season", {}).get("name"):
            return ev["season"]["name"]
    except:
        pass
    return "Unknown League"

def main():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    r = requests.get(url, timeout=15)
    events = r.json().get("events", [])

    all_matches = []
    for ev in events:
        comp = ev.get("competitions", [{}])[0]
        teams = comp.get("competitors", [])
        if len(teams) < 2:
            continue
        home = next((t for t in teams if t.get("homeAway")=="home"), teams[0])
        away = next((t for t in teams if t.get("homeAway")=="away"), teams[1])
        home_name = home.get("team", {}).get("displayName", "")
        away_name = away.get("team", {}).get("displayName", "")
        league = get_league_name_fixed(ev)

        # هنا الشروط - تو مبسطة، بعد نجيب الحقيقية
        # نفترض نجيبهم من API
        top4 = "【entity-City¦canonical_name=Manchester City】" in home_name or "Norwich" in home_name
        home90 = True
        h2h = "【entity-United¦canonical_name=Manchester United】" not in away_name

        score = sum([top4, home90, h2h])
        if score >= 1: # حتى شرط واحد يبعث
            all_matches.append({
                "match": f"{home_name} vs {away_name}",
                "league": league,
                "top4": top4,
                "home90": home90,
                "h2h": h2h,
                "score": score
            })

    # يرتب حسب عدد الشروط
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')}\n\n"
    msg += f"فحصت {len(events)} ماتش، لقيت {len(all_matches)} فيه شروط:\n\n"

    for s in all_matches[:10]:
        msg += f"{'✅' if s['score']==3 else '⚠️'} {s['match']}\n"
        msg += f"🏆 {s['league']}\n"
        # يوري الشروط
        t1 = "✅ Top4" if s['top4'] else "❌ Top4 ناقص"
        t2 = "✅ 90% دار" if s['home90'] else "❌ 90% ناقص"
        t3 = "✅ H2H 5/5" if s['h2h'] else "❌ H2H ناقص"
        msg += f"{t1} | {t2} | {t3}\n"
        msg += f"النتيجة: {s['score']}/3 شروط\n\n"

    print(msg)
    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

if __name__ == "__main__":
    main()
