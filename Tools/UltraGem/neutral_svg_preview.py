"""Pure SVG editor placeholder renderer for all five factory profiles (LFX-M08-010).

All geometry is generated from the pre-existing neutral_preview_recipes. No
external media, textures, scripts, URLs, licensed art or Engine game state.
SVG viewBox scales without raster upscaling; Unity SVG-import proof remains open.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from neutral_preview_recipes import geometric_preview_recipe

_NS='http://www.w3.org/2000/svg'
ET.register_namespace('',_NS)

def _shape(board: ET.Element,kind: str,x: int,y: int,color: str) -> None:
    base={'fill':color,'stroke':'#FFFFFF','stroke-width':'3', 'data-shape':kind}
    if kind=='circle':
        ET.SubElement(board,f'{{{_NS}}}circle',{**base,'cx':str(x),'cy':str(y),'r':'25'})
    elif kind=='oval':
        ET.SubElement(board,f'{{{_NS}}}ellipse',{**base,'cx':str(x),'cy':str(y),'rx':'29','ry':'19'})
    elif kind in ('square','rounded_square'):
        ET.SubElement(board,f'{{{_NS}}}rect',{**base,'x':str(x-25),'y':str(y-25),
              'width':'50','height':'50','rx':'10' if kind=='rounded_square' else '0'})
    else:
        n={'triangle':3,'diamond':4,'hexagon':6,'octagon':8,'star':10}[kind]
        points=[]
        for i in range(n):
            angle=math.pi*i*2/n-math.pi/2
            radius=29 if kind!='star' or i%2==0 else 13
            points.append(f'{x+radius*math.cos(angle):.2f},{y+radius*math.sin(angle):.2f}')
        ET.SubElement(board,f'{{{_NS}}}polygon',{**base,'points':' '.join(points)})


def render_preview_svg(profile_id: str, *, reduced_motion: bool = True) -> str:
    recipe=geometric_preview_recipe(profile_id,reduced_motion=reduced_motion)
    root=ET.Element(f'{{{_NS}}}svg',{
        'viewBox':'0 0 360 640','width':'100%','height':'100%',
        'preserveAspectRatio':'xMidYMid meet','role':'img',
        'aria-label':f'{profile_id} neutral editor preview',
        'data-result-status':'SYNTHETIC_PREVIEW_ONLY',
        'data-engine-status':'BLOCKED_ENG_M24',
    })
    ET.SubElement(root,f'{{{_NS}}}title').text=f'{profile_id} neutral SVG concept-free preview'
    ET.SubElement(root,f'{{{_NS}}}rect',{
        'width':'360','height':'640','fill':recipe['backgroundHex']})
    ET.SubElement(root,f'{{{_NS}}}rect',{
        'x':'20','y':'155','width':'320','height':'320','rx':'24','fill':recipe['accentHex']})
    board=ET.SubElement(root,f'{{{_NS}}}g',{'data-layer':'static-board'})
    for r in range(3):
        for c in range(3):
            p=recipe['pieceShapes'][(r+c)%3]
            _shape(board,p['kind'],95+85*c,222+85*r,p['colorHex'])
    # Shape geometry alone conveys piece ID if viewed in monochrome.
    return ET.tostring(root,encoding='unicode',short_empty_elements=True)+'\n'


def verify_scaling_contract(svg: str, *, display_width: int) -> dict:
    if type(display_width) is not int or not 240<=display_width<=2160:
        raise ValueError('preview display width out of bounded mobile/desktop range')
    root=ET.fromstring(svg)
    if root.tag != f'{{{_NS}}}svg' or root.attrib.get('viewBox')!='0 0 360 640':
        raise ValueError('not a supported responsive SVG preview')
    if any(n.tag.split('}')[-1] in {'script','image','foreignObject','use'} for n in root.iter()):
        raise ValueError('external/raster/script content is forbidden')
    if root.attrib.get('data-engine-status')!='BLOCKED_ENG_M24':
        raise ValueError('the SVG Engine limitation was removed')
    shapes=[n.attrib.get('data-shape') for n in root.iter() if 'data-shape' in n.attrib]
    if len(shapes)!=9 or len(set(shapes))!=3:
        raise ValueError('three distinct silhouettes must remain distinguishable')
    return {'displayWidth':display_width,'viewBox':'0 0 360 640',
            'scaleFactor':round(display_width/360,6),
            'pieceKinds':sorted(set(shapes)),
            'rasterResamplingRequired':False,
            'unitySvgImporterValidated':False,
            'engineStatus':'BLOCKED_ENG_M24'}
