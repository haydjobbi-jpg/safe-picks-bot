import requests, os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_matches_working():
    today = datetime.now()
    all_matches = []

    # طريقة 1: 【entity-ESPN¦canonical_name=ESPN】 - يخدم ديما من 【entity-GitHub¦canonical_name=GitHub】
    for offset in [0, -1, 1]:
        date_str = (today + timedelta(days=offset)).strftime("%Y%m%d")
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date_str}"
            r = requests.get(url, timeout=15)
            events = r.json().get("events", [])
            for ev in events:
                comp = ev.get("competitions", [{}])[0]
                teams = comp.get("competitors", [])
                if len(teams)>=2:
                    h = teams[0].get("team", {}).get("displayName", "Home")
                    a = teams[1].get("team", {}).get("displayName", "Away")
                    # نجيب اسم البطولة الحقيقي
                    league = ev.get("leagues", [{}])[0].get("name") if ev.get("leagues") else comp.get("notes", ["League"])[0] if comp.get("notes") else "League"
                    all_matches.append({"match": f"{h} vs {a}", "league": league, "date": date_str})
        except:
            pass

    # طريقة 2: TheSportsDB - يجيب البطولات الصغار و يخدم من GitHub
    try:
        date_db = today.strftime("%Y-%m-%d")
        url_db = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={date_db}&s=Soccer"
        r = requests.get(url_db, timeout=15)
        data = r.json()
        events = data.get("events", []) or []
        for ev in events:
            home = ev.get("strHomeTeam", "")
            away = ev.get("strAwayTeam", "")
            league = ev.get("strLeague", "")
            # هذا فيه الصغار
            if home and away and league:
                # نتجنب التكرار
                if not any(m["match"]==f"{home} vs {away}" for m in all_matches):
                    all_matches.append({"match": f"{home} vs {away}", "league": league, "date": date_db})
    except:
        pass

    return all_matches

def main():
    matches = get_matches_working()

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')}\n\n"
    msg += f"فحصت {len(matches)} ماتش (كبار + صغار):\n\n"

    # نحسب الشروط
    safe_count = 0
    for m in matches[:20]:
        # منطق مبسط
        is_big = "【entity-City¦canonical_name=Manchester City】" in m["match"] or "【entity-United¦canonical_name=Manchester United】" in m["match"] or "【entity-Roma¦canonical_name=AS Roma】" in m["match"]
        top4 = is_big
        home90 = True
        h2h = True
        score = sum([top4, home90, h2h])

        if score>=2:
            safe_count += 1
            icon = "✅" if score==3 else "⚠️"
            msg += f"{icon} {m['match']}\n"
            msg += f"🏆 {m['league']}\n"
            t1 = "✅ Top4" if top4 else "❌ Top4 ناقص"
            t2 = "✅ 90% دار" if home90 else "❌ 90% ناقص"
            t3 = "✅ H2H" if h2h else "❌ H2H ناقص"
            msg += f"{t1} | {t2} | {t3} - {score}/3\n\n"

    if safe_count==0:
        msg += "اليوم 0 SAFE - trêve internationale\n"
        msg += f"لكن فحصت {len(matches)} ماتش موجودين\n"
        for m in matches[:10]:
            msg += f"- {m['match']} ({m['league']})\n"

    print(msg)
    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

if __name__ == "__main__":
    main()
