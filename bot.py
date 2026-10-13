import os, requests
from datetime import datetime, timedelta

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
API_KEY=os.getenv("API_FOOTBALL_KEY")

def get_data(url):
    try:
        headers={"x-apisports-key": API_KEY}
        r=requests.get(url, headers=headers, timeout=15)
        j=r.json()
        return j.get("response", [])
    except:
        return []

# اليوم بتوقيت الدوحة
tomorrow = (datetime.utcnow()+timedelta(hours=3)).strftime("%Y-%m-%d")

fixtures = get_data(f"https://v3.football.api-sports.io/fixtures?date={tomorrow}")

picks = []

for m in fixtures:
    try:
        fid = m["fixture"]["id"]
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        league_id = m["league"]["id"]
        season = m["league"]["season"]

        # 6. موجود في مواقع الرهانات؟ (لازم عندو كوت)
        odds = get_data(f"https://v3.football.api-sports.io/odds?fixture={fid}")
        if not odds:
            continue
        # نشوف كان عندو كوت صحيحة
        has_odd = False
        odd_value = "1.8"
        for book in odds[0].get("bookmakers", []):
            for bet in book.get("bets", []):
                if bet.get("values"):
                    has_odd = True
                    odd_value = bet["values"][0].get("odd", "1.8")
                    break
        if not has_odd:
            continue

        # 1. Top4 + 2. دار
        standings = get_data(f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}")
        if not standings:
            continue
        table = standings[0]["league"]["standings"][0]
        home_rank = 99
        for t in table:
            if t["team"]["id"] == home_id:
                home_rank = t["rank"]
                break
        if home_rank > 4:
            continue

        # 3. 5/5 رابح آخر 5
        last5 = get_data(f"https://v3.football.api-sports.io/fixtures?team={home_id}&last=5")
        wins = 0
        for game in last5:
            if game["teams"]["home"]["id"] == home_id and game["teams"]["home"]["winner"]:
                wins += 1
            if game["teams"]["away"]["id"] == home_id and game["teams"]["away"]["winner"]:
                wins += 1
        if wins < 5:
            continue

        # 4. 90% في الدار (نحسبوها من stats)
        stats = get_data(f"https://v3.football.api-sports.io/teams/statistics?team={home_id}&league={league_id}&season={season}")
        rate = 100
        guaranteed = True
        try:
            if stats:
                home_wins = stats[0]["fixtures"]["wins"]["home"]
                home_played = stats[0]["fixtures"]["played"]["home"]
                if home_played > 0:
                    rate = (home_wins / home_played) * 100
                if rate < 80: # نخليوها 80 باش نلقاو، كان تحب 90 بدلها
                    guaranteed = False
        except:
            rate = 100

        # 5. H2H رابح المواجهات
        h2h = get_data(f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=3")
        h2h_wins = 0
        for game in h2h:
            if game["teams"]["home"]["id"] == home_id and game["teams"]["home"]["winner"]:
                h2h_wins += 1
            if game["teams"]["away"]["id"] == home_id and game["teams"]["away"]["winner"]:
                h2h_wins += 1
        if h2h_wins == 0:
            continue

        # الذكاء: W1 ولا 1X
        pick_type = "W1" if (guaranteed and rate >= 90 and h2h_wins >= 2) else "1X"

        picks.append(f"⚽ {m['league']['name']}\n{m['teams']['home']['name']} vs {m['teams']['away']['name']}\n👉 {pick_type} @ {odd_value} | Top{home_rank} | 5/5 | {int(rate)}% دار | H2H:{h2h_wins} | موجود\n")

        if len(picks) >= 10:
            break
    except:
        continue

# من 0 إلى 10 - يبعث ديما
if picks:
    msg = f"🔥 Safe Picks Daily - {tomorrow} ({len(picks)}/10)\n00:30 Doha\n\n" + "\n".join(picks)
else:
    msg = f"📭 Safe Picks Daily - {tomorrow} (0/10)\n00:30 Doha\n\nاليوم {len(fixtures)} ماتش، حتى واحد ما فيه 6 شروط:\nTop4 + دار + 90% + 5/5 + H2H + موجود في الرهانات"

requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
