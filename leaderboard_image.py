from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

W,H=1536,864
BG=(10,10,9); GOLD=(205,166,83); TEXT=(245,243,238); MUTED=(190,186,177)

def font(size,bold=False):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]:
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()

def t(d,xy,s,size,fill=TEXT,bold=False,anchor=None):
    d.text(xy,str(s),font=font(size,bold),fill=fill,anchor=anchor)

def box(d,xy,fill=(21,20,17),outline=(112,91,50),r=18,w=2):
    d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=w)

def avatar(im,d,cx,cy,r,p,outline):
    raw=p.get("avatar")
    if raw:
        try:
            a=Image.open(BytesIO(raw)).convert("RGB")
            a=ImageOps.fit(a,(r*2,r*2),method=Image.Resampling.LANCZOS)
            m=Image.new("L",(r*2,r*2));ImageDraw.Draw(m).ellipse((0,0,r*2-1,r*2-1),fill=255)
            im.paste(a,(cx-r,cy-r),m);d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=outline,width=3);return
        except Exception:pass
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(35,35,32),outline=outline,width=3)
    t(d,(cx,cy),(p.get("name") or "?")[:1].upper(),r,fill=(220,216,205),bold=True,anchor="mm")

def remain(seconds,short=False):
    s=max(0,int(seconds));days,rem=divmod(s,86400);hours=rem//3600
    return f"{days}j {hours}h" if short else f"{days} JOURS {hours} HEURES"

def render_top(group_title,season_number,month_label,players,total_players,top10_xp,remaining_seconds,group_avatar=None):
    im=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(im)
    # warm soft glow like approved reference
    glow=Image.new("RGBA",(W,H),(0,0,0,0));gd=ImageDraw.Draw(glow)
    gd.ellipse((-250,-350,650,550),fill=(133,91,30,55));gd.ellipse((500,-400,1300,350),fill=(113,82,30,38))
    glow=glow.filter(ImageFilter.GaussianBlur(120));im=Image.alpha_composite(im.convert("RGBA"),glow).convert("RGB");d=ImageDraw.Draw(im)
    box(d,(20,14,W-20,H-14),fill=(17,17,14),outline=(132,105,58),r=24,w=2)

    # header
    box(d,(60,31,164,132),fill=(24,23,19),outline=(115,91,50),r=14,w=2)
    t(d,(112,82),"M",54,(231,207,151),True,"mm")
    t(d,(183,36),"C L A S S E M E N T   G R O U P E",21,(224,220,210),True)
    t(d,(183,67),(group_title or "GROUPE").upper()[:22],42,TEXT,True)
    t(d,(183,112),"Top des membres de ce groupe",20,(199,195,187))
    t(d,(1480,34),f"SAISON {season_number}",25,(241,207,127),True,"ra")
    t(d,(1480,70),month_label.upper(),18,(214,211,203),False,"ra")
    d.line((1302,94,1480,94),fill=(100,82,50),width=1)
    t(d,(1480,116),"◷  Fin dans "+remain(remaining_seconds,True),19,(196,193,186),False,"ra")

    # top 3
    cards=[(53,164,523,355,1,(58,27,34),(189,91,112)),(547,124,989,355,0,(48,43,27),(231,186,73)),(1013,164,1483,355,2,(34,32,47),(153,134,193))]
    for x1,y1,x2,y2,idx,fill,accent in cards:
        box(d,(x1,y1,x2,y2),fill=fill,outline=accent,r=14,w=2);cx=(x1+x2)//2
        d.ellipse((cx-22,y1-20,cx+22,y1+24),fill=accent);t(d,(cx,y1+2),idx+1,21,(20,18,15),True,"mm")
        if idx<len(players):
            p=players[idx];avatar(im,d,cx,y1+72,43,p,accent)
            t(d,(cx,y1+126),p["name"][:18],23,TEXT,True,"ma")
            t(d,(cx,y1+154),p["rank"].upper(),20,accent,True,"ma")
            t(d,(cx,y1+181),f'{p["xp"]:,} XP'.replace(","," "),19,(217,213,204),False,"ma")
        else:
            t(d,(cx,y1+116),"—",30,MUTED,True,"mm")

    # 4-7 rows
    y=374
    for idx in range(3,7):
        box(d,(53,y,1483,y+57),fill=(22,21,17),outline=(102,81,44),r=11,w=1)
        t(d,(76,y+29),f"#{idx+1}",23,(210,205,193),True,"lm")
        if idx<len(players):
            p=players[idx];avatar(im,d,185,y+29,23,p,(181,176,163))
            t(d,(243,y+29),p["name"][:22],23,TEXT,True,"lm")
            t(d,(1450,y+29),f'{p["rank"]}  —  {p["xp"]:,} XP'.replace(","," "),21,(219,215,206),False,"rm")
        else:t(d,(243,y+29),"—",23,MUTED,False,"lm")
        y+=64

    # footer
    box(d,(53,644,1483,754),fill=(24,23,19),outline=(116,92,50),r=17,w=2)
    data=[("MEMBRES DU GROUPE",str(total_players)),("TOP 10",f'{top10_xp:,} XP'.replace(","," ")),("FIN DE SAISON DANS",remain(remaining_seconds))]
    centers=[275,768,1260]
    for i,(lab,val) in enumerate(data):
        if i:d.line((centers[i]-246,669,centers[i]-246,728),fill=(80,70,52),width=1)
        t(d,(centers[i],669),lab,17,(194,190,181),False,"ma")
        t(d,(centers[i],711),val,27,(242,224,183),True,"ma")

    out=BytesIO();im.save(out,"PNG",optimize=True);out.seek(0);return out
