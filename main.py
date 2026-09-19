import asyncio, os, random, re, unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import asyncpg
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, MessageReactionUpdated
from ranks import RANKS, rank_for_xp, next_rank
from tasks import TASK_POOL, DAILY_TASK_COUNT, DAILY_BONUS
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
      ON CONFLICT(starts_at,ends_at) DO UPDATE SET label=EXCLUDED.label RETURNING id""",start,end,start.strftime("%Y-%m"))

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
    keys=await pool.fetch("SELECT task_key FROM daily_task_sets WHERE chat_id=$1 AND day=$2",chat_id,day)
    if len(keys)<DAILY_TASK_COUNT:
        seed=f"{chat_id}:{day.isoformat()}"
        rng=random.Random(seed)
        chosen=rng.sample(list(TASK_POOL),DAILY_TASK_COUNT)
        for key in chosen:
            await pool.execute("INSERT INTO daily_task_sets(chat_id,day,task_key) VALUES($1,$2,$3) ON CONFLICT DO NOTHING",chat_id,day,key)
        keys=await pool.fetch("SELECT task_key FROM daily_task_sets WHERE chat_id=$1 AND day=$2 ORDER BY task_key",chat_id,day)
    return [r["task_key"] for r in keys]

async def task_event(chat_id,u,event,unique_key=None,amount=1,chat_title=None):
    day=datetime.now(TZ).date()
    keys=await daily_tasks(chat_id)
    for key in keys:
        task=TASK_POOL[key]
        if task["event"]!=event: continue
        if unique_key is not None:
            inserted=await pool.fetchval("""INSERT INTO task_unique_events(chat_id,user_id,day,task_key,unique_key)
              VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING RETURNING 1""",chat_id,u.id,day,key,str(unique_key))
            if not inserted: continue
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
        if bonus: await add_xp(chat_id,u,DAILY_BONUS,"tasks:5of5",chat_title)
@dp.message(Command("tasks"))
@dp.message(Command("missions"))
async def tasks_cmd(m:Message):
    if m.chat.type=="private": return await m.answer("Utilise /tasks dans un groupe.")
    await ensure_user(m.chat.id,m.from_user,m.chat.title)
    day=datetime.now(TZ).date()
    keys=await daily_tasks(m.chat.id)
    lines=[]
    done=0
    for key in keys:
        task=TASK_POOL[key]
        row=await pool.fetchrow("SELECT progress,claimed FROM task_progress WHERE chat_id=$1 AND user_id=$2 AND day=$3 AND task_key=$4",m.chat.id,m.from_user.id,day,key)
        progress=row["progress"] if row else 0
        claimed=bool(row and row["claimed"])
        done+=int(claimed)
        lines.append(f"{'✅' if claimed else '▫️'} {task['label']} — {min(progress,task['target'])}/{task['target']} · +{task['reward']} XP")
    await m.answer("📋 TÂCHES DU JOUR\n\n"+"\n".join(lines)+f"\n\n🎁 {done}/5 · Bonus 5/5 : +{DAILY_BONUS} XP")


