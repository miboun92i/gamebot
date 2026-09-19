from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

W,H=1320,1600

def font(size,bold=False):
    paths=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try: return ImageFont.truetype(p,size)
        except OSError: pass
    return ImageFont.load_default()

def centered(draw,text,y,f,fill):
    box=draw.textbbox((0,0),text,font=f)
    draw.text(((W-(box[2]-box[0]))/2,y),text,font=f,fill=fill)

def card(draw,box,r=28,fill=(20,19,15),outline=(111,91,46),width=2):
    draw.rounded_rectangle(box,radius=r,fill=fill,outline=outline,width=width)

def podium_card(draw,x,y,w,h,pos,name,xp,rank):
    card(draw,(x,y,x+w,y+h),32,(25,23,17),(146,119,59),3)
    cx=x+w//2
    draw.ellipse((cx-55,y+38,cx+55,y+148),fill=(47,44,34),outline=(183,151,74),width=4)
    pf=font(46,True)
    label={1:"1",2:"2",3:"3"}[pos]
    b=draw.textbbox((0,0),label,font=pf)
    draw.text((cx-(b[2]-b[0])/2,y+64),label,font=pf,fill=(224,190,100))
    nf=font(34,True); rf=font(25); xf=font(28,True)
    display=name[:17]
    b=draw.textbbox((0,0),display,font=nf); draw.text((cx-(b[2]-b[0])/2,y+175),display,font=nf,fill=(241,236,218))
    b=draw.textbbox((0,0),rank,font=rf); draw.text((cx-(b[2]-b[0])/2,y+225),rank,font=rf,fill=(177,163,126))
    xptext=f"{xp:,} XP".replace(","," ")
    b=draw.textbbox((0,0),xptext,font=xf); draw.text((cx-(b[2]-b[0])/2,y+267),xptext,font=xf,fill=(221,184,88))

def render_top(group_title,season_label,players,total_players,top10_xp,days_left):
    im=Image.new("RGB",(W,H),(10,10,8)); d=ImageDraw.Draw(im)
    # subtle premium background
    for i in range(10):
        d.ellipse((-300+i*180,-200+i*80,350+i*180,450+i*80),outline=(28,27,21),width=2)
    centered(d,(group_title or "GROUPE").upper(),70,font(34,True),(180,154,88))
    centered(d,"CLASSEMENT GROUPE",125,font(62,True),(244,239,220))
    centered(d,f"SAISON {season_label}",205,font(26,True),(147,136,105))

    slots=[(455,310,410,360),(65,390,350,330),(905,390,350,330)]
    order=[0,1,2]
    for slot,idx in zip(slots,order):
        if idx<len(players):
            p=players[idx]
            podium_card(d,*slot,idx+1,p["name"],p["xp"],p["rank"])

    y=790
    for idx in range(3,min(7,len(players))):
        p=players[idx]
        card(d,(90,y,1230,y+112),25,(20,19,15),(71,62,39),2)
        d.text((130,y+32),f"{idx+1}.",font=font(35,True),fill=(184,154,79))
        d.text((220,y+27),p["name"][:25],font=font(32,True),fill=(239,234,216))
        d.text((650,y+36),p["rank"],font=font(24),fill=(161,150,119))
        xptext=f"{p['xp']:,} XP".replace(","," ")
        box=d.textbbox((0,0),xptext,font=font(29,True))
        d.text((1180-(box[2]-box[0]),y+31),xptext,font=font(29,True),fill=(216,180,87))
        y+=132

    card(d,(90,1335,1230,1515),30,(17,16,13),(103,86,47),2)
    labels=[("JOUEURS",str(total_players)),("XP TOP 10",f"{top10_xp:,}".replace(","," ")),("FIN SAISON",f"{days_left} j")]
    for i,(lab,val) in enumerate(labels):
        cx=280+i*380
        b=d.textbbox((0,0),val,font=font(36,True)); d.text((cx-(b[2]-b[0])/2,1380),val,font=font(36,True),fill=(230,195,103))
        b=d.textbbox((0,0),lab,font=font(20,True)); d.text((cx-(b[2]-b[0])/2,1432),lab,font=font(20,True),fill=(147,137,107))
    out=BytesIO(); im.save(out,"PNG",optimize=True); out.seek(0); return out
