import asyncio, os, random, unicodedata
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, MessageReactionUpdated, BufferedInputFile, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ranks import RANKS, rank_for_xp, next_rank
from tasks import TASK_POOL, DAILY_TASK_COUNT, DAILY_BONUS
from leaderboard_image import render_top

TOKEN=os.environ["BOT_TOKEN"]
DB_URL=os.environ["DATABASE_URL"]
TZ=ZoneInfo(os.getenv("TIMEZONE","Europe/Paris"))
INTERVAL=int(os.getenv("GAME_INTERVAL_HOURS","2"))
TEST_MODE=os.getenv("TEST_MODE","false").lower()=="true"
OWNER_ID=int(os.getenv("OWNER_ID","0"))
TEST_CHAT_ID=int(os.getenv("TEST_CHAT_ID","0"))
dp=Dispatcher()
pool=None
active_games={}
recent_anagrams={}\nrecent_flags={}

WORDS=["abricot","adresse","aiguille","alarme","amande","animal","appareil","argent","armoire","aventure","banane","bateau","biscuit","bouteille","bureau","cabane","cadeau","cahier","camion","cascade","cerise","chance","chapeau","chocolat","cinema","citron","clavier","cloche","coffre","colline","couleur","courage","cuisine","danseur","diamant","dragon","eclair","ecole","ecran","etoile","famille","fenetre","festival","foret","fromage","garage","gateau","guitare","histoire","horloge","jardin","journal","jungle","lampe","livre","magie","maison","marche","melodie","message","mirage","montagne","moteur","musique","mystere","nature","nuage","ocean","orange","parfum","parole","passage","peinture","pirate","planete","plume","puzzle","rapide","rivage","robot","secret","silence","soleil","sourire","tableau","telegram","tempete","tigre","tomate","train","tresor","valise","village","visage","voyage","astronaute","bibliotheque","extraordinaire","magnifique","parapluie","restaurant","telephone","tourbillon"]
COPY=["incroyable","parapluie","astronaute","magnifique","cacahuete","tourbillon","telegram"]
FLAGS={"🇦🇫":"Afghanistan","🇿🇦":"Afrique du Sud","🇦🇱":"Albanie","🇩🇿":"Algérie","🇩🇪":"Allemagne","🇦🇩":"Andorre","🇦🇴":"Angola","🇦🇬":"Antigua-et-Barbuda","🇸🇦":"Arabie saoudite","🇦🇷":"Argentine","🇦🇲":"Arménie","🇦🇺":"Australie","🇦🇹":"Autriche","🇦🇿":"Azerbaïdjan","🇧🇸":"Bahamas","🇧🇭":"Bahreïn","🇧🇩":"Bangladesh","🇧🇧":"Barbade","🇧🇪":"Belgique","🇧🇿":"Belize","🇧🇯":"Bénin","🇧🇹":"Bhoutan","🇧🇾":"Biélorussie","🇲🇲":"Birmanie","🇧🇴":"Bolivie","🇧🇦":"Bosnie-Herzégovine","🇧🇼":"Botswana","🇧🇷":"Brésil","🇧🇳":"Brunei","🇧🇬":"Bulgarie","🇧🇫":"Burkina Faso","🇧🇮":"Burundi","🇰🇭":"Cambodge","🇨🇲":"Cameroun","🇨🇦":"Canada","🇨🇻":"Cap-Vert","🇨🇫":"République centrafricaine","🇨🇱":"Chili","🇨🇳":"Chine","🇨🇾":"Chypre","🇨🇴":"Colombie","🇰🇲":"Comores","🇨🇬":"Congo","🇨🇩":"République démocratique du Congo","🇰🇵":"Corée du Nord","🇰🇷":"Corée du Sud","🇨🇷":"Costa Rica","🇨🇮":"Côte d’Ivoire","🇭🇷":"Croatie","🇨🇺":"Cuba","🇩🇰":"Danemark","🇩🇯":"Djibouti","🇩🇲":"Dominique","🇪🇬":"Égypte","🇦🇪":"Émirats arabes unis","🇪🇨":"Équateur","🇪🇷":"Érythrée","🇪🇸":"Espagne","🇪🇪":"Estonie","🇸🇿":"Eswatini","🇺🇸":"États-Unis","🇪🇹":"Éthiopie","🇫🇯":"Fidji","🇫🇮":"Finlande","🇫🇷":"France","🇬🇦":"Gabon","🇬🇲":"Gambie","🇬🇪":"Géorgie","🇬🇭":"Ghana","🇬🇷":"Grèce","🇬🇩":"Grenade","🇬🇹":"Guatemala","🇬🇳":"Guinée","🇬🇼":"Guinée-Bissau","🇬🇶":"Guinée équatoriale","🇬🇾":"Guyana","🇭🇹":"Haïti","🇭🇳":"Honduras","🇭🇺":"Hongrie","🇲🇭":"Îles Marshall","🇸🇧":"Îles Salomon","🇮🇳":"Inde","🇮🇩":"Indonésie","🇮🇶":"Irak","🇮🇷":"Iran","🇮🇪":"Irlande","🇮🇸":"Islande","🇮🇱":"Israël","🇮🇹":"Italie","🇯🇲":"Jamaïque","🇯🇵":"Japon","🇯🇴":"Jordanie","🇰🇿":"Kazakhstan","🇰🇪":"Kenya","🇰🇬":"Kirghizistan","🇰🇮":"Kiribati","🇰🇼":"Koweït","🇱🇦":"Laos","🇱🇸":"Lesotho","🇱🇻":"Lettonie","🇱🇧":"Liban","🇱🇷":"Liberia","🇱🇾":"Libye","🇱🇮":"Liechtenstein","🇱🇹":"Lituanie","🇱🇺":"Luxembourg","🇲🇰":"Macédoine du Nord","🇲🇬":"Madagascar","🇲🇾":"Malaisie","🇲🇼":"Malawi","🇲🇻":"Maldives","🇲🇱":"Mali","🇲🇹":"Malte","🇲🇦":"Maroc","🇲🇺":"Maurice","🇲🇷":"Mauritanie","🇲🇽":"Mexique","🇫🇲":"Micronésie","🇲🇩":"Moldavie","🇲🇨":"Monaco","🇲🇳":"Mongolie","🇲🇪":"Monténégro","🇲🇿":"Mozambique","🇳🇦":"Namibie","🇳🇷":"Nauru","🇳🇵":"Népal","🇳🇮":"Nicaragua","🇳🇪":"Niger","🇳🇬":"Nigeria","🇳🇴":"Norvège","🇳🇿":"Nouvelle-Zélande","🇴🇲":"Oman","🇺🇬":"Ouganda","🇺🇿":"Ouzbékistan","🇵🇰":"Pakistan","🇵🇼":"Palaos","🇵🇦":"Panama","🇵🇬":"Papouasie-Nouvelle-Guinée","🇵🇾":"Paraguay","🇳🇱":"Pays-Bas","🇵🇪":"Pérou","🇵🇭":"Philippines","🇵🇱":"Pologne","🇵🇹":"Portugal","🇶🇦":"Qatar","🇩🇴":"République dominicaine","🇨🇿":"Tchéquie","🇷🇴":"Roumanie","🇬🇧":"Royaume-Uni","🇷🇺":"Russie","🇷🇼":"Rwanda","🇰🇳":"Saint-Christophe-et-Niévès","🇱🇨":"Sainte-Lucie","🇸🇲":"Saint-Marin","🇻🇨":"Saint-Vincent-et-les-Grenadines","🇸🇻":"Salvador","🇼🇸":"Samoa","🇸🇹":"Sao Tomé-et-Principe","🇸🇳":"Sénégal","🇷🇸":"Serbie","🇸🇨":"Seychelles","🇸🇱":"Sierra Leone","🇸🇬":"Singapour","🇸🇰":"Slovaquie","🇸🇮":"Slovénie","🇸🇴":"Somalie","🇸🇩":"Soudan","🇸🇸":"Soudan du Sud","🇱🇰":"Sri Lanka","🇸🇪":"Suède","🇨🇭":"Suisse","🇸🇷":"Suriname","🇸🇾":"Syrie","🇹🇯":"Tadjikistan","🇹🇿":"Tanzanie","🇹🇩":"Tchad","🇹🇭":"Thaïlande","🇹🇱":"Timor oriental","🇹🇬":"Togo","🇹🇴":"Tonga","🇹🇹":"Trinité-et-Tobago","🇹🇳":"Tunisie","🇹🇲":"Turkménistan","🇹🇷":"Turquie","🇹🇻":"Tuvalu","🇺🇦":"Ukraine","🇺🇾":"Uruguay","🇻🇺":"Vanuatu","🇻🇦":"Vatican","🇻🇪":"Venezuela","🇻🇳":"Viêt Nam","🇾🇪":"Yémen","🇿🇲":"Zambie","🇿🇼":"Zimbabwe"}

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
        CREATE TABLE IF NOT EXISTS message_activity(\n          chat_id BIGINT,user_id BIGINT,last_text TEXT,last_xp_at TIMESTAMPTZ,\n          spam_window_start TIMESTAMPTZ,spam_count INT DEFAULT 0,xp_blocked_until TIMESTAMPTZ,\n          PRIMARY KEY(chat_id,user_id));\n        CREATE TABLE IF NOT EXISTS daily_task_sets(
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

async def message_activity_xp(m,u,text):
    cid=m.chat.id; now=datetime.now(timezone.utc); clean=norm(text)
    if not clean or len(clean)<3 or text.startswith("/"): return
    row=await pool.fetchrow("SELECT * FROM message_activity WHERE chat_id=$1 AND user_id=$2",cid,u.id)
    if row and row["xp_blocked_until"] and row["xp_blocked_until"]>now: return
    ws=row["spam_window_start"] if row else None; count=row["spam_count"] if row else 0
    if not ws or (now-ws).total_seconds()>30: ws=now; count=0
    count+=1
    repeated=bool(row and row["last_text"] and norm(row["last_text"])==clean)
    if count>=12 or (repeated and count>=5):
        until=now+timedelta(minutes=20)
        await pool.execute("INSERT INTO message_activity(chat_id,user_id,last_text,spam_window_start,spam_count,xp_blocked_until) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(chat_id,user_id) DO UPDATE SET last_text=$3,spam_window_start=$4,spam_count=$5,xp_blocked_until=$6",cid,u.id,text,ws,count,until)
        await m.reply("⚠️ Spam détecté — gain d’XP suspendu pendant 20 minutes.")
        return
    last=row["last_xp_at"] if row else None
    eligible=not repeated and (not last or (now-last).total_seconds()>=8)
    await pool.execute("INSERT INTO message_activity(chat_id,user_id,last_text,last_xp_at,spam_window_start,spam_count) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(chat_id,user_id) DO UPDATE SET last_text=$3,last_xp_at=COALESCE($4,message_activity.last_xp_at),spam_window_start=$5,spam_count=$6",cid,u.id,text,now if eligible else None,ws,count)
    if eligible: await add_xp(cid,u,1,"message_activity",m.chat.title)

def test_allowed(m):
    return TEST_MODE and m.from_user and m.from_user.id==OWNER_ID and (not TEST_CHAT_ID or m.chat.id==TEST_CHAT_ID)

@dp.message(Command("testgame"))
async def test_game(m:Message,bot:Bot):
    if not test_allowed(m): return
    active_games.pop(m.chat.id,None); await start_game(bot,m.chat.id)

@dp.message(Command("testxp"))
async def test_xp(m:Message):
    if not test_allowed(m): return
    try: amount=int((m.text or "").split(maxsplit=1)[1])
    except Exception: return await m.answer("Usage : /testxp 30000")
    if amount<0 or amount>1000000: return await m.answer("Montant test invalide.")
    await add_xp(m.chat.id,m.from_user,amount,"test_xp",m.chat.title)
    await m.answer(f"🧪 +{amount} XP test ajoutés.")

@dp.message(Command("testspam"))
async def test_spam(m:Message):
    if not test_allowed(m): return
    until=datetime.now(timezone.utc)+timedelta(minutes=20)
    await pool.execute("INSERT INTO message_activity(chat_id,user_id,xp_blocked_until) VALUES($1,$2,$3) ON CONFLICT(chat_id,user_id) DO UPDATE SET xp_blocked_until=$3",m.chat.id,m.from_user.id,until)
    await m.answer("🧪 Blocage XP anti-spam activé pour 20 minutes.")

@dp.message(Command("testreset"))
async def test_reset(m:Message):
    if not test_allowed(m): return
    sid=await current_season_id()
    await pool.execute("UPDATE player_season_stats SET xp=0,wins=0,tasks_completed=0,best_streak=0 WHERE chat_id=$1 AND season_id=$2",m.chat.id,sid)
    await m.answer("🧪 Saison du groupe remise à zéro pour le test.")

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

def pick_anagram(chat_id):
    recent=recent_anagrams.setdefault(chat_id,[])
    candidates=[w for w in WORDS if w not in recent] or WORDS
    word=random.choice(candidates)
    recent.append(word)
    if len(recent)>30: del recent[:-30]
    chars=list(word)
    while "".join(chars)==word: random.shuffle(chars)
    difficulty="FACILE" if len(word)<=6 else "MOYEN" if len(word)<=9 else "DIFFICILE"
    return word,"".join(chars),difficulty

def flag_keyboard(options):
    return InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text=options[i],callback_data="flag:"+norm(options[i])),
       InlineKeyboardButton(text=options[i+1],callback_data="flag:"+norm(options[i+1]))]
      for i in range(0,8,2)
    ])

async def start_game(bot,chat_id):
    if chat_id in active_games: return
    await pool.execute("INSERT INTO group_settings(chat_id) VALUES($1) ON CONFLICT DO NOTHING",chat_id)
    cfg=await pool.fetchrow("SELECT * FROM group_settings WHERE chat_id=$1",chat_id)
    if not cfg["games_enabled"]: return
    kinds=[]
    if cfg["game_anagram"]: kinds.append("anagram")
    if cfg["game_copy"]: kinds.append("copy")
    if cfg["game_math"]: kinds.append("math")
    if cfg["game_flag"]: kinds.append("flag")
    if not kinds: return
    kind=random.choice(kinds)
    markup=None
    if kind=="anagram":
        ans,scrambled,difficulty=pick_anagram(chat_id)
        text=f"🧩 ANAGRAMME · {difficulty}\n\nRemets les lettres dans le bon ordre :\n\n🔥  {scrambled.upper()}"
    elif kind=="copy":
        ans=random.choice(COPY); text="⚡ RAPIDITÉ\n\nRecopie exactement ce mot :\n\n🔥  "+ans.upper()
    elif kind=="math":
        x=random.randint(4,25); y=random.randint(2,12); op=random.choice(["+","-","×"])
        ans=str(x+y if op=="+" else x-y if op=="-" else x*y); text=f"🧠 CALCUL MENTAL\n\nCombien font :\n\n🔥  {x} {op} {y} ?"
    else:
        flag,ans=random.choice(list(FLAGS.items()))
        wrong=random.sample([v for v in FLAGS.values() if v!=ans],7)
        options=wrong+[ans]; random.shuffle(options)
        text=f"🚩 DRAPEAU\n\nQuel pays correspond à ce drapeau ?\n\n{flag}"
        markup=flag_keyboard(options)
    msg=await bot.send_message(chat_id,text+"\n\n🏆 Premier à répondre correctement : +250 XP",reply_markup=markup)
    active_games[chat_id]={"kind":kind,"answer":norm(ans),"started":datetime.now(timezone.utc),"message_id":msg.message_id,"cooldowns":{}}

@dp.callback_query(lambda q: q.data and q.data.startswith("flag:"))
async def flag_answer(q:CallbackQuery,bot:Bot):
    if not q.message: return
    cid=q.message.chat.id; game=active_games.get(cid)
    if not game or game.get("kind")!="flag" or game.get("message_id")!=q.message.message_id:
        return await q.answer("Cette manche est terminée.",show_alert=False)
    now=datetime.now(timezone.utc); until=game["cooldowns"].get(q.from_user.id)
    if until and until>now:
        left=max(1,int((until-now).total_seconds()+0.99))
        return await q.answer(f"Attends {left}s avant de réessayer.",show_alert=True)
    choice=q.data.split(":",1)[1]
    if choice!=game["answer"]:
        game["cooldowns"][q.from_user.id]=now+timedelta(seconds=5)
        return await q.answer("❌ Mauvaise réponse · attends 5 secondes.",show_alert=True)
    active_games.pop(cid,None)
    elapsed=(now-game["started"]).total_seconds()
    await add_xp(cid,q.from_user,250,"game_win",q.message.chat.title)
    sid=await current_season_id()
    await pool.execute("UPDATE users SET wins=wins+1 WHERE chat_id=$1 AND user_id=$2",cid,q.from_user.id)
    await pool.execute("UPDATE player_season_stats SET wins=wins+1 WHERE chat_id=$1 AND user_id=$2 AND season_id=$3",cid,q.from_user.id,sid)
    await q.message.edit_reply_markup(reply_markup=None)
    await q.message.answer(f"🏆 {q.from_user.full_name} remporte la manche en {elapsed:.1f}s !\n+250 XP")
    await q.answer("Bonne réponse !")

async def close_finished_seasons(bot):
    now=datetime.now(TZ)
    seasons=await pool.fetch("SELECT id,label FROM seasons WHERE ends_at<=$1",now)
    groups=await pool.fetch("SELECT chat_id,title FROM groups")
    for season in seasons:
        for group in groups:
            cid=group["chat_id"]; sid=season["id"]
            already=await pool.fetchval("SELECT 1 FROM season_closures WHERE chat_id=$1 AND season_id=$2",cid,sid)
            if already: continue
            rows=await pool.fetch("""SELECT s.user_id,s.xp,u.name FROM player_season_stats s
              JOIN users u ON u.chat_id=s.chat_id AND u.user_id=s.user_id
              WHERE s.chat_id=$1 AND s.season_id=$2 ORDER BY s.xp DESC,s.user_id ASC""",cid,sid)
            if not rows:
                await pool.execute("INSERT INTO season_closures(chat_id,season_id) VALUES($1,$2) ON CONFLICT DO NOTHING",cid,sid)
                continue
            async with pool.acquire() as con:
                async with con.transaction():
                    for pos,r in enumerate(rows,1):
                        await con.execute("""INSERT INTO season_results(chat_id,season_id,user_id,position,xp,rank_name)
                          VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING""",
                          cid,sid,r["user_id"],pos,r["xp"],rank_for_xp(r["xp"]))
                    podium=[("champion","Champion"),("vice","Vice-champion"),("top3","Top 3")]
                    for pos,(prefix,label) in enumerate(podium,1):
                        if len(rows)<pos: break
                        code=f"{prefix}_s{sid}_g{abs(cid)}"
                        bid=await con.fetchval("""INSERT INTO badges(code,label,category) VALUES($1,$2,'competition')
                          ON CONFLICT(code) DO UPDATE SET label=EXCLUDED.label RETURNING id""",
                          code,f"{label} · {season['label']}")
                        await con.execute("""INSERT INTO player_badges(chat_id,user_id,badge_id,season_id)
                          VALUES($1,$2,$3,$4) ON CONFLICT DO NOTHING""",cid,rows[pos-1]["user_id"],bid,sid)
                    await con.execute("INSERT INTO season_closures(chat_id,season_id) VALUES($1,$2) ON CONFLICT DO NOTHING",cid,sid)
            names=[r["name"] for r in rows[:3]]
            medals=["🥇","🥈","🥉"]
            text="🏆 SAISON TERMINÉE — "+season["label"]+"\n\n"+ "\n".join(f"{medals[i]} {name}" for i,name in enumerate(names))
            text+="\n\n✨ Nouvelle saison : XP et rang repartent de zéro."
            try: await bot.send_message(cid,text)
            except Exception: pass

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

async def award_badges(chat_id,user_id):
    sid=await current_season_id()
    row=await pool.fetchrow("""SELECT COALESCE(sum(wins),0) wins,COALESCE(sum(tasks_completed),0) tasks,
      count(*) seasons FROM player_season_stats WHERE chat_id=$1 AND user_id=$2""",chat_id,user_id)
    checks=[("wins_100",row["wins"]>=100),("wins_500",row["wins"]>=500),
            ("tasks_100",row["tasks"]>=100),("tasks_500",row["tasks"]>=500),
            ("veteran_3",row["seasons"]>=3),("ancient_6",row["seasons"]>=6),("legend_12",row["seasons"]>=12)]
    for code,ok in checks:
        if ok:
            bid=await pool.fetchval("SELECT id FROM badges WHERE code=$1",code)
            await pool.execute("""INSERT INTO player_badges(chat_id,user_id,badge_id,season_id)
              VALUES($1,$2,$3,$4) ON CONFLICT DO NOTHING""",chat_id,user_id,bid,sid)

@dp.message(Command("stats"))
async def stats_cmd(m:Message):
    if m.chat.type=="private": return await m.answer("Utilise /stats dans un groupe.")
    sid=await ensure_user(m.chat.id,m.from_user,m.chat.title)
    await award_badges(m.chat.id,m.from_user.id)
    cur=await pool.fetchrow("""SELECT xp,wins,tasks_completed,best_streak FROM player_season_stats
      WHERE chat_id=$1 AND user_id=$2 AND season_id=$3""",m.chat.id,m.from_user.id,sid)
    pos=await pool.fetchval("""SELECT 1+count(*) FROM player_season_stats
      WHERE chat_id=$1 AND season_id=$2 AND xp>$3""",m.chat.id,sid,cur["xp"])
    career=await pool.fetchrow("""SELECT COALESCE(sum(xp),0) lifetime_xp,COALESCE(sum(wins),0) wins,
      COALESCE(sum(tasks_completed),0) tasks,count(*) seasons,COALESCE(max(xp),0) best_xp
      FROM player_season_stats WHERE chat_id=$1 AND user_id=$2""",m.chat.id,m.from_user.id)
    podiums=await pool.fetchval("SELECT count(*) FROM season_results WHERE chat_id=$1 AND user_id=$2 AND position<=3",m.chat.id,m.from_user.id)
    firsts=await pool.fetchval("SELECT count(*) FROM season_results WHERE chat_id=$1 AND user_id=$2 AND position=1",m.chat.id,m.from_user.id)
    badges=await pool.fetch("""SELECT b.label FROM player_badges pb JOIN badges b ON b.id=pb.badge_id
      WHERE pb.chat_id=$1 AND pb.user_id=$2 ORDER BY pb.earned_at DESC LIMIT 3""",m.chat.id,m.from_user.id)
    badge_text=" · ".join("🏅 "+b["label"] for b in badges) if badges else "Aucun pour le moment"
    await m.answer(
      f"📊 STATS — {m.from_user.full_name}\n\n"
      f"🏅 {rank_for_xp(cur['xp'])} · {cur['xp']} XP · #{pos}\n"
      f"🎮 {cur['wins']} victoires cette saison\n"
      f"📋 {cur['tasks_completed']} tâches complétées\n\n"
      f"🏆 CARRIÈRE\n"
      f"XP total : {career['lifetime_xp']}\n"
      f"Saisons jouées : {career['seasons']}\n"
      f"Podiums : {podiums} · #1 : {firsts}\n"
      f"Meilleure saison : {career['best_xp']} XP\n\n"
      f"🎖 {badge_text}")

@dp.message(Command("badges"))
async def badges_cmd(m:Message):
    await ensure_user(m.chat.id,m.from_user,m.chat.title)
    await award_badges(m.chat.id,m.from_user.id)
    rows=await pool.fetch("""SELECT b.label,b.category,pb.earned_at FROM player_badges pb
      JOIN badges b ON b.id=pb.badge_id WHERE pb.chat_id=$1 AND pb.user_id=$2 ORDER BY pb.earned_at""",m.chat.id,m.from_user.id)
    if not rows: return await m.answer("🎖 Tu n’as pas encore de badge dans ce groupe.")
    await m.answer("🎖 TES BADGES\n\n"+"\n".join(f"• {r['label']} · {r['category']}" for r in rows))

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

async def group_scores():
    sid=await current_season_id()
    return await pool.fetch("""WITH ranked AS (
      SELECT s.chat_id,s.xp,ROW_NUMBER() OVER(PARTITION BY s.chat_id ORDER BY s.xp DESC,s.user_id) rn
      FROM player_season_stats s WHERE s.season_id=$1)
      SELECT g.chat_id,COALESCE(g.title,'Groupe') title,COALESCE(SUM(r.xp) FILTER(WHERE r.rn<=10),0)::BIGINT score
      FROM groups g LEFT JOIN ranked r ON r.chat_id=g.chat_id
      GROUP BY g.chat_id,g.title ORDER BY score DESC,g.chat_id""",sid)

@dp.message(Command("grouprank"))
async def group_rank_cmd(m:Message):
    if m.chat.type=="private": return await m.answer("Utilise /grouprank dans un groupe.")
    await ensure_user(m.chat.id,m.from_user,m.chat.title)
    rows=await group_scores()
    for i,r in enumerate(rows,1):
        if r["chat_id"]==m.chat.id:
            return await m.answer(f"🌐 CLASSEMENT GROUPE\n\n🏆 {r['title']}\n📍 #{i} sur {len(rows)} groupes\n⭐ {r['score']:,} XP · Top 10".replace(","," "))

@dp.message(Command("grouptop"))
async def group_top_cmd(m:Message):
    rows=await group_scores()
    if not rows: return await m.answer("🌐 Aucun groupe classé pour le moment.")
    medals=["🥇","🥈","🥉"]
    lines=[]
    for i,r in enumerate(rows[:10],1):
        icon=medals[i-1] if i<=3 else f"{i}."
        lines.append(f"{icon} {r['title']} — {r['score']:,} XP".replace(","," "))
    await m.answer("🌐 TOP GROUPES — TOP 10\n\n"+"\n".join(lines)+"\n\nScore = XP cumulée des 10 meilleurs joueurs du groupe.")

@dp.message(Command("groupranks"))
async def group_ranks_cmd(m:Message):
    await m.answer("🌐 RANGS DE GROUPE\n\nLe rang d’un groupe correspond à sa position dans /grouptop pour la saison en cours.\nLe score utilisé est l’XP cumulée de ses 10 meilleurs joueurs.")

@dp.message(Command("season"))
async def season_cmd(m:Message):
    if m.chat.type=="private": return await m.answer("Utilise /season dans un groupe.")
    sid=await ensure_user(m.chat.id,m.from_user,m.chat.title)
    season=await pool.fetchrow("SELECT label,ends_at FROM seasons WHERE id=$1",sid)
    me=await pool.fetchrow("SELECT xp,wins,tasks_completed FROM player_season_stats WHERE chat_id=$1 AND user_id=$2 AND season_id=$3",m.chat.id,m.from_user.id,sid)
    pos=await pool.fetchval("SELECT 1+count(*) FROM player_season_stats WHERE chat_id=$1 AND season_id=$2 AND xp>$3",m.chat.id,sid,me["xp"])
    top=await pool.fetch("""SELECT u.name,s.xp FROM player_season_stats s JOIN users u ON u.chat_id=s.chat_id AND u.user_id=s.user_id WHERE s.chat_id=$1 AND s.season_id=$2 ORDER BY s.xp DESC,s.user_id LIMIT 3""",m.chat.id,sid)
    end=season["ends_at"].astimezone(TZ); delta=end-datetime.now(TZ); hours=max(0,int(delta.total_seconds()//3600)); days,hours=divmod(hours,24)
    podium="\n".join(f"{['🥇','🥈','🥉'][i]} {r['name']} — {r['xp']} XP" for i,r in enumerate(top)) or "Pas encore de classement"
    await m.answer(f"🏆 SAISON — {season['label']}\n\n⏳ {days}j {hours}h restantes\n🏅 {rank_for_xp(me['xp'])} · {me['xp']} XP · #{pos}\n🎮 {me['wins']} victoires · 📋 {me['tasks_completed']} tâches\n\n{podium}\n\n🔄 Reset : {end.strftime('%d/%m à %H:%M')}")

@dp.message(Command("help"))
async def help_cmd(m:Message):
    await m.answer("🎮 COMMANDES\n\n/rank — ton rang\n/ranks — tous les rangs\n/top — Top 7 du groupe\n/stats — tes statistiques\n/season — saison actuelle\n/tasks — tâches du jour\n/badges — tes badges\n/grouprank — rang du groupe\n/groupranks — système des groupes\n/grouptop — Top groupes\n/settings — réglages admins\n/help — cette aide")

def settings_keyboard(row):
    def b(label,key,val): return InlineKeyboardButton(text=f"{label} {'✅' if val else '❌'}",callback_data="set:"+key)
    return InlineKeyboardMarkup(inline_keyboard=[
      [b("Jeux","games_enabled",row["games_enabled"]),b("Tâches","tasks_enabled",row["tasks_enabled"])],
      [b("Anagramme","game_anagram",row["game_anagram"]),b("Calcul","game_math",row["game_math"])],
      [b("Recopie","game_copy",row["game_copy"]),b("Drapeau","game_flag",row["game_flag"])],
      [b("Annonces rang","rank_announcements",row["rank_announcements"])],
      [b("Fin saison","season_announcements",row["season_announcements"])]
    ])

@dp.message(Command("settings"))
async def settings_cmd(m:Message,bot:Bot):
    if m.chat.type=="private": return await m.answer("Utilise /settings dans un groupe.")
    member=await bot.get_chat_member(m.chat.id,m.from_user.id)
    if member.status not in ("administrator","creator"): return await m.answer("🔒 Réservé aux administrateurs.")
    await pool.execute("INSERT INTO group_settings(chat_id) VALUES($1) ON CONFLICT DO NOTHING",m.chat.id)
    row=await pool.fetchrow("SELECT * FROM group_settings WHERE chat_id=$1",m.chat.id)
    await m.answer("⚙️ RÉGLAGES DU GROUPE\n\nAppuie sur un bouton pour activer/désactiver.",reply_markup=settings_keyboard(row))

@dp.callback_query(lambda q: q.data and q.data.startswith("set:"))
async def settings_callback(q:CallbackQuery,bot:Bot):
    if not q.message: return
    member=await bot.get_chat_member(q.message.chat.id,q.from_user.id)
    if member.status not in ("administrator","creator"): return await q.answer("Admins uniquement.",show_alert=True)
    key=q.data.split(":",1)[1]
    allowed={"games_enabled","tasks_enabled","rank_announcements","season_announcements","game_anagram","game_math","game_copy","game_flag"}
    if key not in allowed: return
    await pool.execute(f"UPDATE group_settings SET {key}=NOT {key} WHERE chat_id=$1",q.message.chat.id)
    row=await pool.fetchrow("SELECT * FROM group_settings WHERE chat_id=$1",q.message.chat.id)
    await q.message.edit_reply_markup(reply_markup=settings_keyboard(row)); await q.answer("Réglage enregistré")

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
    scheduler.add_job(close_finished_seasons,"cron",hour=0,minute=2,args=[bot],id="season_close")
    await close_finished_seasons(bot)
    scheduler.start()
    try: await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await pool.close()

if __name__=="__main__":
    asyncio.run(main())
