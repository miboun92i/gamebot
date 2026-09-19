from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

W,H=1600,800
BG=(13,13,11); PANEL=(25,24,20); GOLD=(207,169,87); TEXT=(242,240,234); MUTED=(164,160,151)

def font(size,bold=False):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]:
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()

def txt(d,xy,s,size,fill=TEXT,bold=False,anchor=None):
    d.text(xy,str(s),font=font(size,bold),fill=fill,anchor=anchor)

def box(d,xy,fill=PANEL,outline=(100,84,50),radius=18,width=2):
    d.rounded_rectangle(xy,radius=radius,fill=fill,outline=outline,width=width)

def avatar(d,cx,cy,r,label):
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(34,34,32),outline=(201,190,164),width=2)
    txt(d,(cx,cy),label[:1].upper() if label else "?",r,fill=(215,210,198),bold=True,anchor="mm")

def render_top(group_title,season_label,players,total_players,top10_xp,days_left):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    # soft background glow
    for n in range(8):
        d.ellipse((-250+n*250,-420+n*35,500+n*250,330+n*35),outline=(31,29,23),width=2)
    box(d,(18,18,W-18,H-18),fill=(18,18,15),outline=(118,96,52),radius=25,width=2)

    # brand/header
    box(d,(55,45,155,145),fill=(28,27,22),outline=(99,81,47),radius=16)
    txt(d,(105,95),"M",52,GOLD,True,"mm")
    txt(d,(180,50),"CLASSEMENT GROUPE",22,(211,205,190),True)
    txt(d,(180,78),(group_title or "GROUPE").upper()[:26],42,TEXT,True)
    txt(d,(180,125),"Top des membres de ce groupe",19,MUTED)
    txt(d,(1510,50),f"SAISON {season_label}",25,(232,195,113),True,"ra")
    txt(d,(1510,91),f"Fin dans {days_left} jours",19,MUTED,False,"ra")

    # podium cards: 2, 1, 3
    cards=[(55,175,535,385,1,(56,30,35),(156,88,106)),(560,145,1040,385,0,(49,44,28),(220,178,74)),(1065,175,1545,385,2,(34,32,45),(137,119,175))]
    for x1,y1,x2,y2,idx,fill,accent in cards:
        box(d,(x1,y1,x2,y2),fill=fill,outline=accent,radius=16,width=2)
        pos=idx+1
        cx=(x1+x2)//2
        d.ellipse((cx-22,y1-18,cx+22,y1+26),fill=accent)
        txt(d,(cx,y1+4),pos,21,(20,19,16),True,"mm")
        if idx<len(players):
            p=players[idx]; avatar(d,cx,y1+80,43,p["name"])
            txt(d,(cx,y1+139),p["name"][:20],23,TEXT,True,"ma")
            txt(d,(cx,y1+169),p["rank"].upper(),20,accent,True,"ma")
            txt(d,(cx,y1+198),f'{p["xp"]:,} XP'.replace(","," "),19,(202,198,188),False,"ma")
        else:
            txt(d,(cx,y1+115),"—",28,MUTED,True,"mm")

    # rows 4-7
    y=405
    for idx in range(3,7):
        box(d,(55,y,1545,y+55),fill=(24,23,19),outline=(91,76,46),radius=12,width=1)
        txt(d,(80,y+28),f"#{idx+1}",20,(196,191,179),True,"lm")
        if idx<len(players):
            p=players[idx]; avatar(d,185,y+28,21,p["name"])
            txt(d,(235,y+28),p["name"][:24],21,TEXT,True,"lm")
            txt(d,(1465,y+28),f'{p["rank"]}  —  {p["xp"]:,} XP'.replace(","," "),18,(199,195,185),False,"rm")
        else:
            txt(d,(235,y+28),"—",21,MUTED,False,"lm")
        y+=62

    # footer
    box(d,(55,660,1545,755),fill=(25,24,20),outline=(111,91,52),radius=18,width=2)
    footer=[("MEMBRES DU GROUPE",str(total_players)),("TOP 10",f'{top10_xp:,} XP'.replace(","," ")),("FIN DE SAISON DANS",f"{days_left} JOURS")]
    for i,(lab,val) in enumerate(footer):
        cx=270+i*520
        if i: d.line((cx-260,678,cx-260,737),fill=(75,69,56),width=1)
        txt(d,(cx,685),lab,16,MUTED,False,"ma")
        txt(d,(cx,724),val,26,(232,218,183),True,"ma")

    out=BytesIO();im.save(out,"PNG",optimize=True);out.seek(0);return out
