import requests, os
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_all_with_small():
    today = datetime.now().strftime("%Y-%m-%d")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "Accept": "application/json"
    }
    try:
        # 【entity-SofaScore¦canonical_name=SofaScore】 يجيب 500+ ماتش بالصغار
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
        r = requests.get(url, headers=headers, timeout=20)
        data = r.json()
        events = data.get("events", [])
        matches = []
        for ev in events:
            tour = ev.get("tournament", {})
            cat = tour.get("category", {}).get("name", "")
            tname = tour.get("name", "")
            league = f"{cat} {tname}".strip()
            home = ev.get("homeTeam", {}).get("name", "")
            away = ev.get("awayTeam", {}).get("name", "")
            # نحب الصغار برك
            if any(x in league.lower() for x in ["malta", "estonia", "lithuania", "latvia", "armenia", "georgia", "cyprus", "iceland", "faroe", "luxembourg", "andorra", "gibraltar", "wales", "northern ireland", "algeria", "tunisia", "morocco", "qatar", "kuwait", "bahrain", "second", "third", "u19", "u21", "youth", "women"]):
                matches.append({"match": f"{home} vs {away}", "league": league, "is_small": True})
            else:
                matches.append({"match": f"{home} vs {away}", "league": league, "is_small": False})
        return matches
    except Exception as e:
        print(f"SofaScore error: {e}")
        # fallback ESPN
        try:
            url2 = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today.replace('-','')}"
            r2 = requests.get(url2, timeout=15)
            events = r2.json().get("events", [])
            matches = []
            for ev in events:
                comp = ev.get("competitions", [{}])[0]
                teams = comp.get("competitors", [])
                if len(teams)>=2:
                    h = teams[0].get("team", {}).get("displayName", "")
                    a = teams[1].get("team", {}).get("displayName", "")
                    matches.append({"match": f"{h} vs {a}", "league": "Major League", "is_small": False})
            return matches
        except:
            return []

def main():
    all_m = get_all_with_small()
    small = [m for m in all_m if m["is_small"]]
    big = [m for m in all_m if not m["is_small"]]

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')}\n\n"
    msg += f"فحصت {len(all_m)} ماتش:\n"
    msg += f"- {len(big)} بطولات كبار\n"
    msg += f"- {len(small)} بطولات صغار ✅\n\n"

    if small:
        msg += "ماتشات صغار اليوم:\n"
        for s in small[:15]:
            msg += f"🔹 {s['match']}\n"
            msg += f" 🏆 {s['league']}\n"
        if len(small)>15:
            msg += f"... و {len(small)-15} ماتش صغار اخرين\n"
    else:
        msg += "SofaScore بلوكي - نحاول طريقة اخرى...\n"
        for b in big[:10]:
            msg += f"- {b['match']} ({b['league']})\n"

    print(msg)
    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

if __name__ == "__main__":
    main()
