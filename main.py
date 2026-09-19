import asyncio, os, random, re, unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import asyncpg
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from ranks import RANKS, rank_for_xp, next_rank
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN=os.environ["BOT_TOKEN"]
DB_URL=os.environ["DATABASE_URL"]
TZ=ZoneInfo(os.getenv("TIMEZONE","Europe/Paris"))
INTERVAL=int(os.getenv("GAME_INTERVAL_HOURS","2"))
dp=Dispatcher()
pool=None
active_games={}

WORDS=["silence","telegram","mystere","cascade","planete","orange","pirate","musique","voyage","rapide","secret","chance","dragon","cinema","jungle","mirage","puzzle","soleil"]
COPY=["incroyable","parapluie","astronaute","magnifique","cacahuete","tourbillon","telegram"]
MISSIONS={"detailed":(7,25),"replies":(3,25),"reactions_received":(6,50)}

def norm(s):
    s=unicodedata.normalize("NFD",s.lower().strip())
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

def period_start(kind):
    now=datetime.now(TZ)
    if kind=="day": return now.replace(hour=0,minute=0,second=0,microsecond=0)
    if kind=="week":
        d=now-timedelta(days=now.weekday())
        return d.replace(hour=0,minute=0,second=0,microsecond=0)
    if kind=="month": return now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    return datetime(2000,1,1,tzinfo=TZ)

async def init_db():
    global pool
    pool=await asyncpg.create_pool(DB_URL)
    async with pool.acquire() as c:
        await c.execute("""
        CREATE TABLE IF NOT EXISTS users(
          chat_id BIGINT, user_id BIGINT, name TEXT, total_xp BIGINT DEFAULT 0,
          wins BIGINT DEFAULT 0, PRIMARY KEY(chat_id,user_id));
        CREATE TABLE IF NOT EXISTS xp_events(
          id BIGSERIAL PRIMARY KEY, chat_id BIGINT,user_id BIGINT,xp INT,reason TEXT,
          created_at TIMESTAMPTZ DEFAULT now());
        CREATE TABLE IF NOT EXISTS daily_stats(
          chat_id BIGINT,user_id BIGINT,day DATE,detailed INT DEFAULT 0,replies INT DEFAULT 0,
          reactions_received INT DEFAULT 0, PRIMARY KEY(chat_id,user_id,day));
        CREATE TABLE IF NOT EXISTS mission_claims(
          chat_id BIGINT,user_id BIGINT,day DATE,mission TEXT,
          PRIMARY KEY(chat_id,user_id,day,mission));
        CREATE TABLE IF NOT EXISTS message_xp(
          chat_id BIGINT,user_id BIGINT,last_text TEXT,last_at TIMESTAMPTZ,
          PRIMARY KEY(chat_id,user_id));
        """)

async def ensure_user(chat_id,u):
    name=u.full_name or u.username or str(u.id)
    await pool.execute("""INSERT INTO users(chat_id,user_id,name) VALUES($1,$2,$3)
      ON CONFLICT(chat_id,user_id) DO UPDATE SET name=EXCLUDED.name""",chat_id,u.id,name)

async def add_xp(chat_id,u,xp,reason):
    await ensure_user(chat_id,u)
    await pool.execute("UPDATE users SET total_xp=total_xp+$1 WHERE chat_id=$2 AND user_id=$3",xp,chat_id,u.id)
    await pool.execute("INSERT INTO xp_events(chat_id,user_id,xp,reason) VALUES($1,$2,$3,$4)",chat_id,u.id,xp,reason)

async def bump_stat(chat_id,user_id,field,amount=1):
    day=datetime.now(TZ).date()
    await pool.execute("""INSERT INTO daily_stats(chat_id,user_id,day) VALUES($1,$2,$3)
      ON CONFLICT DO NOTHING""",chat_id,user_id,day)
    await pool.execute(f"UPDATE daily_stats SET {field}={field}+$1 WHERE chat_id=$2 AND user_id=$3 AND day=$4",amount,chat_id,user_id,day)

async def claim_missions(chat_id,u):
    day=datetime.now(TZ).date()
    row=await pool.fetchrow("SELECT * FROM daily_stats WHERE chat_id=$1 AND user_id=$2 AND day=$3",chat_id,u.id,day)
    if not row:return
    for key,(target,reward) in MISSIONS.items():
        if row[key]>=target:
            done=await pool.fetchval("SELECT 1 FROM mission_claims WHERE chat_id=$1 AND user_id=$2 AND day=$3 AND mission=$4",chat_id,u.id,day,key)
            if not done:
                await pool.execute("INSERT INTO mission_claims VALUES($1,$2,$3,$4)",chat_id,u.id,day,key)
                await add_xp(chat_id,u,reward,"mission:"+key)

def new_game():
    kind=random.choice(["anagram","copy","math"])
    if kind=="anagram":
        ans=random.choice(WORDS); chars=list(ans)
        while "".join(chars)==ans: random.shuffle(chars)
        return kind,"🧩 ANAGRAMME\n\nRemets les lettres dans le bon ordre :\n\n🔥  "+ "".join(chars).upper(),ans
    if kind=="copy":
        ans=random.choice(COPY)
        return kind,"⚡ RAPIDITÉ\n\nRecopie exactement ce mot :\n\n🔥  "+ans.upper(),ans
    a=random.randint(4,25); b=random.randint(2,12); op=random.choice(["+","-","×"])
    if op=="+": ans=a+b
    elif op=="-": ans=a-b
    else: ans=a*b
    return kind,f"🧠 CALCUL MENTAL\n\nCombien font :\n\n🔥  {a} {op} {b} ?",str(ans)

async def start_game(bot,chat_id):
    if chat_id in active_games:return
    kind,text,ans=new_game()
    msg=await bot.send_message(chat_id,text+"\n\n🏆 Premier à répondre correctement : +250 XP")
    active_games[chat_id]={"answer":norm(ans),"started":datetime.now(timezone.utc),"message_id":msg.message_id}

async def scheduled_games(bot):
    rows=await pool.fetch("SELECT DISTINCT chat_id FROM users")
    for r in rows:
        try: await start_game(bot,r["chat_id"])
        except Exception: pass

@dp.message(Command("jeu"))
async def cmd_game(m:Message,bot:Bot):
    if m.chat.type=="private": return await m.answer("Ajoute-moi dans un groupe pour jouer.")
    member=await bot.get_chat_member(m.chat.id,m.from_user.id)
    if member.status not in ("administrator","creator"): return
    await start_game(bot,m.chat.id)

@dp.message(Command("profil"))
async def profile(m:Message):
    await ensure_user(m.chat.id,m.from_user)
    r=await pool.fetchrow("SELECT total_xp,wins FROM users WHERE chat_id=$1 AND user_id=$2",m.chat.id,m.from_user.id)
    rank=await pool.fetchval("SELECT 1+count(*) FROM users WHERE chat_id=$1 AND total_xp>$2",m.chat.id,r["total_xp"])
    level=1+r["total_xp"]//500
    await m.answer(f"👤 {m.from_user.full_name}\n⭐ {r['total_xp']} XP · Niveau {level}\n🏆 {r['wins']} jeux gagnés\n📊 #{rank} du classement général")

@dp.message(Command("rank"))
async def rank_cmd(m:Message):
    sid=await ensure_user(m.chat.id,m.from_user,m.chat.title)
    xp=await pool.fetchval("SELECT xp FROM player_season_stats WHERE chat_id=$1 AND user_id=$2 AND season_id=$3",m.chat.id,m.from_user.id,sid) or 0
    rank=rank_for_xp(xp)
    nxt,threshold=next_rank(xp)
    extra=f"\n➡️ Prochain : {nxt} à {threshold} XP" if nxt else "\n✨ Rang maximum atteint"
    await m.answer(f"🏅 {rank}\n⭐ {xp} XP cette saison"+extra)

@dp.message(Command("ranks"))
async def ranks_cmd(m:Message):
    await m.answer("🏅 RANGS DE SAISON\n\n"+"\n".join(f"{name} — {xp:,} XP".replace(","," ") for name,xp in RANKS))

@dp.message(Command("top"))
async def top_cmd(m:Message):
    sid=await current_season_id()
    rows=await pool.fetch("""SELECT u.name,s.xp FROM player_season_stats s
      JOIN users u ON u.chat_id=s.chat_id AND u.user_id=s.user_id
      WHERE s.chat_id=$1 AND s.season_id=$2 ORDER BY s.xp DESC,u.user_id ASC LIMIT 7""",m.chat.id,sid)
    if not rows:
        return await m.answer("🏆 Pas encore de classement pour cette saison.")
    medals=["🥇","🥈","🥉"]
    lines=[f"{medals[i] if i<3 else str(i+1)+'.'} {r['name']} — {r['xp']} XP · {rank_for_xp(r['xp'])}" for i,r in enumerate(rows)]
    await m.answer("🏆 TOP 7 DU GROUPE — SAISON EN COURS\n\n"+"\n".join(lines))

@dp.message(Command("missions"))
async def missions(m:Message):
    day=datetime.now(TZ).date()
    r=await pool.fetchrow("SELECT * FROM daily_stats WHERE chat_id=$1 AND user_id=$2 AND day=$3",m.chat.id,m.from_user.id,day)
    vals={k:(r[k] if r else 0) for k in MISSIONS}
    await m.answer("📋 OBJECTIFS DU JOUR\n\n"+
      f"📝 Messages détaillés : {min(vals['detailed'],7)}/7\n"+
      f"↩️ Réponses : {min(vals['replies'],3)}/3\n"+
      f"❤️ Réactions reçues : {min(vals['reactions_received'],6)}/6\n\nLes récompenses sont créditées automatiquement.")

@dp.message(Command("classement"))
async def ranking(m:Message):
    parts=(m.text or "").split()
    kind=parts[1].lower() if len(parts)>1 and parts[1].lower() in ("jour","semaine","mois","general") else "semaine"
    mapk={"jour":"day","semaine":"week","mois":"month","general":"all"}
    k=mapk[kind]
    if k=="all":
        rows=await pool.fetch("SELECT name,total_xp xp FROM users WHERE chat_id=$1 ORDER BY total_xp DESC LIMIT 10",m.chat.id)
    else:
        start=period_start(k)
        rows=await pool.fetch("""SELECT u.name,COALESCE(sum(e.xp),0)::bigint xp FROM users u
          LEFT JOIN xp_events e ON e.chat_id=u.chat_id AND e.user_id=u.user_id AND e.created_at >= $2
          WHERE u.chat_id=$1 GROUP BY u.user_id,u.name ORDER BY xp DESC LIMIT 10""",m.chat.id,start)
    medals=["🥇","🥈","🥉"]
    lines=[f"{medals[i] if i<3 else str(i+1)+'.'} {r['name']} — {r['xp']} XP" for i,r in enumerate(rows)]
    await m.answer("🏆 CLASSEMENT "+kind.upper()+"\n\n"+("\n".join(lines) if lines else "Pas encore de classement."))

@dp.message(F.reaction)
async def reaction_handler(m:Message):
    pass

@dp.message()
async def messages(m:Message):
    if not m.from_user or m.from_user.is_bot or m.chat.type=="private" or not m.text:return
    u=m.from_user; cid=m.chat.id; text=m.text.strip()
    await ensure_user(cid,u,m.chat.title)

    game=active_games.get(cid)
    if game and norm(text)==game["answer"]:
        elapsed=(datetime.now(timezone.utc)-game["started"]).total_seconds()
        active_games.pop(cid,None)
        await add_xp(cid,u,250,"game_win",m.chat.title)
        await pool.execute("UPDATE users SET wins=wins+1 WHERE chat_id=$1 AND user_id=$2",cid,u.id)
        return await m.reply(f"🏆 {u.full_name} remporte la manche en {elapsed:.1f}s !\n+50 XP")

    if text.startswith("/"):return
    now=datetime.now(timezone.utc)
    prev=await pool.fetchrow("SELECT last_text,last_at FROM message_xp WHERE chat_id=$1 AND user_id=$2",cid,u.id)
    eligible=True
    if len(text)<3: eligible=False
    if prev and norm(prev["last_text"] or "")==norm(text): eligible=False
    if prev and prev["last_at"] and (now-prev["last_at"]).total_seconds()<8: eligible=False
    await pool.execute("""INSERT INTO message_xp(chat_id,user_id,last_text,last_at) VALUES($1,$2,$3,$4)
      ON CONFLICT(chat_id,user_id) DO UPDATE SET last_text=EXCLUDED.last_text,last_at=EXCLUDED.last_at""",cid,u.id,text,now)
    if eligible:
        xp=2 if len(text)>=40 else 1
        await add_xp(cid,u,xp,"detailed_message" if xp==2 else "message")
        if len(text)>=40: await bump_stat(cid,u.id,"detailed")
        if m.reply_to_message and m.reply_to_message.from_user and m.reply_to_message.from_user.id!=u.id:
            await add_xp(cid,u,1,"reply")
            await bump_stat(cid,u.id,"replies")
        await claim_missions(cid,u)

async def main():
    await init_db()
    bot=Bot(TOKEN)
    scheduler=AsyncIOScheduler(timezone=TZ)
    scheduler.add_job(scheduled_games,"interval",hours=INTERVAL,args=[bot],id="games")
    scheduler.start()
    try: await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await pool.close()

if __name__=="__main__":
    asyncio.run(main())
