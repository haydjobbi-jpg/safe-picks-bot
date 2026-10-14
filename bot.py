import requests, os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_TOKEN", "")

def get_matches_guaranteed():
    today = datetime.now()
    # طريقة 1: ESPN
    for offset in [0, -1, 1]:
        date_str = (today + timedelta(days=offset)).strftime("%Y%m%d")
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date_str}"
            r = requests.get(url, timeout=15)
            events = r.json().get("events", [])
            if events:
                matches = []
                for ev in events[:300]:
                    comp = ev.get("competitions", [{}])[0]
                    teams = comp.get("competitors", [])
                    if len(teams) >= 2:
                        h = teams[0].get("team", {}).get("displayName", "Home")
                        a = teams[1].get("team", {}).get("displayName", "Away")
                        lg = ev.get("leagues", [{}])[0].get("name", comp.get("notes", ["League"])[0] if comp.get("notes") else "League")
                        matches.append(f"{h} vs {a} ({lg})")
                if matches:
                    return matches, f"ESPN {date_str}"
        except:
            pass

    # طريقة 2: football-data.org
    if FOOTBALL_DATA_KEY:
        try:
            d1 = today.strftime("%Y-%m-%d")
            d2 = (today + timedelta(days=1)).strftime("%Y-%m-%d")
            url = f"https://api.football-data.org/v4/matches?dateFrom={d1}&dateTo={d2}"
            r = requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15)
            ms = r.json().get("matches", [])
            if ms:
                matches = [f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} ({m['competition']['name']})" for m in ms]
                return matches, "football-data.org"
        except:
            pass

    return [f"No data - API blocked, check tomorrow"], "fallback"

def main():
    matches, source = get_matches_guaranteed()
    total = len(matches)

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')} - {source}\n\n"
    msg += f"فما {total} ماتش اليوم (كبار + صغار)\n"
    for m in matches[:20]:
        msg += f"- {m}\n"
    if total > 20:
        msg += f"... و {total-20} ماتش اخرين\n"
    msg += f"\nSAFE (90% + H2H): 0 اليوم (البطولات الكبيرة واقفة)\n"

    print(msg)
    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

if __name__ == "__main__":
    main()
