"""Seolnong Hangul composition and centerline drawings.

Every modern syllable uses shared initial, medial, and final components.
Stroke expansion follows placement at a common width of 60 units."""
from pathlib import Path
from functools import lru_cache
import json
import math
import pathops
from .hieuh_forms import draw_hieuh, h_geometry
from .cap_forms import cap_geometry, draw_head
from .ascii_shapes import LATIN, LOWER

ROOT = Path(__file__).resolve().parent
STROKE = 60.0
MASTERS = json.loads((ROOT / 'jamo_masters.json').read_text(encoding='utf-8'))
EXTRA_CODEPOINTS = [0x00B7, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D,
                    0x2026, 0x2190, 0x2191, 0x2192, 0x2193, 0x20A9]
L_NAMES = ['g','gg','n','d','dd','r','m','b','bb','s','ss','o','j','jj','ch','k','t','p','h']
T_NAMES = [None,'g','gg','gs','n','nj','nh','d','r','rg','rm','rb','rs','rt','rp','rh',
           'm','b','bs','s','ss','o','j','ch','k','t','p','h']
VERTICAL = {0,1,2,3,4,5,6,7,20}
HORIZONTAL = {8,12,13,17,18}
COMPOUND = {9:(8,0),10:(8,1),11:(8,20),14:(13,4),15:(13,5),16:(13,20),19:(18,20)}
PAIRS = {'gg':('g','g'),'dd':('d','d'),'bb':('b','b'),'ss':('s','s'),'jj':('j','j'),
         'gs':('g','s'),'nj':('n','j'),'nh':('n','h'),'rg':('r','g'),'rm':('r','m'),
         'rb':('r','b'),'rs':('r','s'),'rt':('r','t'),'rp':('r','p'),'rh':('r','h'),'bs':('b','s')}
PAIR_PRESSURE = {'n': .90, 'r': 1.15, 'm': 1.10, 'b': 1.10,
                 'ch': 1.10, 't': 1.10, 'p': 1.05, 'h': 1.25}


class Drawing:
    def __init__(self): self.path = pathops.Path()
    def stroke(self, commands, width=STROKE):
        p = pathops.Path()
        for c in commands:
            op, vals = c[0], c[1:]
            if op == 'M': p.moveTo(*vals)
            elif op == 'L': p.lineTo(*vals)
            elif op == 'C': p.cubicTo(*vals)
            elif op == 'Q': p.quadTo(*vals)
            elif op == 'Z': p.close()
        p.stroke(width, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4)
        p.convertConicsToQuads(0.06)
        self.path.addPath(p)
    def line(self, x1,y1,x2,y2,width=STROKE):
        self.stroke([('M',x1,y1),('L',x2,y2)],width)
    def ellipse(self,cx,cy,rx,ry,width=STROKE):
        k=0.5522847498307936
        self.stroke([('M',cx+rx,cy),('C',cx+rx,cy+ry*k,cx+rx*k,cy+ry,cx,cy+ry),
          ('C',cx-rx*k,cy+ry,cx-rx,cy+ry*k,cx-rx,cy),
          ('C',cx-rx,cy-ry*k,cx-rx*k,cy-ry,cx,cy-ry),
          ('C',cx+rx*k,cy-ry,cx+rx,cy-ry*k,cx+rx,cy),('Z',)],width)
    def add(self,p): self.path.addPath(p)
    def finish(self,pen):
        self.path.convertConicsToQuads(0.06)
        q=pathops.simplify(self.path,fix_winding=True,keep_starting_points=True,clockwise=True)
        q.convertConicsToQuads(0.06)
        q.draw(pen)


def transform(commands,box):
    x0,y0,x1,y1=box; w=x1-x0; h=y1-y0
    return [(c[0], *[x0+v*w if i%2==0 else y0+v*h for i,v in enumerate(c[1:])]) for c in commands]


def pair_boxes(name, box, role='final'):
    x0,y0,x1,y1=box; w=x1-x0; a,b=PAIRS[name]
    gap=80.0
    if role == 'final':
        wa,wb=PAIR_PRESSURE.get(a,1.0),PAIR_PRESSURE.get(b,1.0)
    else:
        wa=wb=1.0
    split=x0+(w-gap)*wa/(wa+wb)
    return (x0,y0,split,y1),(split+gap,y0,x1,y1)


def smoothstep(lo, hi, value):
    t = max(0.0, min(1.0, (value - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def legacy_giyeok_path(box, role='initial'):
    """The previous skeleton remains the source for kieuk and final giyeok."""
    x0,y0,x1,y1=box; w=x1-x0; h=y1-y0
    if role == 'final': end,control=.92,.96
    elif h/max(w,1)<1.0: end,control=.89,.96
    else: end,control=.74,.90
    return [('M',.02,1),('L',.87,1),('C',.95,1,.96,.97,.96,.88),
            ('C',.96,.55,control,.18,end,0)]


def giyeok_geometry(box, width=STROKE, role='initial', sweep_gain=1.0):
    """Contextual initial curve from the available box, not a syllable list.

    Tall or nearly square slots allow the lower stroke to return leftward.
    Very wide slots keep a short descent, and narrow paired slots damp the
    return so two giyeoks still have distinct interiors at the same pen width.
    sweep_gain is a study axis; the released drawing uses its default 1.0.
    """
    x0,y0,x1,y1=box; w=x1-x0; h=y1-y0
    aspect=h/max(w,1.0)
    verticality=smoothstep(.72,1.08,aspect)
    narrow=.35+.65*smoothstep(width*2.2,width*5.6,w)
    sweep=min(.76,(.16+.44*verticality)*narrow*sweep_gain)
    end=.96-sweep
    # A long initial keeps its descending direction before turning; a short
    # one distributes the same gesture over the available shallow envelope.
    turn_y=.48+.10*smoothstep(1.05,1.9,aspect)
    control_x=min(.94,end+.30)
    return {'aspect':aspect,'verticality':verticality,'narrow_damping':narrow,
            'sweep':sweep,'end_x':end,'turn_y':turn_y,'control_x':control_x,
            'role':role,'width':width,
            'path':[('M',.02,1),('L',.87,1),
                    ('C',.95,1,.96,.97,.96,.88),
                    ('C',.96,turn_y,control_x,.14,end,0)]}


def draw_jieut_body(d, box, width=STROKE):
    """Reuse the photographed Siot gesture under J/Chieuch's top bar.

    A long descending main stroke and a lower, shorter right branch form one
    family with Siot. The centerline is positioned before stroke expansion,
    so compression and paired jamo never thin the common pen.
    """
    for path in MASTERS['s.initial']['paths']:
        d.stroke(transform(path, box), width)


def draw_jieut(d, box, width=STROKE):
    x0, y0, x1, y1 = box
    w = x1 - x0
    d.line(x0 + .02 * w, y1, x0 + .98 * w, y1, width)
    draw_jieut_body(d, box, width)


def draw_chieuch(d, box, width=STROKE, role='initial', form='parallel'):
    g = cap_geometry(box, width, role)
    draw_head(d, g, form)
    draw_jieut_body(d, (box[0], box[1], box[2], g['bar_y']), width)


@lru_cache(maxsize=4096)
def consonant(name,box,width=STROKE,role='initial',form='parallel',variant=None):
    d=Drawing(); x0,y0,x1,y1=box; w=x1-x0; h=y1-y0
    if name in PAIRS:
        a,b=PAIRS[name]; ba,bb=pair_boxes(name,box,role)
        d.add(consonant(a,ba,width,role,form))
        d.add(consonant(b,bb,width,role,form))
        return d.path
    old_g_path=legacy_giyeok_path(box,role)
    g_path=giyeok_geometry(box,width,role)['path'] if role=='initial' else old_g_path
    specs={
      'g':[g_path],
      'n':[[('M',.05,1),('L',.05,.18),('C',.05,.03,.15,0,.32,0),('L',1,.035)]],
      'd':[[('M',1,1),('L',.08,1),('C',.02,1,0,.98,0,.91),('L',0,.08),('C',0,.02,.02,0,.09,0),('L',1,.025)]],
      'm':[[('M',0,1),('L',1,1),('L',1,0),('L',0,0),('Z',)]],
      'b':[[('M',0,1),('L',0,.06),('C',0,.02,.02,0,.06,0),('L',.94,0),('C',.98,0,1,.02,1,.06),('L',1,1)], [('M',0,.53),('L',1,.53)]],
      'k':[old_g_path, [('M',.04,.56),('L',.93,.56)]],
      'p':[[('M',0,1),('L',1,1)], [('M',0,0),('L',1,.015)], [('M',.16,1),('L',.34,.005)], [('M',.84,1),('L',.66,.01)]],
    }
    if name=='o': d.ellipse((x0+x1)/2,(y0+y1)/2,w*.48,h*.48,width)
    elif name=='h': draw_hieuh(d,box,width,role,form)
    elif name=='j': draw_jieut(d,box,width)
    elif name=='ch': draw_chieuch(d,box,width,role,form)
    else:
        key = 'n.shallow' if name=='n' and variant=='shallow' else (
            'r.final' if name=='r' and role=='final' else name+'.initial')
        paths=MASTERS[key]['paths'] if key in MASTERS else specs[name]
        for s in paths: d.stroke(transform(s,box),width)
    return d.path


def vertical_vowel(d,v,x,y0,y1,left=135,right=140,width=STROKE,
                   long_anchor=None, photo_eo=False, left_floor=None):
    h=y1-y0; cy=y0+h*.52; dy=h*.20
    if v in {0,2}:
        lean=h*(3/127)
        d.line(x-lean/2,y0,x+lean/2,y1,width)
        arm=min(h*(35/127),220)
        cy=y0+h*(64/127)
        for yy in ([cy-dy/2,cy+dy/2] if v==2 else [cy]):
            sx=x+(yy-(y0+y1)/2)*(3/127)+width*(5/36)
            d.line(sx,yy,sx+arm,yy-arm*(5/35),width)
        return
    if v==4 and long_anchor is not None:
        d.line(x,y0,x,y1,width)
        ax,ay=long_anchor
        d.line(ax,ay,x-6.7,ay,width)
        return
    if v in {4,6} and photo_eo:
        lean=h*(4/126)
        d.stroke([('M',x+lean/2,y1),
                  ('C',x+lean/4,y1-h*(44/126),x-lean/2,y0+h*(37/126),x-lean/2,y0)],width)
        arm=min(h*(32/126),140)
        cy=y0+h*(66/126)
        for yy in ([cy-dy/2,cy+dy/2] if v==6 else [cy]):
            ex=x-lean*.75
            reach=min(arm,ex-left_floor) if left_floor is not None else arm
            d.line(ex-reach,yy-reach*(7/32),ex,yy,width)
        return
    d.line(x,y0,x,y1,width)
    if v in {1,2,3}:
        arm=155 if v in {1,3} else right
        for yy in ([cy-dy/2,cy+dy/2] if v in {2,3} else [cy]): d.line(x,yy,x+arm,yy-4,width)
    elif v in {4,5,6,7}:
        for yy in ([cy-dy/2,cy+dy/2] if v in {6,7} else [cy]): d.line(x-left,yy-9,x,yy,width)
    if v in {1,3,5,7}: d.line(x+155,y0-4,x+155,y1,width)


def horizontal_vowel(d,v,x0,x1,y0,y1,width=STROKE,slope=3.0):
    cx=(x0+x1)/2; spread=(x1-x0)*.19
    if v in {8,12}:
        d.line(x0,y0,x1,y0+slope,width)
        for x in ([cx-spread,cx+spread] if v==12 else [cx]): d.line(x,y0,x,y1,width)
    elif v in {13,17}:
        d.line(x0,y1,x1,y1,width)
        for x in ([cx-spread,cx+spread] if v==17 else [cx]): d.line(x,y0,x,y1,width)
    else: d.line(x0,(y0+y1)/2,x1,(y0+y1)/2,width)


def final_profile(v,t):
    if not t: return None
    n=T_NAMES[t]
    if n=='m':
        # A full rectangular frame appears heavier than the open or rounded
        # finals. Reduce its width and vertical envelope at unchanged pen width.
        # This is the single-final profile; the mieum inside a cluster keeps its
        # independently allocated narrow component box.
        return {'kind':'box','name':n,'box':(235,40,765,295)}
    if n=='o':
        if v in {4,5,6,7}: ellipse=(500,185.5,257.95,127.3)
        elif v in {0,1,2,3}: ellipse=(484.925,178.8,278.05,120.6)
        else: ellipse=(500,170,280,139)
        return {'kind':'oval','name':n,'ellipse':ellipse}
    if n=='r' and v in VERTICAL:
        box=tuple(MASTERS['r.final']['calibrated_box']);kind='curl'
    else:
        top=320 if n in {'h','nh','rh'} else 335
        box=(205,28,795,top)
        kind='hieuh' if n in {'h','nh','rh'} else ('box' if n in {'m','b','p'} else 'other')
    return {'kind':kind,'name':n,'box':box}


def limit_final_height(profile,top):
    q=dict(profile)
    if q['kind']=='oval':
        cx,cy,rx,ry=q['ellipse'];bottom=cy-ry
        if cy+ry>top: cy,ry=(bottom+top)/2,(top-bottom)/2
        q['ellipse']=(cx,cy,rx,ry)
    else:
        x0,y0,x1,y1=q['box'];q['box']=(x0,y0,x1,min(y1,top))
    return q


@lru_cache(maxsize=11172)
def layout_for(l,v,t):
    """Return shared L/V/T placement; no character or codepoint is inspected."""
    n=L_NAMES[l]; paired=n in PAIRS; fp=final_profile(v,t)
    q={'initial_name':n,'initial_variant':None,'final':fp,'vowel_index':v,
       'vowel_class':'vertical' if v in VERTICAL else ('horizontal' if v in HORIZONTAL else 'compound')}
    if v in VERTICAL:
        y0,y1=(420,778.45) if t else (65,820)
        if paired:
            x0,x1=(120,510) if v in {1,3,5,7} else ((150,550) if v in {4,6} else (145,575))
        else:
            x0,x1=190,(480 if v in {1,3,5,7} else (580 if v in {0,2,20} else 555))
            key=n+'.initial'
            if t and key in MASTERS and v in {0,2,4,6,20}:
                x0,y0,x1,y1=MASTERS[key]['calibrated_box']
        if n=='h' and t: y0,y1=420,820
        q['initial_box']=(x0,y0,x1,y1)
        vy0,vy1=(423.35,805.25) if t else (50,820)
        if fp and fp['kind']=='curl': vy0,vy1=423.35,775.10
        if fp and fp['kind']=='oval':
            vy0,vy1=(383.15,805.25) if v in {4,5,6,7} else (376.45,801.90)
        q['vertical_y']=(vy0,vy1)
        # The slanted short-arm master belongs to compact, with-final forms.
        # Tall forms retain the wider medial column. Two arms also need more
        # lateral clearance than one, irrespective of which initial is used.
        q['photo_eo']=bool(t) and v in {4,6}
        # A closed right wall needs literal white clearance for the medial arm;
        # an open/curved initial may legitimately let the arm enter its interior.
        q['eo_left_floor']=x1+STROKE+12 if n in {'m','b','bb'} else None
        q['vertical_x']=(731.15 if v==4 else 766.15) if t and v in {4,6} else (770 if v in {4,6} else (
            (680 if paired else 655) if v in {5,7} else
            (650 if v in {1,3} else (790 if v==20 else (674.2 if fp and fp['kind']=='oval' and not paired else 705)))))
        q['long_eo_anchor']=None
        if n=='s' and v==4:
            # Align the medial arm with the opening in the shared S master.
            q['vertical_x']=747.9
            q['long_eo_anchor']=(x0+(x1-x0)*(68/90),y0+(y1-y0)*(53/107))
        return q
    if v in HORIZONTAL:
        q['initial_box']=(215,570 if t else 355,785,820)
        q['horizontal_box']=(190,425 if t else 65,810,500 if t else 245)
    else:
        q['initial_box']=(140 if paired else 190,570 if t else 340,530 if paired else 525,820)
        q['horizontal_box']=(175,420 if t else 70,575,500 if t else 230)
        hv,vv=COMPOUND[v]
        q['vertical_x']=700 if vv==5 else (660 if vv==1 else (795 if vv==20 else 710))
        q['vertical_y']=(420 if t else 70,820)
    q['horizontal_slope']=3.0
    if n=='n' and v in HORIZONTAL and t:
        q['initial_box']=tuple(MASTERS['n.shallow']['calibrated_box'])
        q['initial_variant']='shallow'
        q['horizontal_box']=(218,468,785,565)
        q['horizontal_slope']=0.0
    if n=='h' and t:
        x0,_,x1,y1=q['initial_box']
        q['initial_box']=(x0,540,x1,y1)
        hx0,_,hx1,_=q['horizontal_box']
        q['horizontal_box']=(hx0,370,hx1,455)
        if v not in HORIZONTAL: q['vertical_y']=(370,820)
        q['final']=limit_final_height(fp,285)
    return q


def draw_medial(d,l,v,layout):
    if v in VERTICAL:
        y0,y1=layout['vertical_y']
        vertical_vowel(d,v,layout['vertical_x'],y0,y1,
                       left=90 if v in {5,7} else 135,
                       long_anchor=layout['long_eo_anchor'],photo_eo=layout['photo_eo'],
                       left_floor=layout['eo_left_floor'])
    else:
        x0,y0,x1,y1=layout['horizontal_box']
        hv=v if v in HORIZONTAL else COMPOUND[v][0]
        horizontal_vowel(d,hv,x0,x1,y0,y1,slope=layout['horizontal_slope'])
        if v not in HORIZONTAL:
            vv=COMPOUND[v][1];vy0,vy1=layout['vertical_y']
            vertical_vowel(d,vv,layout['vertical_x'],vy0,vy1,
                           left=85 if vv==5 else 105,right=115)


def draw_final(d,profile,form='parallel'):
    if profile is None: return
    if profile['kind']=='oval': d.ellipse(*profile['ellipse'],STROKE)
    else: d.add(consonant(profile['name'],tuple(profile['box']),role='final',form=form))


def syllable_components(l,v,t,form='parallel'):
    q=layout_for(l,v,t)
    initial=consonant(q['initial_name'],tuple(q['initial_box']),form=form,variant=q['initial_variant'])
    medial=Drawing();draw_medial(medial,l,v,q)
    final=Drawing();draw_final(final,q['final'],form)
    return {'initial':initial,'medial':medial.path,'final':final.path}


def draw_syllable(l,v,t,pen,form='parallel'):
    d=Drawing()
    for path in syllable_components(l,v,t,form).values(): d.add(path)
    d.finish(pen)


def draw_jamo(kind,index,pen,form='parallel'):
    d=Drawing()
    if kind=='L': d.add(consonant(L_NAMES[index],(205,50,795,810),form=form))
    elif kind=='T': d.add(consonant(T_NAMES[index],(205,50,795,810),role='final',form=form))
    else:
        if index in VERTICAL: vertical_vowel(d,index,495 if index in {1,3,5,7} else 570,50,810,left=250,right=225)
        elif index in HORIZONTAL: horizontal_vowel(d,index,200,800,210,640)
        else:
            h,v=COMPOUND[index];horizontal_vowel(d,h,180,550,120,360)
            vertical_vowel(d,v,630 if v in {1,5} else 730,120,810,left=130,right=115)
    d.finish(pen)


def draw_ascii(ch,pen):
    if ch==' ':return 430
    d=Drawing();adv=600
    if ch in LATIN or ch in LOWER:
        ss=LATIN.get(ch,LOWER.get(ch)); box=(100,45,500,765)
        for p in ss:d.stroke(transform(p,box),STROKE)
    elif ch in '.:,;!·':
        ys={'.':[55],':':[110,470],',':[55],';':[110,470],'!':[65],'·':[365]}[ch]
        for y in ys:d.line(170,y,170,y+2,STROKE)
        if ch in ',;':d.line(170,ys[0],110,ys[0]-115,STROKE)
        if ch=='!':d.line(170,275,170,765,STROKE)
        adv=340
    elif ch=='?':
        d.stroke([('M',95,620),('C',100,845,510,840,505,630),('C',505,490,275,480,275,315)],STROKE);d.line(275,55,275,57,STROKE)
    elif ch in "'\"`‘’“”":
        xs=[150,330] if ch in '\"“”' else [190]
        for x in xs:d.line(x,755,x+(-50 if ch in '`‘“' else 0),600,STROKE)
        adv=480 if len(xs)>1 else 320
    elif ch in '-–—_=':
        adv=1000 if ch=='—' else (760 if ch=='–' else 600)
        for y in ([300,470] if ch=='=' else [25 if ch=='_' else 380]):d.line(80,y,adv-80,y,STROKE)
    elif ch in '+×':
        if ch=='+':d.line(100,380,500,380,STROKE);d.line(300,120,300,640,STROKE)
        else:d.line(100,180,500,600,STROKE);d.line(100,600,500,180,STROKE)
    elif ch in '/\\|':
        if ch=='|':d.line(300,-50,300,830,STROKE)
        elif ch=='/':d.line(80,-30,520,820,STROKE)
        else:d.line(80,820,520,-30,STROKE)
    elif ch in '()[]{}<>':
        flip=ch in ')]}>';cx=300;s=-1 if flip else 1
        if ch in '()':d.stroke([('M',cx+s*130,830),('C',cx-s*160,610,cx-s*160,170,cx+s*130,-50)],STROKE)
        elif ch in '[]':d.stroke([('M',cx+s*120,830),('L',cx-s*70,830),('L',cx-s*70,-50),('L',cx+s*120,-50)],STROKE)
        elif ch in '<>':d.stroke([('M',cx+s*180,670),('L',cx-s*170,380),('L',cx+s*180,90)],STROKE)
        else:d.stroke([('M',cx+s*140,830),('C',cx-s*80,830,cx-s*40,700,cx-s*40,580),('C',cx-s*40,450,cx-s*110,400,cx-s*140,390),('C',cx-s*110,380,cx-s*40,330,cx-s*40,210),('C',cx-s*40,80,cx-s*80,-50,cx+s*140,-50)],STROKE)
    elif ch=='#':
        for x in [190,390]:d.line(x-50,60,x+50,770,STROKE)
        for y in [270,540]:d.line(55,y,545,y,STROKE)
    elif ch=='%':
        d.line(70,40,530,760,STROKE);d.ellipse(150,650,90,100,STROKE);d.ellipse(450,150,90,100,STROKE)
    elif ch=='*':
        for a in [90,18,162]:
            a=math.radians(a);d.line(300-math.cos(a)*220,460-math.sin(a)*220,300+math.cos(a)*220,460+math.sin(a)*220,STROKE)
    elif ch=='^':d.stroke([('M',80,530),('L',300,780),('L',520,530)],STROKE)
    elif ch=='~':d.stroke([('M',70,355),('C',210,570,390,190,530,405)],STROKE)
    elif ch=='$':
        for p in LATIN['S']:d.stroke(transform(p,(100,100,500,715)),STROKE)
        d.line(300,20,300,800,STROKE)
    elif ch=='&':
        d.stroke([('M',540,35),('C',390,180,160,395,110,565),('C',30,820,460,865,430,600),('C',415,460,75,350,65,190),('C',40,-80,510,-50,535,390)],STROKE)
    elif ch=='@':
        d.ellipse(300,385,230,345,STROKE);d.ellipse(285,390,110,175,STROKE);d.stroke([('M',395,540),('L',395,230),('C',500,180,535,275,535,390)],STROKE)
    elif ch=='…':
        for x in [160,500,840]:d.line(x,55,x,57,STROKE)
        adv=1000
    elif ch in '←→↑↓':
        if ch in '←→':
            tip=100 if ch=='←' else 900;tail=900 if ch=='←' else 100;sgn=1 if ch=='←' else -1
            d.line(tail,380,tip,380,STROKE);d.stroke([('M',tip+sgn*240,620),('L',tip,380),('L',tip+sgn*240,140)],STROKE)
        else:
            tip=780 if ch=='↑' else 0;tail=0 if ch=='↑' else 780;sgn=-1 if ch=='↑' else 1
            d.line(500,tail,500,tip,STROKE);d.stroke([('M',260,tip+sgn*240),('L',500,tip),('L',740,tip+sgn*240)],STROKE)
        adv=1000
    elif ch=='₩':
        for p in LATIN['W']:d.stroke(transform(p,(70,50,930,765)),STROKE)
        d.line(90,440,910,440,STROKE);d.line(90,320,910,320,STROKE);adv=1000
    else:raise ValueError(f'Unsupported ASCII/extra character {ch!r}')
    d.finish(pen);return adv
