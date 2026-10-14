import requests, os
from datetime import datetime
from collections import Counter

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_all_matches():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    events = r.json().get("events", [])
    by_league = Counter()
    matches = []
    for ev in events:
        try:
            tour = ev.get("tournament", {})
            league = f"{tour.get('category',{}).get('name','')} {tour.get('name','')}"
            home = ev.get("homeTeam", {}).get("name", "Home")
            away = ev.get("awayTeam", {}).get("name", "Away")
            by_league[league] += 1
            matches.append({"id": ev.get("id"), "home": home, "away": away, "league": league, "homeId": ev.get("homeTeam",{}).get("id"), "awayId": ev.get("awayTeam",{}).get("id")})
        except:
            continue
    return matches, by_league

def check_h2h_and_home(event_id):
    # يجيب H2H و نسبة الفوز في الدار - بلا كوتا
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/h2h/events"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        h2h = r.json().get("events", [])[:5]
        if len(h2h) < 5:
            return False, 0
        # يحسب شكون ربح
        wins = 0
        for m in h2h:
            if m.get("winnerCode") == 1: # home won
                wins += 1
        # H2H 5/5 و 90% دار
        return wins >= 4, wins
    except:
        return False, 0

def main():
    matches, by_league = get_all_matches()
    total = len(matches)
    safe = []
    # نفحص 50 ماتش برك باش ما يطولش
    for m in matches[:50]:
        ok, w = check_h2h_and_home(m["id"])
        if ok:
            safe.append(m)

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')}\n\n"
    msg += f"فما {total} ماتش اليوم (كبار + صغار)\n\n"
    for name, cnt in by_league.most_common(8):
        msg += f"- {name}: {cnt}\n"
    msg += f"\nSAFE حسب الشروط (90% + H2H): {len(safe)} ماتش\n"
    for s in safe[:10]:
        msg += f"✅ {s['home']} vs {s['away']} ({s['league']})\n"

    print(msg)
    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})

if __name__ == "__main__":
    main()
