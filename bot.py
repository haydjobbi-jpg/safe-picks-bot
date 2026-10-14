"""
SAFE-PICKS-BOT V3 - الخطة المحترفة الكاملة
الخطوة 1: القائمة الحقيقية من مواقع الرهان
الخطوة 2: فلتر Top4 + 90% + H2H 5/5
الخطوة 3: أولوية كان لقينا أقل من 10
"""
import requests, json, os
from datetime import datetime, timedelta

API_KEY = os.environ.get("FOOTBALL_DATA_KEY", "9dca548ced944c72bebb0a2d976bcf04")
HEADERS = {"X-Auth-Token": API_KEY}
CACHE_FILE = "top4_cache.json"

BETTING_LEAGUES = {
    "PL": "Premier League",
    "PD": "La Liga", 
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "ELC": "Championship",
    "BSA": "Serie A Brazil",
    "CL": "Champions League",
}

def step1_get_real_betting_matches():
    print("\n" + "="*60)
    print("📌 الخطوة 1: نجيبو الماتشات الحقيقية الموجودة في مواقع الرهان")
    print("="*60)
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={today}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"❌ خطأ: {r.status_code}")
            return []
        data = r.json()
        matches = data.get("matches", [])
        real = []
        by_league = {}
        for m in matches:
            comp_name = m["competition"]["name"]
            by_league[comp_name] = by_league.get(comp_name, 0) + 1
            if "Friendly" not in comp_name:
                real.append(m)
        print(f"\n📊 اليوم {len(matches)} ماتش الكل")
        print(f"📊 منهم {len(real)} موجودين في مواقع الرهان:")
        for league, count in by_league.items():
            print(f"   - {league}: {count}")
        print(f"\n✅ القاعدة: {len(real)} ماتش حقيقي")
        return real
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return []

def get_standings_cache():
    if os.path.exists(CACHE_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
        if datetime.now() - mtime < timedelta(hours=12):
            print(f"\n✅ كاش الترتيب من {mtime.strftime('%H:%M')}")
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    print("\n📡 نجيبو الترتيب Top4...")
    cache = {}
    for code in BETTING_LEAGUES.keys():
        try:
            url = f"https://api.football-data.org/v4/competitions/{code}/standings"
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            data = r.json()
            top4 = {}
            for st in data.get("standings", []):
                if st["type"] == "TOTAL":
                    for t in st["table"][:4]:
                        top4[t["team"]["id"]] = {
                            "rank": t["position"],
                            "name": t["team"]["name"],
                            "won": t["won"],
                            "played": t["playedGames"],
                            "win_rate": (t["won"]/t["playedGames"]*100) if t["playedGames"]>0 else 0
                        }
            cache[code] = top4
        except:
            pass
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
    return cache

def get_h2h_home_last5(home_id, away_id):
    try:
        url = f"https://api.football-data.org/v4/teams/{home_id}/matches?limit=30"
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return {"won": 0, "total": 0, "is_5_5": False}
        matches = r.json().get("matches", [])
        h2h = []
        for m in matches:
            if m["homeTeam"]["id"] == home_id and m["awayTeam"]["id"] == away_id:
                if m["score"]["winner"] == "HOME_TEAM":
                    h2h.append("W")
                else:
                    h2h.append("L")
                if len(h2h) >= 5:
                    break
        won = h2h.count("W")
        return {"won": won, "total": len(h2h), "is_5_5": won==5 and len(h2h)>=5, "details": h2h}
    except:
        return {"won": 0, "total": 0, "is_5_5": False, "details": []}

def step2_and_3_filter_with_priority(matches, standings_cache):
    print("\n" + "="*60)
    print("📌 الخطوة 2: فلتر Top4 + 90% + H2H 5/5")
    print("="*60)
    results = []
    for m in matches:
        home_id = m["homeTeam"]["id"]
        home_name = m["homeTeam"]["name"]
        away_name = m["awayTeam"]["name"]
        comp_name = m["competition"]["name"]
        team_data = None
        for league_top4 in standings_cache.values():
            if home_id in league_top4:
                team_data = league_top4[home_id]
                break
        if not team_data:
            continue
        cond1_rank = team_data["rank"]
        try:
            url = f"https://api.football-data.org/v4/teams/{home_id}/matches?status=FINISHED&limit=15"
            r = requests.get(url, headers=HEADERS, timeout=20)
            home_wins = 0
            home_games = 0
            if r.status_code == 200:
                for game in r.json().get("matches", []):
                    if game["homeTeam"]["id"] == home_id:
                        home_games += 1
                        if game["score"]["winner"] == "HOME_TEAM":
                            home_wins += 1
                        if home_games >= 10:
                            break
            home_win_rate = (home_wins/home_games*100) if home_games>0 else team_data["win_rate"]
        except:
            home_win_rate = team_data["win_rate"]
        cond2 = home_win_rate >= 90
        cond2_rate = home_win_rate
        h2h = get_h2h_home_last5(home_id, m["awayTeam"]["id"])
        cond3 = h2h["is_5_5"]
        cond3_won = h2h["won"]
        score = sum([True, cond2, cond3])
        missing = []
        if not cond2:
            missing.append(f"90% (عندو {cond2_rate:.0f}%)")
        if not cond3:
            missing.append(f"H2H {cond3_won}/5 في دارو")
        results.append({
            "home": home_name,
            "away": away_name,
            "league": comp_name,
            "rank": cond1_rank,
            "home_rate": cond2_rate,
            "h2h": h2h,
            "score": score,
            "missing": missing,
        })
        status = "✅" if score==3 else f"⚠️ {score}/3"
        print(f"{status} {home_name} (Top{cond1_rank}) vs {away_name} | {comp_name} | دار {cond2_rate:.0f}% | H2H {cond3_won}/5 | ناقص: {', '.join(missing) if missing else 'لا شيء'}")
    print("\n" + "="*60)
    print("📌 الخطوة 3: الترتيب بالأولوية")
    print("="*60)
    results.sort(key=lambda x: x["score"], reverse=True)
    p3 = [r for r in results if r["score"]==3]
    p2 = [r for r in results if r["score"]==2]
    p1 = [r for r in results if r["score"]==1]
    print(f"⭐⭐⭐ 3/3: {len(p3)} ماتش")
    print(f"⭐⭐ 2/3: {len(p2)} ماتش")
    print(f"⭐ 1/3: {len(p1)} ماتش")
    return p3 + p2 + p1

def main():
    print(f"🚀 SAFE-PICKS-BOT V3 - {datetime.now().strftime('%Y-%m-%d %H:%M')} Doha")
    betting_matches = step1_get_real_betting_matches()
    if not betting_matches:
        print("\n📩 اليوم ما فماش ماتشات في مواقع الرهان - trêve")
        return
    standings = get_standings_cache()
    final = step2_and_3_filter_with_priority(betting_matches, standings)
    print("\n" + "="*60)
    print(f"🎯 النتيجة: {len(final)} ماتش مرتبين بالأولوية")
    print("="*60)
    msg = f"📩 Safe Picks {datetime.now().strftime('%Y-%m-%d')} - {len(betting_matches)} ماتش حقيقي في الرهان\n\n"
    if not final:
        msg += "اليوم ما فماش ماتشات بالشروط"
        print(msg)
    else:
        for i, r in enumerate(final[:10], 1):
            if r["score"] == 3:
                msg += f"{i}. ⭐⭐⭐ {r['home']} (Top{r['rank']}) vs {r['away']} - {r['league']}\n   دار {r['home_rate']:.0f}% | H2H {r['h2h']['won']}/5\n"
            elif r["score"] == 2:
                msg += f"{i}. ⭐⭐ {r['home']} (Top{r['rank']}) vs {r['away']} - ناقص: {', '.join(r['missing'])}\n"
            else:
                msg += f"{i}. ⭐ {r['home']} (Top{r['rank']}) vs {r['away']} - ناقص: {', '.join(r['missing'])}\n"
        print("\n📩 الرسالة:\n" + msg)
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if bot_token and chat_id and final:
        try:
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": msg})
            print("\n📨 تبعثت لتيليجرام ✅")
        except Exception as e:
            print(f"\n❌ تيليجرام: {e}")

if __name__ == "__main__":
    main()
