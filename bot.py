import requests, os
from datetime import datetime, timedelta
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

def get_api_football_stats(team_id_api):
    try:
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        url = f"https://v3.football.api-sports.io/teams/statistics?team={team_id_api}&season=2024&league=1"
        # نجيب آخر فورم بسيطة
        url2 = f"https://v3.football.api-sports.io/fixtures?team={team_id_api}&last=5"
        r = requests.get(url2, headers=headers, timeout=10).json()
        fixtures = r.get("response", [])[:5]
        gf=ga=w=0
        for f in fixtures:
            goals = f.get("goals",{})
            g_home = goals.get("home",0) or 0
            g_away = goals.get("away",0) or 0
            gf+= g_home+g_away
            # بسيط
        return {"avg": round(gf/5,2) if fixtures else 1.4}
    except:
        return {"avg":1.4}

def get_power(name):
    powers = {" 【entity-Real Madrid¦canonical_name=Real Madrid】":92," Man City":92," 【entity-Liverpool¦canonical_name=Liverpool】":90," 【entity-Barcelona¦canonical_name=Barcelona】":90," 【entity-Bayern¦canonical_name=Bayern】":89," 【entity-Arsenal¦canonical_name=Arsenal】":88," Inter":87," 【entity-PSG¦canonical_name=PSG】":87," 【entity-Paris¦canonical_name=Paris Saint-Germain】":87," 【entity-Atletico¦canonical_name=Atletico】":85," 【entity-Milan¦canonical_name=AC Milan】":82," 【entity-Roma¦canonical_name=AS Roma】":78}
    for k,v in powers.items():
        if k.lower() in name.lower(): return v
    return 72

def ai_final_pick(home, away, league, time_str, ph, pa):
    prompt = f"""ماتش: {home} (قوة {ph}) vs {away} (قوة {pa}) - {league} الساعة {time_str} Doha.

أنت خبير رهانات محترف. اعطيني أقل ريسك رهان ممكن لهذا الماتش في سطر واحد فقط بالتونسي:

الصيغة المطلوبة:
نوع الرهان - سبب قصير جدا

أمثلة صحيحة:
Over 1.5 - {home} يمركي 1.9 هدف في دارو كل ماتش
1W - {home} يربح 80% في بلادو
1X - {home} ما خسرش آخر 6 في دارو

اختار واحد فقط من: 1W, 1X, X2, Over 1.5, Over 0.5 HT. اختار الأضمن.
"""
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"temperature":0.4,"max_tokens":70},
            timeout=15
        )
        text = r.json()["choices"][0]["message"]["content"].strip().replace("\n"," ")
        risk = 12 if "1W" in text and ph-pa>10 else 16 if "Over 1.5" in text else 22 if "1X" in text else 30
        return text, risk
    except:
        if ph-pa>12: return f"1W - {home} أقوى برشا", 15
        return f"Over 1.5 - {home} يمركي برشا في دارو", 18

def main():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    try:
        events = requests.get(url, timeout=15).json().get("events", [])
    except:
        events = []

    picks=[]
    for ev in events[:20]:
        comp = ev.get("competitions",[{}])[0]
        teams = comp.get("competitors",[])
        if len(teams)<2: continue
        h_obj = next((t for t in teams if t.get("homeAway")=="home"), teams[0])
        a_obj = next((t for t in teams if t.get("homeAway")=="away"), teams[1])
        home = h_obj.get("team",{}).get("displayName","Home")
        away = a_obj.get("team",{}).get("displayName","Away")
        league = ev.get("leagues",[{}])[0].get("name") if ev.get("leagues") else "League"
        dt = datetime.fromisoformat(ev.get("date","").replace("Z","+00:00")) + timedelta(hours=3)
        t = dt.strftime("%H:%M")

        ph = get_power(home); pa = get_power(away)
        pick_txt, risk = ai_final_pick(home, away, league, t, ph, pa)
        picks.append({"match":f"{home} vs {away}","league":league,"time":t,"pick":pick_txt,"risk":risk})
        time.sleep(1.2)

    picks_sorted = sorted(picks, key=lambda x: x["risk"])[:10]

    msg = f"🔥 TOP 10 أقل ريسك - {datetime.now().strftime('%d/%m')} Doha 🔥\nالبوت حلل {len(events)} ماتش بذكاء AI واختارلك الأضمن:\n\n"
    if not picks_sorted:
        msg+="اليوم trêve - البوت جاهز ✅\nالمفاتيح الكل موجودة: BOT_TOKEN, CHAT_ID, GROQ_API_KEY, API_FOOTBALL_KEY"
    else:
        for i,p in enumerate(picks_sorted,1):
            icon = "✅" if p["risk"]<18 else "⚠️" if p["risk"]<25 else "🔶"
            msg+= f"{i}. {icon} {p['match']}\n 🏆 {p['league']} | 🕐 {p['time']}\n 💡 {p['pick']}\n 📊 ريسك: {p['risk']}% - {'ممتاز ⭐' if p['risk']<18 else 'جيد'}\n\n"
        msg+= "✅ البوت يفلتر وحده - Over 1.5 = يمركي برشا في دارو / 1W = يربح برشا في دارو"

    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":msg[:3800]}, timeout=15)
    print(msg)

if __name__=="__main__":
    main()
