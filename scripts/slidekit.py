#!/usr/bin/env python3
"""Minimal OOXML slide builder: rects, lines, text with runs."""
import copy
from xml.etree import ElementTree as ET

A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'a': A, 'p': P, 'r': R}
for k, v in NS.items():
    ET.register_namespace(k, v)

EMU = 914400.0
FONT = 'Microsoft YaHei'

INK = '1E3A2F'
INK_SOFT = '2C4A3C'
CLAY = 'C2703F'
SAGE = '5C8170'
SAGE_L = '8FAE9A'
TINT = 'F1ECE1'
PAPER = 'FDFBF7'
HAIR = 'E2DACB'
GREY = '6B7269'
GREY_L = '8A9189'
WHITE = 'FFFFFF'
CREAM = 'EFE8DA'


def q(tag):
    p, l = tag.split(':')
    return '{%s}%s' % (NS[p], l)


def E(v):
    return int(round(v * EMU))


def _rpr(run, size, color, bold=False, spc=None, italic=False, alpha=None):
    rPr = ET.Element(q('a:rPr'))
    rPr.set('lang', 'zh-CN')
    rPr.set('altLang', 'en-US')
    rPr.set('sz', str(int(size * 100)))
    if bold:
        rPr.set('b', '1')
    if italic:
        rPr.set('i', '1')
    if spc:
        rPr.set('spc', str(int(spc)))
    sf = ET.SubElement(rPr, q('a:solidFill'))
    c = ET.SubElement(sf, q('a:srgbClr'))
    c.set('val', color)
    if alpha is not None:
        a = ET.SubElement(c, q('a:alpha'))
        a.set('val', str(int(alpha)))
    for tag in ('a:latin', 'a:ea', 'a:cs'):
        ET.SubElement(rPr, q(tag)).set('typeface', FONT)
    return rPr


def _para(spec):
    """spec: dict(text|runs, size, color, bold, align, line, before, after, bullet, spc)"""
    p = ET.Element(q('a:p'))
    pPr = ET.SubElement(p, q('a:pPr'))
    pPr.set('algn', spec.get('align', 'l'))
    if spec.get('bullet'):
        marL = E(spec.get('indent', 0.16))
        pPr.set('marL', str(int(marL)))
        pPr.set('indent', str(-int(marL)))
        buClr = ET.SubElement(pPr, q('a:buClr'))
        c = ET.SubElement(buClr, q('a:srgbClr'))
        c.set('val', spec.get('bullet_color', CLAY))
        buSz = ET.SubElement(pPr, q('a:buSzPct'))
        buSz.set('val', '70000')
        buFont = ET.SubElement(pPr, q('a:buFont'))
        buFont.set('typeface', 'Arial')
        bu = ET.SubElement(pPr, q('a:buChar'))
        bu.set('char', spec.get('bullet_char', '▪'))
    elif spec.get('no_bullet', True):
        ET.SubElement(pPr, q('a:buNone'))
    if spec.get('line'):
        ln = ET.SubElement(pPr, q('a:lnSpc'))
        pct = ET.SubElement(ln, q('a:spcPct'))
        pct.set('val', str(int(spec['line'] / 1.2 * 100000)))
    for key, tag in (('before', 'a:spcBef'), ('after', 'a:spcAft')):
        if spec.get(key):
            sp = ET.SubElement(pPr, q(tag))
            pts = ET.SubElement(sp, q('a:spcPts'))
            pts.set('val', str(int(spec[key] * 100)))
    runs = spec.get('runs') or [(spec.get('text', ''), {})]
    for text, opt in runs:
        r = ET.SubElement(p, q('a:r'))
        r.append(_rpr(r, opt.get('size', spec.get('size', 12)),
                      opt.get('color', spec.get('color', INK)),
                      opt.get('bold', spec.get('bold', False)),
                      opt.get('spc', spec.get('spc')),
                      opt.get('italic', False),
                      opt.get('alpha')))
        t = ET.SubElement(r, q('a:t'))
        t.text = text
        if text != text.strip():
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    if not runs:
        ET.SubElement(p, q('a:endParaRPr')).set('sz', str(int(spec.get('size', 12) * 100)))
    return p


def _base_sp(idx, name):
    sp = ET.Element(q('p:sp'))
    nv = ET.SubElement(sp, q('p:nvSpPr'))
    cnv = ET.SubElement(nv, q('p:cNvPr'))
    cnv.set('id', str(idx))
    cnv.set('name', name)
    ET.SubElement(nv, q('p:cNvSpPr')).set('txBox', '1')
    ET.SubElement(nv, q('p:nvPr'))
    return sp


def shape(idx, name, x, y, w, h, fill=None, geom='rect', adj=None,
          line=None, line_w=0.75, alpha=None, paras=None, anchor='t',
          wrap='square', insets=(0, 0, 0, 0), rot=None):
    sp = _base_sp(idx, name)
    spPr = ET.SubElement(sp, q('p:spPr'))
    xfrm = ET.SubElement(spPr, q('a:xfrm'))
    if rot:
        xfrm.set('rot', str(int(rot * 60000)))
    off = ET.SubElement(xfrm, q('a:off'))
    off.set('x', str(E(x))); off.set('y', str(E(y)))
    ext = ET.SubElement(xfrm, q('a:ext'))
    ext.set('cx', str(E(w))); ext.set('cy', str(E(h)))
    g = ET.SubElement(spPr, q('a:prstGeom'))
    g.set('prst', geom)
    av = ET.SubElement(g, q('a:avLst'))
    if adj is not None:
        gd = ET.SubElement(av, q('a:gd'))
        gd.set('name', 'adj')
        gd.set('fmla', 'val %d' % int(adj * 100000))
    if fill:
        sf = ET.SubElement(spPr, q('a:solidFill'))
        c = ET.SubElement(sf, q('a:srgbClr'))
        c.set('val', fill)
        if alpha is not None:
            a = ET.SubElement(c, q('a:alpha'))
            a.set('val', str(int(alpha)))
    else:
        ET.SubElement(spPr, q('a:noFill'))
    ln = ET.SubElement(spPr, q('a:ln'))
    ln.set('w', str(int(line_w * 12700)))
    if line:
        sf = ET.SubElement(ln, q('a:solidFill'))
        c = ET.SubElement(sf, q('a:srgbClr'))
        c.set('val', line)
    else:
        ET.SubElement(ln, q('a:noFill'))
    if paras is not None:
        tb = ET.SubElement(sp, q('p:txBody'))
        bp = ET.SubElement(tb, q('a:bodyPr'))
        bp.set('wrap', wrap)
        bp.set('lIns', str(E(insets[0]))); bp.set('tIns', str(E(insets[1])))
        bp.set('rIns', str(E(insets[2]))); bp.set('bIns', str(E(insets[3])))
        bp.set('anchor', anchor)
        bp.set('anchorCtr', '0')
        ET.SubElement(bp, q('a:noAutofit'))
        ET.SubElement(tb, q('a:lstStyle'))
        for spec in paras:
            tb.append(_para(spec))
    return sp


def text(idx, name, x, y, w, h, paras, anchor='t', insets=(0, 0, 0, 0), wrap='square'):
    return shape(idx, name, x, y, w, h, fill=None, paras=paras, anchor=anchor,
                 insets=insets, wrap=wrap)


def hline(idx, name, x, y, w, color=HAIR, weight=0.75):
    return shape(idx, name, x, y, w, 0.01, fill=color, line=None)


def vline(idx, name, x, y, h, color=HAIR, weight=0.75):
    return shape(idx, name, x, y, 0.01, h, fill=color, line=None)


def arrow(idx, name, x, y, w, color, weight=1.0):
    """horizontal connector with arrow head"""
    sp = _base_sp(idx, name)
    spPr = ET.SubElement(sp, q('p:spPr'))
    xfrm = ET.SubElement(spPr, q('a:xfrm'))
    off = ET.SubElement(xfrm, q('a:off')); off.set('x', str(E(x))); off.set('y', str(E(y)))
    ext = ET.SubElement(xfrm, q('a:ext')); ext.set('cx', str(E(w))); ext.set('cy', '0')
    g = ET.SubElement(spPr, q('a:prstGeom')); g.set('prst', 'line'); ET.SubElement(g, q('a:avLst'))
    ET.SubElement(spPr, q('a:noFill'))
    ln = ET.SubElement(spPr, q('a:ln'))
    ln.set('w', str(int(weight * 12700)))
    sf = ET.SubElement(ln, q('a:solidFill'))
    c = ET.SubElement(sf, q('a:srgbClr')); c.set('val', color)
    tail = ET.SubElement(ln, q('a:tailEnd'))
    tail.set('type', 'triangle'); tail.set('w', 'med'); tail.set('len', 'med')
    return sp


def build_slide(base_root, shapes, bg=PAPER):
    """Replace spTree children of base slide root with generated shapes."""
    root = copy.deepcopy(base_root)
    cSld = root.find(q('p:cSld'))
    old_bg = cSld.find(q('p:bg'))
    if old_bg is not None:
        cSld.remove(old_bg)
    bg_el = ET.Element(q('p:bg'))
    bgPr = ET.SubElement(bg_el, q('p:bgPr'))
    sf = ET.SubElement(bgPr, q('a:solidFill'))
    c = ET.SubElement(sf, q('a:srgbClr')); c.set('val', bg)
    ET.SubElement(bgPr, q('a:effectLst'))
    cSld.insert(0, bg_el)
    spTree = cSld.find(q('p:spTree'))
    keep = []
    for ch in list(spTree):
        tag = ch.tag.split('}')[1]
        if tag in ('nvGrpSpPr', 'grpSpPr'):
            keep.append(ch)
    for ch in list(spTree):
        spTree.remove(ch)
    for ch in keep:
        spTree.append(ch)
    for sh in shapes:
        spTree.append(sh)
    return root


def write(root, path):
    xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    open(path, 'wb').write(xml)


def picture(idx, name, rid, x, y, w, h, crop_l=0, crop_t=0, crop_r=0, crop_b=0):
    """<p:pic> with stretch fill; crop values are 1/1000 of a percent."""
    from xml.etree import ElementTree as ET
    pic = ET.Element(q('p:pic'))
    nv = ET.SubElement(pic, q('p:nvPicPr'))
    cnv = ET.SubElement(nv, q('p:cNvPr'))
    cnv.set('id', str(idx)); cnv.set('name', name)
    cnpic = ET.SubElement(nv, q('p:cNvPicPr'))
    ET.SubElement(cnpic, q('a:picLocks')).set('noChangeAspect', '1')
    ET.SubElement(nv, q('p:nvPr'))
    bf = ET.SubElement(pic, q('p:blipFill'))
    blip = ET.SubElement(bf, q('a:blip'))
    blip.set('{%s}embed' % NS['r'], rid)
    ET.SubElement(bf, q('a:stretch')).append(ET.Element(q('a:fillRect')))
    if any((crop_l, crop_t, crop_r, crop_b)):
        sr = ET.Element(q('a:srcRect'))
        for k, v in (('l', crop_l), ('t', crop_t), ('r', crop_r), ('b', crop_b)):
            if v:
                sr.set(k, str(int(v)))
        bf.insert(1, sr)
    spPr = ET.SubElement(pic, q('p:spPr'))
    xf = ET.SubElement(spPr, q('a:xfrm'))
    off = ET.SubElement(xf, q('a:off')); off.set('x', str(E(x))); off.set('y', str(E(y)))
    ext = ET.SubElement(xf, q('a:ext')); ext.set('cx', str(E(w))); ext.set('cy', str(E(h)))
    g = ET.SubElement(spPr, q('a:prstGeom')); g.set('prst', 'rect')
    ET.SubElement(g, q('a:avLst'))
    return pic
