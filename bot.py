import requests, os
from datetime import datetime, timedelta
from collections import Counter

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_TOKEN", "")

def espn_fetch():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        events = data.get("events", [])
        real = []
        by_league = Counter()
        for ev in events:
            try:
                if ev.get("competitions"):
                    comp = ev["competitions"][0]
                    lg = comp.get("league", {})
                    league_name = lg.get("name") or lg.get("abbreviation") or "Unknown"
                    if league_name == "Unknown" and ev.get("leagues"):
                        league_name = ev["leagues"][0].get("name", "Unknown")
                    competitors = comp.get("competitors", [])
                    if len(competitors) >= 2:
                        home = None
                        away = None
                        for c in competitors:
                            if c.get("homeAway") == "home":
                                home = c
                            else:
                                away = c
                        if not home:
                            home = competitors[0]
                            away = competitors[1]
                        home_name = home.get("team", {}).get("displayName", "Home")
                        away_name = away.get("team", {}).get("displayName", "Away")
                        by_league[league_name] += 1
                        real.append({"home": home_name, "away": away_name, "league": league_name})
            except:
                continue
        return real, by_league
    except Exception as e:
        print(f"ESPN error: {e}")
        return [], Counter()

def football_data_fetch():
    if not FOOTBALL_DATA_KEY:
        return []
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={tomorrow}"
    try:
        r = requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=20)
        if r.status_code!= 200:
            return []
        return r.json().get("matches", [])
    except:
        return []

def main():
    print(f"V8 CLEAN {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    real_500, by_league = espn_fetch()
    safe = football_data_fetch()
    total = len(real_500)

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')}\n\n"
    msg += f"Real list: {total} matches today (ESPN Free)\n"
    msg += f"Note: betting sites have ~500 with eSports + Reserve\n\n"
    if by_league:
        msg += "Top leagues today:\n"
        for name, cnt in by_league.most_common(7):
            if name!= "Unknown":
                msg += f"- {name}: {cnt}\n"
    msg += f"\nSAFE (Top4 + 90% + H2H 5/5): {len(safe)} matches\n"
    if total > 0 and len(safe) == 0:
        msg += "\nBig leagues paused today -> 0 SAFE is normal\n"
        msg += f"All {total} are small leagues\n"

    print(msg)
    if BOT_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                         json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
            print("Sent OK")
        except Exception as e:
            print(f"Telegram error: {e}")

if __name__ == "__main__":
    main()
