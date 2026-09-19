from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

W,H=1536,768
BG=(12,12,10); GOLD=(202,164,82); TEXT=(244,242,237); MUTED=(184,180,170)

def font(size,bold=False):
    names=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
           "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    for p in names:
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()

def t(d,xy,s,size,fill=TEXT,bold=False,anchor=None):
    d.text(xy,str(s),font=font(size,bold),fill=fill,anchor=anchor)

def box(d,xy,fill=(22,21,18),outline=(107,88,50),r=18,w=2):
    d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=w)

def paste_avatar(im,d,cx,cy,r,p,outline):
    raw=p.get("avatar")
    if raw:
        try:
            av=Image.open(BytesIO(raw)).convert("RGB")
            av=ImageOps.fit(av,(r*2,r*2),method=Image.Resampling.LANCZOS)
            mask=Image.new("L",(r*2,r*2),0); md=ImageDraw.Draw(mask);md.ellipse((0,0,r*2-1,r*2-1),fill=255)
            im.paste(av,(cx-r,cy-r),mask)
            d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=outline,width=3)
            return
        except Exception: pass
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(37,37,34),outline=outline,width=3)
    t(d,(cx,cy),(p.get("name") or "?")[:1].upper(),max(18,r),fill=(220,216,205),bold=True,anchor="mm")

def remaining_text(seconds):
    seconds=max(0,int(seconds)); days,rem=divmod(seconds,86400); hours=rem//3600
    return f"{days} JOURS {hours} HEURES"

def render_top(group_title,season_number,month_label,players,total_players,top10_xp,remaining_seconds,group_avatar=None):
    im=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(im)
    box(d,(20,14,W-20,H-14),fill=(18,18,15),outline=(125,101,56),r=24,w=2)

    # logo + header
    logo={"name":"M","avatar":group_avatar}
    paste_avatar(im,d,110,82,46,logo,(121,98,55))
    if not group_avatar:t(d,(110,82),"M",48,GOLD,True,"mm")
    t(d,(180,34),"C L A S S E M E N T   G R O U P E",20,(218,214,203),True)
    t(d,(180,62),(group_title or "GROUPE").upper()[:24],38,TEXT,True)
    t(d,(180,108),"Top des membres de ce groupe",19,MUTED)
    t(d,(1480,34),f"SAISON {season_number}",23,(237,202,126),True,"ra")
    t(d,(1480,67),month_label.upper(),17,(210,207,199),False,"ra")
    d.line((1320,91,1480,91),fill=(90,77,51),width=1)
    t(d,(1480,111),"◷  Fin dans "+remaining_text(remaining_seconds).lower().replace(" jours","j").replace(" heures","h"),17,MUTED,False,"ra")

    # podium
    cards=[(52,162,522,354,1,(55,27,33),(177,91,111)),(546,124,990,354,0,(48,43,27),(226,181,72)),(1014,162,1484,354,2,(34,32,46),(145,128,185))]
    for x1,y1,x2,y2,idx,fill,accent in cards:
        box(d,(x1,y1,x2,y2),fill=fill,outline=accent,r=15,w=2);cx=(x1+x2)//2
        d.ellipse((cx-21,y1-18,cx+21,y1+24),fill=accent)
        t(d,(cx,y1+3),str(idx+1),20,(20,18,15),True,"mm")
        if idx<len(players):
            p=players[idx];paste_avatar(im,d,cx,y1+75,42,p,accent)
            t(d,(cx,y1+130),p["name"][:18],21,TEXT,True,"ma")
            t(d,(cx,y1+157),p["rank"].upper(),18,accent,True,"ma")
            t(d,(cx,y1+183),f'{p["xp"]:,} XP'.replace(","," "),17,(210,206,197),False,"ma")
        else:t(d,(cx,y1+115),"—",27,MUTED,True,"mm")

    # #4-#7
    y=372
    for idx in range(3,7):
        box(d,(52,y,1484,y+53),fill=(23,22,18),outline=(91,75,44),r=11,w=1)
        t(d,(76,y+27),f"#{idx+1}",19,(203,198,186),True,"lm")
        if idx<len(players):
            p=players[idx];paste_avatar(im,d,183,y+27,21,p,(170,165,151))
            t(d,(235,y+27),p["name"][:22],20,TEXT,True,"lm")
            t(d,(1430,y+27),f'{p["rank"]}  —  {p["xp"]:,} XP'.replace(","," "),18,(211,207,198),False,"rm")
        else:t(d,(235,y+27),"—",20,MUTED,False,"lm")
        y+=60

    # footer
    box(d,(52,624,1484,730),fill=(25,24,20),outline=(112,91,50),r=17,w=2)
    data=[("MEMBRES DU GROUPE",str(total_players)),("TOP 10",f'{top10_xp:,} XP'.replace(","," ")),("FIN DE SAISON DANS",remaining_text(remaining_seconds))]
    centers=[270,768,1265]
    for i,(lab,val) in enumerate(data):
        if i:d.line((centers[i]-250,647,centers[i]-250,708),fill=(78,69,51),width=1)
        t(d,(centers[i],651),lab,15,MUTED,False,"ma");t(d,(centers[i],692),val,24,(236,218,178),True,"ma")

    out=BytesIO();im.save(out,"PNG",optimize=True);out.seek(0);return out
