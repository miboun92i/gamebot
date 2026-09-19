import asyncio, os, random, unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, MessageReactionUpdated, BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ranks import RANKS, rank_for_xp, next_rank
from tasks import TASK_POOL, DAILY_TASK_COUNT, DAILY_BONUS
from leaderboard_image import render_top

TOKEN=os.environ["BOT_TOKEN"]
DB_URL=os.environ["DATABASE_URL"]
TZ=ZoneInfo(os.getenv("TIMEZONE","Europe/Paris"))
INTERVAL=int(os.getenv("GAME_INTERVAL_HOURS","2"))
dp=Dispatcher()
pool=None
active_games={}

WORDS=["silence","telegram","mystere","cascade","planete","orange","pirate","musique","voyage","rapide","secret","chance","dragon","cinema","jungle","mirage","puzzle","soleil"]
COPY=["incroyable","parapluie","astronaute","magnifique","cacahuete","tourbillon","telegram"]

def norm(s):
    s=unicodedata.normalize("NFD",str(s).lower().strip())
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

async def init_db():
    global pool
    pool=await asyncpg.create_pool(DB_URL)
    async with pool.acquire() as c:
        await c.execute("""
        CREATE TABLE IF NOT EXISTS users(
          chat_id BIGINT,user_id BIGINT,name TEXT,total_xp BIGINT DEFAULT 0,wins BIGINT DEFAULT 0,
          PRIMARY KEY(chat_id,user_id));
        CREATE TABLE IF NOT EXISTS groups(
          chat_id BIGINT PRIMARY KEY,title TEXT,created_at TIMESTAMPTZ DEFAULT now());
        CREATE TABLE IF NOT EXISTS seasons(
          id BIGSERIAL PRIMARY KEY,starts_at TIMESTAMPTZ NOT NULL,ends_at TIMESTAMPTZ NOT NULL,
          label TEXT NOT NULL,UNIQUE(starts_at,ends_at));
        CREATE TABLE IF NOT EXISTS player_season_stats(
          chat_id BIGINT,user_id BIGINT,season_id BIGINT REFERENCES seasons(id),xp BIGINT DEFAULT 0,
          wins BIGINT DEFAULT 0,tasks_completed INT DEFAULT 0,best_streak INT DEFAULT 0,
          PRIMARY KEY(chat_id,user_id,season_id));
        CREATE TABLE IF NOT EXISTS xp_events(
          id BIGSERIAL PRIMARY KEY,chat_id BIGINT,user_id BIGINT,xp INT,reason TEXT,
          created_at TIMESTAMPTZ DEFAULT now());
        CREATE TABLE IF NOT EXISTS daily_task_sets(
          chat_id BIGINT,day DATE,task_key TEXT,PRIMARY KEY(chat_id,day,task_key));
        CREATE TABLE IF NOT EXISTS task_progress(
          chat_id BIGINT,user_id BIGINT,day DATE,task_key TEXT,progress INT DEFAULT 0,claimed BOOLEAN DEFAULT FALSE,
          PRIMARY KEY(chat_id,user_id,day,task_key));
        CREATE TABLE IF NOT EXISTS daily_bonus_claims(
          chat_id BIGINT,user_id BIGINT,day DATE,PRIMARY KEY(chat_id,user_id,day));
        CREATE TABLE IF NOT EXISTS task_unique_events(
          chat_id BIGINT,user_id BIGINT,day DATE,task_key TEXT,unique_key TEXT,
          PRIMARY KEY(chat_id,user_id,day,task_key,unique_key));
        CREATE TABLE IF NOT EXISTS message_authors(
          chat_id BIGINT,message_id BIGINT,user_id BIGINT,PRIMARY KEY(chat_id,message_id));
        CREATE TABLE IF NOT EXISTS message_reply_counts(
          chat_id BIGINT,message_id BIGINT,author_id BIGINT,count INT DEFAULT 0,
          PRIMARY KEY(chat_id,message_id));
        """)

async def current_season_id():
    now=datetime.now(TZ)
    start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    end=start.replace(year=start.year+1,month=1) if start.month==12 else start.replace(month=start.month+1)
    return await pool.fetchval("""INSERT INTO seasons(starts_at,ends_at,label) VALUES($1,$2,$3)
      ON CONFLICT(starts_at,ends_at) DO UPDATE SET label=EXCLUDED.label RETURNING id""",
      start,end,start.strftime("%Y-%m"))

async def ensure_user(chat_id,u,chat_title=None):
    name=u.full_name or u.username or str(u.id)
    await pool.execute("""INSERT INTO users(chat_id,user_id,name) VALUES($1,$2,$3)
      ON CONFLICT(chat_id,user_id) DO UPDATE SET name=EXCLUDED.name""",chat_id,u.id,name)
    await pool.execute("""INSERT INTO groups(chat_id,title) VALUES($1,$2)
      ON CONFLICT(chat_id) DO UPDATE SET title=COALESCE(EXCLUDED.title,groups.title)""",chat_id,chat_title)
    sid=await current_season_id()
    await pool.execute("""INSERT INTO player_season_stats(chat_id,user_id,season_id) VALUES($1,$2,$3)
      ON CONFLICT DO NOTHING""",chat_id,u.id,sid)
    return sid

async def add_xp(chat_id,u,xp,reason,chat_title=None):
    sid=await ensure_user(chat_id,u,chat_title)
    await pool.execute("UPDATE users SET total_xp=total_xp+$1 WHERE chat_id=$2 AND user_id=$3",xp,chat_id,u.id)
    await pool.execute("UPDATE player_season_stats SET xp=xp+$1 WHERE chat_id=$2 AND user_id=$3 AND season_id=$4",xp,chat_id,u.id,sid)
    await pool.execute("INSERT INTO xp_events(chat_id,user_id,xp,reason) VALUES($1,$2,$3,$4)",chat_id,u.id,xp,reason)

async def daily_tasks(chat_id):
    day=datetime.now(TZ).date()
    rows=await pool.fetch("SELECT task_key FROM daily_task_sets WHERE chat_id=$1 AND day=$2",chat_id,day)
    if len(rows)<DAILY_TASK_COUNT:
        chosen=random.Random(f"{chat_id}:{day.isoformat()}").sample(list(TASK_POOL),DAILY_TASK_COUNT)
        for key in chosen:
            await pool.execute("INSERT INTO daily_task_sets(chat_id,day,task_key) VALUES($1,$2,$3) ON CONFLICT DO NOTHING",chat_id,day,key)
        rows=await pool.fetch("SELECT task_key FROM daily_task_sets WHERE chat_id=$1 AND day=$2 ORDER BY task_key",chat_id,day)
    return [r["task_key"] for r in rows]

async def task_event(chat_id,u,event,unique_key=None,amount=1,chat_title=None):
    day=datetime.now(TZ).date()
    for key in await daily_tasks(chat_id):
        task=TASK_POOL[key]
        if task["event"]!=event:
            continue
        if unique_key is not None:
            inserted=await pool.fetchval("""INSERT INTO task_unique_events(chat_id,user_id,day,task_key,unique_key)
              VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING RETURNING 1""",chat_id,u.id,day,key,str(unique_key))
            if not inserted:
                continue
        await pool.execute("""INSERT INTO task_progress(chat_id,user_id,day,task_key,progress) VALUES($1,$2,$3,$4,$5)
          ON CONFLICT(chat_id,user_id,day,task_key) DO UPDATE SET progress=task_progress.progress+$5""",
          chat_id,u.id,day,key,amount)
        row=await pool.fetchrow("SELECT progress,claimed FROM task_progress WHERE chat_id=$1 AND user_id=$2 AND day=$3 AND task_key=$4",chat_id,u.id,day,key)
        if row["progress"]>=task["target"] and not row["claimed"]:
            claimed=await pool.fetchval("""UPDATE task_progress SET claimed=TRUE WHERE chat_id=$1 AND user_id=$2 AND day=$3
              AND task_key=$4 AND claimed=FALSE RETURNING 1""",chat_id,u.id,day,key)
            if claimed:
                await add_xp(chat_id,u,task["reward"],"task:"+key,chat_title)
                sid=await current_season_id()
                await pool.execute("UPDATE player_season_stats SET tasks_completed=tasks_completed+1 WHERE chat_id=$1 AND user_id=$2 AND season_id=$3",chat_id,u.id,sid)
    completed=await pool.fetchval("SELECT count(*) FROM task_progress WHERE chat_id=$1 AND user_id=$2 AND day=$3 AND claimed=TRUE",chat_id,u.id,day)
    if completed>=DAILY_TASK_COUNT:
        bonus=await pool.fetchval("""INSERT INTO daily_bonus_claims(chat_id,user_id,day) VALUES($1,$2,$3)
          ON CONFLICT DO NOTHING RETURNING 1""",chat_id,u.id,day)
        if bonus:
            await add_xp(chat_id,u,DAILY_BONUS,"tasks:5of5",chat_title)

def new_game():
    kind=random.choice(["anagram","copy","math"])
    if kind=="anagram":
        ans=random.choice(WORDS); chars=list(ans)
        while "".join(chars)==ans: random.shuffle(chars)
        return kind,"🧩 ANAGRAMME\n\nRemets les lettres dans le bon ordre :\n\n🔥  "+"".join(chars).upper(),ans
    if kind=="copy":
        ans=random.choice(COPY)
        return kind,"⚡ RAPIDITÉ\n\nRecopie exactement ce mot :\n\n🔥  "+ans.upper(),ans
    a=random.randint(4,25); b=random.randint(2,12); op=random.choice(["+","-","×"])
    ans=a+b if op=="+" else a-b if op=="-" else a*b
    return kind,f"🧠 CALCUL MENTAL\n\nCombien font :\n\n🔥  {a} {op} {b} ?",str(ans)

async def start_game(bot,chat_id):
    if chat_id in active_games: return
    _,text,ans=new_game()
    msg=await bot.send_message(chat_id,text+"\n\n🏆 Premier à répondre correctement : +250 XP")
    active_games[chat_id]={"answer":norm(ans),"started":datetime.now(timezone.utc),"message_id":msg.message_id}

async def scheduled_games(bot):
    rows=await pool.fetch("SELECT chat_id FROM groups")
    for r in rows:
        try: await start_game(bot,r["chat_id"])
        except Exception: pass

@dp.message(Command("jeu"))
async def cmd_game(m:Message,bot:Bot):
    if m.chat.type=="private": return await m.answer("Ajoute-moi dans un groupe pour jouer.")
    member=await bot.get_chat_member(m.chat.id,m.from_user.id)
    if member.status not in ("administrator","creator"): return
    await start_game(bot,m.chat.id)

@dp.message(Command("rank"))
async def rank_cmd(m:Message):
    sid=await ensure_user(m.chat.id,m.from_user,m.chat.title)
    xp=await pool.fetchval("SELECT xp FROM player_season_stats WHERE chat_id=$1 AND user_id=$2 AND season_id=$3",m.chat.id,m.from_user.id,sid) or 0
    rank=rank_for_xp(xp); nxt,threshold=next_rank(xp)
    extra=f"\n➡️ Prochain : {nxt} à {threshold} XP" if nxt else "\n✨ Rang maximum atteint"
    await m.answer(f"🏅 {rank}\n⭐ {xp} XP cette saison"+extra)

@dp.message(Command("ranks"))
async def ranks_cmd(m:Message):
    await m.answer("🏅 RANGS DE SAISON\n\n"+"\n".join(f"{name} — {xp:,} XP".replace(","," ") for name,xp in RANKS))

@dp.message(Command("top"))
async def top_cmd(m:Message):
    if m.chat.type=="private": return await m.answer("Utilise /top dans un groupe.")
    sid=await current_season_id()
    rows=await pool.fetch("""SELECT u.name,s.xp FROM player_season_stats s
      JOIN users u ON u.chat_id=s.chat_id AND u.user_id=s.user_id
      WHERE s.chat_id=$1 AND s.season_id=$2 ORDER BY s.xp DESC,u.user_id ASC LIMIT 10""",m.chat.id,sid)
    if not rows: return await m.answer("🏆 Pas encore de classement pour cette saison.")
    season=await pool.fetchrow("SELECT label,ends_at FROM seasons WHERE id=$1",sid)
    total=await pool.fetchval("SELECT count(*) FROM player_season_stats WHERE chat_id=$1 AND season_id=$2",m.chat.id,sid)
    players=[{"name":r["name"],"xp":r["xp"],"rank":rank_for_xp(r["xp"])} for r in rows[:7]]
    top10_xp=sum(r["xp"] for r in rows[:10])
    now=datetime.now(TZ)
    end_at=season["ends_at"].astimezone(TZ)
    days_left=max(0,(end_at.date()-now.date()).days)
    image=render_top(m.chat.title,season["label"],players,total,top10_xp,days_left)
    await m.answer_photo(BufferedInputFile(image.getvalue(),filename="top.png"))

@dp.message(Command("tasks"))
@dp.message(Command("missions"))
async def tasks_cmd(m:Message):
    if m.chat.type=="private": return await m.answer("Utilise /tasks dans un groupe.")
    await ensure_user(m.chat.id,m.from_user,m.chat.title)
    day=datetime.now(TZ).date(); lines=[]; done=0
    for key in await daily_tasks(m.chat.id):
        task=TASK_POOL[key]
        row=await pool.fetchrow("SELECT progress,claimed FROM task_progress WHERE chat_id=$1 AND user_id=$2 AND day=$3 AND task_key=$4",m.chat.id,m.from_user.id,day,key)
        progress=row["progress"] if row else 0; claimed=bool(row and row["claimed"]); done+=int(claimed)
        lines.append(f"{'✅' if claimed else '▫️'} {task['label']} — {min(progress,task['target'])}/{task['target']} · +{task['reward']} XP")
    await m.answer("📋 TÂCHES DU JOUR\n\n"+"\n".join(lines)+f"\n\n🎁 {done}/5 · Bonus 5/5 : +{DAILY_BONUS} XP")

@dp.message_reaction()
async def reaction_update(r:MessageReactionUpdated):
    if not r.user or r.user.is_bot: return
    old=len(r.old_reaction or []); new=len(r.new_reaction or [])
    if new<=old: return
    cid=r.chat.id; reactor=r.user
    await ensure_user(cid,reactor,r.chat.title)
    author=await pool.fetchval("SELECT user_id FROM message_authors WHERE chat_id=$1 AND message_id=$2",cid,r.message_id)
    await task_event(cid,reactor,"reaction_given",unique_key=r.message_id,chat_title=r.chat.title)
    if author and author!=reactor.id:
        await task_event(cid,reactor,"reaction_given_unique",unique_key=author,chat_title=r.chat.title)
        target=await pool.fetchrow("SELECT name FROM users WHERE chat_id=$1 AND user_id=$2",cid,author)
        if target:
            class U:
                id=author; full_name=target["name"]; username=None
            unique=f"{r.message_id}:{reactor.id}"
            await task_event(cid,U(),"reaction_received",unique_key=unique,chat_title=r.chat.title)
            await task_event(cid,U(),"reaction_one",unique_key=unique,chat_title=r.chat.title)

@dp.message()
async def messages(m:Message):
    if not m.from_user or m.from_user.is_bot or m.chat.type=="private": return
    u=m.from_user; cid=m.chat.id; text=(m.text or m.caption or "").strip()
    await ensure_user(cid,u,m.chat.title)
    await pool.execute("INSERT INTO message_authors(chat_id,message_id,user_id) VALUES($1,$2,$3) ON CONFLICT DO NOTHING",cid,m.message_id,u.id)

    game=active_games.get(cid)
    if game and text and norm(text)==game["answer"]:
        elapsed=(datetime.now(timezone.utc)-game["started"]).total_seconds()
        active_games.pop(cid,None)
        await add_xp(cid,u,250,"game_win",m.chat.title)
        sid=await current_season_id()
        await pool.execute("UPDATE users SET wins=wins+1 WHERE chat_id=$1 AND user_id=$2",cid,u.id)
        await pool.execute("UPDATE player_season_stats SET wins=wins+1 WHERE chat_id=$1 AND user_id=$2 AND season_id=$3",cid,u.id,sid)
        await m.reply(f"🏆 {u.full_name} remporte la manche en {elapsed:.1f}s !\n+250 XP")

    if text and not text.startswith("/"):
        await task_event(cid,u,"message",unique_key=m.message_id,chat_title=m.chat.title)
    if m.photo: await task_event(cid,u,"photo",unique_key=m.message_id,chat_title=m.chat.title)
    if m.video: await task_event(cid,u,"video",unique_key=m.message_id,chat_title=m.chat.title)
    if m.voice: await task_event(cid,u,"voice",unique_key=m.message_id,chat_title=m.chat.title)
    if m.photo or m.video or m.voice or m.document:
        await task_event(cid,u,"media",unique_key=m.message_id,chat_title=m.chat.title)

    if m.reply_to_message and m.reply_to_message.from_user and m.reply_to_message.from_user.id!=u.id:
        other=m.reply_to_message.from_user.id
        await task_event(cid,u,"reply",unique_key=m.message_id,chat_title=m.chat.title)
        await task_event(cid,u,"reply_unique",unique_key=other,chat_title=m.chat.title)
        original=m.reply_to_message.message_id
        author=await pool.fetchval("SELECT user_id FROM message_authors WHERE chat_id=$1 AND message_id=$2",cid,original)
        if author and author!=u.id:
            count=await pool.fetchval("""INSERT INTO message_reply_counts(chat_id,message_id,author_id,count) VALUES($1,$2,$3,1)
              ON CONFLICT(chat_id,message_id) DO UPDATE SET count=message_reply_counts.count+1 RETURNING count""",cid,original,author)
            target=await pool.fetchrow("SELECT name FROM users WHERE chat_id=$1 AND user_id=$2",cid,author)
            if target:
                class U:
                    id=author; full_name=target["name"]; username=None
                await task_event(cid,U(),"answer_received",unique_key=m.message_id,chat_title=m.chat.title)
                await task_event(cid,U(),"answer_one",unique_key=f"{original}:{count}",chat_title=m.chat.title)

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
