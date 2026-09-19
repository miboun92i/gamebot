from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

W,H=1536,864
GOLD=(202,163,81); TEXT=(244,242,237); MUTED=(190,186,178)

def font(n,b=False):
    paths=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
           "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if b else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    for p in paths:
        try:return ImageFont.truetype(p,n)
        except OSError:pass
    return ImageFont.load_default()

def tx(d,x,y,s,n,c=TEXT,b=False,a=None): d.text((x,y),str(s),font=font(n,b),fill=c,anchor=a)
def rr(d,xy,fill,outline=(105,83,45),r=14,w=2): d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=w)

def av(im,d,cx,cy,r,p,border):
    raw=p.get("avatar")
    if raw:
        try:
            x=Image.open(BytesIO(raw)).convert("RGB");x=ImageOps.fit(x,(r*2,r*2),Image.Resampling.LANCZOS)
            m=Image.new("L",(r*2,r*2));ImageDraw.Draw(m).ellipse((0,0,r*2-1,r*2-1),fill=255)
            im.paste(x,(cx-r,cy-r),m);d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=border,width=3);return
        except Exception: pass
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(35,35,33),outline=border,width=3)
    tx(d,cx,cy,(p.get("name") or "?")[:1].upper(),r,(220,216,205),True,"mm")

def left(sec,short=False):
    days,rem=divmod(max(0,int(sec)),86400);hours=rem//3600
    return f"{days}j {hours}h" if short else f"{days} JOURS {hours} HEURES"

def render_top(group_title,season_number,month_label,players,total_players,top10_xp,remaining_seconds,group_avatar=None):
    # Geometry is intentionally locked to the approved 1536x864 reference.
    base=Image.new("RGB",(W,H),(9,9,8))
    glow=Image.new("RGBA",(W,H),(0,0,0,0));g=ImageDraw.Draw(glow)
    g.ellipse((-350,-300,650,650),fill=(115,78,28,55));g.ellipse((450,-380,1280,380),fill=(96,71,29,35))
    glow=glow.filter(ImageFilter.GaussianBlur(135));im=Image.alpha_composite(base.convert("RGBA"),glow).convert("RGB");d=ImageDraw.Draw(im)
    rr(d,(20,14,1516,850),(16,16,13),(126,101,57),24,2)

    # HEADER: exact visual scale of reference
    rr(d,(61,31,164,132),(23,22,18),(112,89,50),14,2)
    tx(d,112,82,"M",56,(229,205,148),True,"mm")
    tx(d,183,35,"C L A S S E M E N T   G R O U P E",22,(224,220,210),True)
    tx(d,183,66,(group_title or "GROUPE").upper()[:22],44,TEXT,True)
    tx(d,183,111,"Top des membres de ce groupe",21,(201,197,188))
    tx(d,1480,34,f"SAISON {season_number}",26,(240,205,124),True,"ra")
    tx(d,1480,70,month_label.upper(),19,(216,212,203),False,"ra")
    d.line((1304,94,1480,94),fill=(100,82,50),width=1)
    tx(d,1480,116,"◷  Fin dans "+left(remaining_seconds,True),20,(198,194,186),False,"ra")

    # PODIUM: cards consume the same vertical mass as reference
    cards=[(54,164,523,355,1,(57,26,33),(185,88,108)),(547,124,989,355,0,(48,43,27),(229,184,72)),(1013,164,1482,355,2,(34,32,46),(150,132,190))]
    for x1,y1,x2,y2,idx,fill,accent in cards:
        rr(d,(x1,y1,x2,y2),fill,accent,14,2);cx=(x1+x2)//2
        d.ellipse((cx-22,y1-20,cx+22,y1+24),fill=accent);tx(d,cx,y1+2,idx+1,22,(18,17,14),True,"mm")
        if idx<len(players):
            p=players[idx];av(im,d,cx,y1+72,45,p,accent)
            tx(d,cx,y1+127,p["name"][:18],24,TEXT,True,"ma")
            tx(d,cx,y1+156,p["rank"].upper(),21,accent,True,"ma")
            tx(d,cx,y1+184,f'{p["xp"]:,} XP'.replace(","," "),20,(217,213,204),False,"ma")
        else: tx(d,cx,y1+116,"—",32,MUTED,True,"mm")

    # RANKS 4-7: thick rows, large text and avatars
    y=374
    for idx in range(3,7):
        rr(d,(54,y,1482,y+58),(21,20,17),(100,80,44),11,1)
        tx(d,77,y+29,f"#{idx+1}",24,(211,206,194),True,"lm")
        if idx<len(players):
            p=players[idx];av(im,d,185,y+29,24,p,(180,175,162))
            tx(d,244,y+29,p["name"][:22],24,TEXT,True,"lm")
            tx(d,1450,y+29,f'{p["rank"]}  —  {p["xp"]:,} XP'.replace(","," "),22,(220,216,207),False,"rm")
        else: tx(d,244,y+29,"—",24,MUTED,False,"lm")
        y+=64

    # FOOTER: same three blocks as reference
    rr(d,(54,644,1482,754),(23,22,18),(113,90,49),17,2)
    vals=[("MEMBRES DU GROUPE",str(total_players)),("TOP 10",f'{top10_xp:,} XP'.replace(","," ")),("FIN DE SAISON DANS",left(remaining_seconds))]
    centers=[275,768,1260]
    for i,(lab,val) in enumerate(vals):
        if i:d.line((centers[i]-246,669,centers[i]-246,729),fill=(79,69,51),width=1)
        tx(d,centers[i],669,lab,18,(196,191,182),False,"ma")
        tx(d,centers[i],711,val,28,(241,223,182),True,"ma")

    out=BytesIO();im.save(out,"PNG",optimize=True);out.seek(0);return out
