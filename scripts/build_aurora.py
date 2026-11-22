"""Build a GitHub-compatible animated SVG using only Python's standard library."""
from pathlib import Path
import calendar,datetime as dt,json,math,random,xml.etree.ElementTree as E

N='http://www.w3.org/2000/svg';E.register_namespace('',N)
def tag(s):return '{'+N+'}'+s
ROOT=Path(__file__).resolve().parents[1]

def curtain_field(u,t,motion):
    """An open, ordered contribution curtain; no returning or circular geometry."""
    T=math.tau*(t % motion['period'])/motion['period']
    # Compress and open sections without reversing their left-to-right order.
    x=75+1050*u+(10*math.sin(3*T)+18*math.sin(math.tau*2.1*u+.4+T))*math.sin(math.pi*u)
    y=292+30*math.sin(6*u-.4)+15*math.sin(11*u+.8)
    y+=19*math.sin(math.tau*2.2*u+.7-T)+9*math.sin(math.tau*3.8*u+2*T)
    ripple=sum(a*math.sin(math.tau*f*u+k*T+p) for a,f,k,p in
               zip(motion['amplitude'],motion['spatial'],motion['harmonics'],motion['phase']))
    y=300+54*math.tanh((y+ripple+16*math.sin(2*T+5*u)+18*math.sin(5*T-8*u)-300)/54)
    raw_height=90+68*math.sin(math.pi*u)**.65+12*math.sin(15*u)+8*math.sin(21*u-4*T)
    height=134+31*math.tanh((raw_height-134)/31)
    lean=16*math.sin(7*u)+8*math.cos(14*u)+6*math.sin(9*u-5*T)+5*math.sin(math.tau*2.4*u-2*T)
    brightness=.80+.12*math.sin(17*u-6*T)
    return x,y,height,lean,brightness

def make_fields(u,motion):
    steps=round(motion['period']/motion['step'])
    values=[curtain_field(u,j*motion['period']/steps,motion) for j in range(steps)]
    return values+[values[0]]

def projected_spacing(u,t,motion):
    delta=.0001;low=max(0,u-delta);high=min(1,u+delta)
    left=curtain_field(low,t,motion);right=curtain_field(high,t,motion)
    return ((right[0]+.45*right[3])-(left[0]+.45*left[3]))/(high-low)

def ray_path(x,base,height,lean,width,u):
    points=[]
    for side in [-1,1]:
        for j in (range(17) if side==-1 else range(16,-1,-1)):
            v=j/16
            center=x+lean*(1-v)**1.25+2.5*math.sin(v*4+u*19)*(1-v)
            half_width=width*(.90+.10*v)*(1+.06*math.sin(v*9+u*31))
            points.append((center+side*half_width,base-height+v*height))
    return 'M'+' L'.join(f'{xx:.2f},{yy:.2f}' for xx,yy in points)+' Z'

def animate_values(node,values,motion,kind=None,attribute=None):
    attrs={'attributeName':attribute or ('transform' if kind else 'opacity'),'values':values,
           'calcMode':'linear','dur':f'{motion["period"]}s','repeatCount':'indefinite'}
    if kind:attrs['type']=kind
    E.SubElement(node,tag('animateTransform' if kind else 'animate'),attrs)

def enrich_starfield(root):
    """Keep the original sky and add fixed, fine stars away from the header."""
    stars=root.find('.//'+tag('g')+'[@id="starfield"]')
    rng=random.Random('aurora-denser-sky')
    for i in range(len(stars),900):
        x=rng.uniform(28,1172);y=rng.uniform(108,378)
        radius=rng.uniform(.20,.44);alpha=rng.uniform(.30,.76)
        warm=rng.random()<.12
        g=E.SubElement(stars,tag('g'),{'data-star':str(i+1)})
        if i%5==0:
            E.SubElement(g,tag('circle'),{'cx':f'{x:.2f}','cy':f'{y:.2f}','r':f'{radius*6:.2f}','fill':'url(#stellar-warm)' if warm else 'url(#stellar-cool)','opacity':f'{alpha:.3f}'})
        E.SubElement(g,tag('circle'),{'cx':f'{x:.2f}','cy':f'{y:.2f}','r':f'{radius:.2f}','fill':'#FFF4DE' if warm else '#EDF5FF','opacity':f'{alpha:.3f}'})

def activity_strip(root,data):
    old=root.find('.//'+tag('g')+'[@id="daily-activity"]')
    if old is not None:root.remove(old)
    g=E.SubElement(root,tag('g'),{'id':'daily-activity','data-scope':'current-month'})
    style={'fill':'#92ABB8','font-size':'9','font-family':'monospace','letter-spacing':'.6'}
    snapshot=dt.date.fromisoformat(data['as_of'])
    start=snapshot.replace(day=1);days=calendar.monthrange(start.year,start.month)[1]
    left=50
    E.SubElement(g,tag('text'),dict(style,x=str(left),y='410')).text=start.strftime('%b %Y').upper()+' · DAILY ACTIVITY'
    counts=data.get('daily_counts',{});levels=data.get('daily_levels',{})
    colors=['#182631','#31594E','#589D7F','#8BD4AA','#C5E8C8']
    width=300/days
    for j in range(days):
        day=start+dt.timedelta(days=j);key=day.isoformat()
        level=int(levels.get(key,0))
        if day>snapshot:title=f'{key} · after the data snapshot'
        elif key in counts:title=f'{key} · {int(counts[key])} contributions'
        else:title=f'{key} · intensity level {level}/4 (screenshot; exact count unavailable)'
        rect=E.SubElement(g,tag('rect'),{'x':f'{left+j*width:.3f}','y':'417','width':f'{width*.74:.3f}','height':'6','rx':'.4','fill':colors[max(0,min(4,level))],'data-date':key,'opacity':'.25' if day>snapshot else '1'})
        E.SubElement(rect,tag('title')).text=title
        if day.day==1 or day.day%5==0 or day.day==days:
            E.SubElement(g,tag('text'),dict(style,x=f'{left+(j+.37)*width:.2f}',y='437',**{'letter-spacing':'0','text-anchor':'middle'})).text=str(day.day)
    return g

def build(data,template=None,motion=None,config=None):
    template=template or ROOT/'data/style-template.svg'
    motion=motion or json.loads((ROOT/'data/motion.json').read_text())
    config=config or json.loads((ROOT/'data/config.json').read_text())
    root=E.parse(template).getroot();defs=root.find(tag('defs'))
    enrich_starfield(root)
    total=int(data['total'])
    if total<0 or sum(int(x) for x in data['annual_totals'].values())!=total:raise ValueError('Contribution totals are inconsistent')
    main=root.find('.//'+tag('g')+'[@id="aurora-main"]')
    still=root.find('.//'+tag('g')+'[@id="aurora-static"]')
    for g in [main,still]:
        for child in list(g):g.remove(child)
    main.set('data-contributions',str(total))
    rng=random.Random('cumulative-natural-curtain')
    for i in range(total):
        u=(i+.5+rng.uniform(-.08,.08))/total
        field=make_fields(u,motion);x,base,height,lean,brightness=field[0]
        spreads=[projected_spacing(u,j*motion['period']/(len(field)-1),motion) for j in range(len(field))]
        width=spreads[0]/max(total,180)*rng.uniform(.56,.64)
        micro=.84+.07*math.sin(31*u+.5)+rng.uniform(-.025,.025)
        height_factor=rng.uniform(.98,1.02)
        d=ray_path(x,base,height*height_factor,lean,width,u)
        palette=1 if math.sin(14*u+.6)>.65 else (2 if math.sin(23*u)>.45 else 0)
        for group,animate in [(main,True),(still,False)]:
            outer=E.SubElement(group,tag('g'),{'data-fold':str(i+1),'transform':'translate(0 0)','opacity':f'{brightness*micro:.4f}'})
            anchor=E.SubElement(outer,tag('g'),{'transform':f'translate({x:.3f} {base:.3f})'})
            skew=E.SubElement(anchor,tag('g'),{'transform':'skewX(0)'})
            scale=E.SubElement(skew,tag('g'),{'transform':'scale(1 1)'})
            restore=E.SubElement(scale,tag('g'),{'transform':f'translate({-x:.3f} {-base:.3f})'})
            # A faint 0.35px outer shoulder joins adjacent folds without blurring
            # their filled cores. It uses the same vertical color/fade as the fill.
            E.SubElement(restore,tag('path'),{'d':d,'fill':f'url(#curtain{palette})','stroke':f'url(#curtain{palette})','stroke-width':'.7','stroke-opacity':'.28','stroke-linejoin':'round','paint-order':'stroke fill'})
            if animate:
                animate_values(outer,';'.join(f'{xx-x:.3f} {yy-base:.3f}' for xx,yy,h,l,b in field),motion,'translate')
                animate_values(skew,';'.join(f'{math.degrees(math.atan((spread/spreads[0]*lean-l)/(h*height_factor))):.3f}' for (xx,yy,h,l,b),spread in zip(field,spreads)),motion,'skewX')
                animate_values(scale,';'.join(f'{spread/spreads[0]:.5f} {h/height:.5f}' for (xx,yy,h,l,b),spread in zip(field,spreads)),motion,'scale')
                animate_values(outer,';'.join(f'{b*micro:.4f}' for xx,yy,h,l,b in field),motion)
    for text in root.findall(tag('text')):
        if text.text and text.text.endswith(' CONTRIBUTIONS'):text.text=f'{total} CONTRIBUTIONS'
    activity_strip(root,data)
    # The halo reuses only contribution folds; an empty contribution set stays empty.
    halo_filter=E.SubElement(defs,tag('filter'),{'id':'aurora-halo','filterUnits':'userSpaceOnUse','x':'25','y':'70','width':'1150','height':'310','color-interpolation-filters':'sRGB'})
    E.SubElement(halo_filter,tag('feGaussianBlur'),{'stdDeviation':'5 2'})
    for source,css in [('aurora-main','moving'),('aurora-static','static')]:
        halo=E.Element(tag('g'),{'id':source+'-halo','class':css,'opacity':str(config.get('smoke_opacity',.15)),'filter':'url(#aurora-halo)','aria-hidden':'true'})
        E.SubElement(halo,tag('use'),{'href':'#'+source})
        root.insert(list(root).index(main),halo)
    desc=root.find(tag('desc'))
    desc.text=f'{total} cumulative contributions, represented by exactly {total} visible main folds. No independent curtain is drawn. The compact current-month strip shows daily activity. '+('Exact daily counts from GitHub.' if data.get('source')=='github-graphql' else 'Preview daily intensities are transcribed from screenshots; exact daily counts are unavailable.')+f' Stars, color and motion are decorative. The {motion["period"]}-second animation has a complete reduced-motion still.'
    return root

def write_outputs(data,output=None):
    output=Path(output or ROOT)
    root=build(data);(output/'assets').mkdir(parents=True,exist_ok=True)
    svg=E.tostring(root,encoding='unicode')
    (output/'assets/aurora.svg').write_text(svg)
    # Inline SVG lets the calendar cells expose their exact date/count tooltips.
    (output/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aurora / Ege John</title><style>html{color-scheme:dark}body{margin:0;background:#070311}main{max-width:1200px;margin:28px auto}svg{display:block;width:100%;height:auto}</style><main>'+svg+'</main></html>')
    return root

if __name__=='__main__':
    data=json.loads((ROOT/'data/contributions.json').read_text());root=write_outputs(data)
    print(f'Built {data["total"]} contribution folds; source: {data["source"]}')
