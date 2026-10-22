#!/usr/bin/env python3
"""Render a pptx (simple shapes) to a single HTML page for visual QA.
Usage: python3 render.py <unpacked_dir> <out.html> [slide_numbers]
"""
import sys, os, re, base64, html, json
from xml.etree import ElementTree as ET

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
EMU = 914400.0
PX_PER_IN = 96.0
EMU2PX = PX_PER_IN / EMU
PT2PX = PX_PER_IN / 72.0

FONT_MAP = {
    'Segoe UI': '"Helvetica Neue", Arial, sans-serif',
    'Microsoft YaHei': '"Microsoft YaHei", "PingFang SC", sans-serif',
    'Consolas': 'Menlo, monospace',
}

def q(tag):
    p, l = tag.split(':')
    return '{%s}%s' % (NS[p], l)

def f(e, tag):
    return e.find(q(tag)) if e is not None else None

def fa(e, tag):
    return e.findall(q(tag)) if e is not None else []

def px(v):
    return round(float(v) * EMU2PX, 2)

def color_of(fill_el):
    """Return (hex, alpha) from a fill element or None."""
    if fill_el is None:
        return None
    if f(fill_el, 'a:noFill') is not None:
        return 'none'
    sf = f(fill_el, 'a:solidFill')
    if sf is not None:
        c = sf[0]
        val = c.get('val')
        if val is None and c.tag.endswith('sysClr'):
            val = c.get('lastClr')
        if val is None:
            return None
        a = f(c, 'a:alpha')
        alpha = int(a.get('val')) / 100000.0 if a is not None else 1.0
        return '#' + val, alpha
    gf = f(fill_el, 'a:gradFill')
    if gf is not None:
        stops = []
        for gs in fa(f(gf, 'a:gsLst'), 'a:gs'):
            pos = int(gs.get('pos')) / 100000.0
            c = gs[0]
            val = c.get('val') or c.get('lastClr')
            a = f(c, 'a:alpha')
            alpha = int(a.get('val')) / 100000.0 if a is not None else 1.0
            stops.append((pos, '#' + val, alpha))
        ang = f(gf, 'a:lin')
        angdeg = int(ang.get('ang')) / 60000.0 + 90 if ang is not None else 90
        css = ', '.join('%s%s %d%%' % (c, ('%02x' % int(a * 255)) if a < 1 else '', p * 100) for p, c, a in stops)
        return 'linear-gradient(%ddeg, %s)' % (angdeg, css)
    return None

def fill_css(spPr):
    """CSS background value (string) or None."""
    if spPr is None:
        return None
    c = color_of(spPr)
    if c is None:
        return None
    if c == 'none':
        return 'none'
    if isinstance(c, tuple):
        hexv, alpha = c
        if alpha < 1:
            r, g, b = int(hexv[1:3], 16), int(hexv[3:5], 16), int(hexv[5:7], 16)
            return 'rgba(%d,%d,%d,%.3f)' % (r, g, b, alpha)
        return hexv
    return c


def text_runs_html(p):
    out = []
    for child in p:
        if child.tag == q('a:r'):
            rPr = f(child, 'a:rPr')
            t = f(child, 'a:t')
            txt = html.escape(t.text or '') if t is not None else ''
            style = run_style(rPr)
            if not txt:
                continue
            if txt.strip() == '':
                txt = '&nbsp;'
            out.append('<span style="%s">%s</span>' % (style, txt))
        elif child.tag == q('a:br'):
            out.append('<br/>')
        elif child.tag == q('a:fld'):
            t = f(child, 'a:t')
            if t is not None and t.text:
                out.append('<span style="%s">%s</span>' % (run_style(f(child, 'a:rPr')), html.escape(t.text)))
    return ''.join(out)


def run_style(rPr):
    if rPr is None:
        return ''
    st = []
    sz = rPr.get('sz')
    if sz:
        st.append('font-size:%.1fpx' % (int(sz) / 100.0 * PT2PX))
    if rPr.get('b') == '1':
        st.append('font-weight:700')
    if rPr.get('i') == '1':
        st.append('font-style:italic')
    if rPr.get('u') and rPr.get('u') != 'none':
        st.append('text-decoration:underline')
    if rPr.get('spc'):
        st.append('letter-spacing:%.2fpx' % (int(rPr.get('spc')) / 100.0 * PT2PX))
    sf = rPr.find(q('a:solidFill'))
    if sf is not None and len(sf):
        node = sf[0]
        val = node.get('val') or node.get('lastClr')
        if val:
            alpha = 1.0
            a = f(node, 'a:alpha')
            if a is not None:
                alpha = int(a.get('val')) / 100000.0
            am = f(node, 'a:alphaMod')
            if am is not None:
                alpha = int(am.get('val')) / 100000.0
            st.append('color:#%s' % val)
            if alpha < 1:
                st.append('opacity:%.2f' % alpha)
    lat = f(rPr, 'a:latin')
    ea = f(rPr, 'a:ea')
    fams = []
    for e in (ea, lat):
        if e is not None and e.get('typeface'):
            fams.append(FONT_MAP.get(e.get('typeface'), '"%s"' % e.get('typeface')))
    if fams:
        st.append('font-family:%s' % (', '.join(fams) + ', sans-serif'))
    return ';'.join(st)


def body_html(txBody):
    bodyPr = f(txBody, 'a:bodyPr')
    lIns = int(bodyPr.get('lIns', 91440)) / EMU * PX_PER_IN if bodyPr is not None else 9.6
    rIns = int(bodyPr.get('rIns', 91440)) / EMU * PX_PER_IN if bodyPr is not None else 9.6
    tIns = int(bodyPr.get('tIns', 45720)) / EMU * PX_PER_IN if bodyPr is not None else 4.8
    bIns = int(bodyPr.get('bIns', 45720)) / EMU * PX_PER_IN if bodyPr is not None else 4.8
    anchor = bodyPr.get('anchor', 't') if bodyPr is not None else 't'
    wrap = bodyPr.get('wrap', 'square') if bodyPr is not None else 'square'
    jc = {'t': 'flex-start', 'ctr': 'center', 'b': 'flex-end', 'dist': 'space-between'}.get(anchor, 'flex-start')
    style = ('display:flex;flex-direction:column;justify-content:%s;'
             'padding:%.2fpx %.2fpx %.2fpx %.2fpx;' % (jc, tIns, rIns, bIns, lIns))
    if wrap == 'none':
        style += 'white-space:nowrap;'
    parts = []
    for p in fa(txBody, 'a:p'):
        pPr = f(p, 'a:pPr')
        algn = pPr.get('algn', 'l') if pPr is not None else 'l'
        align = {'l': 'left', 'ctr': 'center', 'r': 'right', 'just': 'justify'}.get(algn, 'left')
        pst = ['margin:0', 'text-align:' + align]
        default_sz = None
        if pPr is not None:
            marL = pPr.get('marL')
            if marL:
                pst.append('margin-left:%.2fpx' % (int(marL) / EMU * PX_PER_IN))
            indent = pPr.get('indent')
            if indent:
                pst.append('text-indent:%.2fpx' % (int(indent) / EMU * PX_PER_IN))
            ln = f(pPr, 'a:lnSpc')
            if ln is not None:
                pct = f(ln, 'a:spcPct')
                if pct is not None:
                    pst.append('line-height:%.3f' % (int(pct.get('val')) / 100000.0 * 1.2))
                pts = f(ln, 'a:spcPts')
                if pts is not None:
                    pst.append('line-height:%.1fpx' % (int(pts.get('val')) / 100.0 * PT2PX))
            for nm, prop in (('a:spcBef', 'margin-top'), ('a:spcAft', 'margin-bottom')):
                sp = f(pPr, nm)
                if sp is not None:
                    pts = f(sp, 'a:spcPts')
                    if pts is not None:
                        pst.append('%s:%.1fpx' % (prop, int(pts.get('val')) / 100.0 * PT2PX))
            d = f(pPr, 'a:defRPr')
            if d is not None and d.get('sz'):
                default_sz = 'font-size:%.1fpx' % (int(d.get('sz')) / 100.0 * PT2PX)
        content = text_runs_html(p)
        if not content.strip():
            content = '&nbsp;'
        bu = None
        if pPr is not None:
            bc = f(pPr, 'a:buChar')
            bn = f(pPr, 'a:buNone')
            if bc is not None:
                bu = bc.get('char', '•')
        if bu:
            content = '<span style="%s">%s </span>' % (default_sz or '', html.escape(bu)) + content
        pst.append('white-space:pre-wrap')
        parts.append('<p style="%s">%s</p>' % (';'.join(pst), content))
    if not parts:
        parts.append('<p style="margin:0">&nbsp;</p>')
    return style, ''.join(parts)


def custgeom_svg(spPr, wpx, hpx, fill, line):
    cg = f(spPr, 'a:custGeom')
    if cg is None:
        return None
    pl = f(cg, 'a:pathLst')
    paths = []
    for path in fa(pl, 'a:path'):
        pw = float(path.get('w') or 1)
        ph = float(path.get('h') or 1)
        d = []
        for cmd in path:
            tag = cmd.tag.split('}')[1]
            pts = []
            for pt in cmd:
                tagp = pt.tag.split('}')[1]
                x = float(pt.get('x', 0)) / pw * wpx
                y = float(pt.get('y', 0)) / ph * hpx
                pts.append((x, y))
            if tag == 'moveTo':
                d.append('M %.2f %.2f' % pts[0])
            elif tag == 'lnTo':
                d.append('L %.2f %.2f' % pts[0])
            elif tag == 'cubicBezTo':
                d.append('C ' + ' '.join('%.2f %.2f' % p for p in pts))
            elif tag == 'quadBezTo':
                d.append('Q ' + ' '.join('%.2f %.2f' % p for p in pts))
            elif tag == 'close':
                d.append('Z')
        paths.append((' '.join(d), path.get('fill', 'norm')))
    out = []
    for d, fillmode in paths:
        attrs = 'd="%s"' % d
        if fillmode == 'none':
            attrs += ' fill="none"'
        else:
            attrs += ' fill="%s"' % (fill or 'none')
        if line:
            attrs += ' stroke="%s" stroke-width="%s"' % line
        out.append('<path %s/>' % attrs)
    return ('<svg width="%.2f" height="%.2f" viewBox="0 0 %.2f %.2f" '
            'preserveAspectRatio="none" style="position:absolute;left:0;top:0;overflow:visible">%s</svg>'
            % (wpx, hpx, wpx, hpx, ''.join(out)))


def line_css(spPr):
    ln = f(spPr, 'a:ln')
    if ln is None:
        return None, None
    c = color_of(ln)
    w = int(ln.get('w', 12700)) / EMU * PX_PER_IN
    dash = f(ln, 'a:prstDash')
    return (c if c and c != 'none' else None), (w, dash.get('val') if dash is not None else None)


def render_shape(sp, ctx, depth=0):
    tag = sp.tag.split('}')[1]
    out = []
    if tag == 'grpSp':
        xfrm = f(sp, 'p:grpSpPr')
        x = f(xfrm, 'a:xfrm')
        off = f(x, 'a:off'); ext = f(x, 'a:ext')
        choff = f(x, 'a:chOff'); chext = f(x, 'a:chExt')
        sx = sy = 1.0
        ox = oy = 0.0
        if off is not None and ext is not None and chext is not None and choff is not None:
            ocx = int(ext.get('cx')); ocy = int(ext.get('cy'))
            ccx = int(chext.get('cx')) or 1; ccy = int(chext.get('cy')) or 1
            sx = ocx / ccx; sy = ocy / ccy
            ox = px(int(off.get('x')) - int(choff.get('x')) * sx)
            oy = px(int(off.get('y')) - int(choff.get('y')) * sy)
        inner = []
        for child in sp:
            if child.tag.split('}')[1] in ('sp', 'pic', 'grpSp', 'graphicFrame', 'cxnSp'):
                inner.extend(render_shape(child, ctx, depth + 1))
        # children positions are absolute in child space; scaling the wrapper maps them correctly
        out.append('<div style="position:absolute;left:0;top:0;width:0;height:0;'
                   'transform-origin:0 0;transform:translate(%.2fpx,%.2fpx) scale(%.4f,%.4f)">%s</div>'
                   % (ox, oy, sx, sy, ''.join(inner)))
        return out

    spPr = f(sp, 'p:spPr')
    xfrm = f(spPr, 'a:xfrm')
    if xfrm is None:
        return out
    off = f(xfrm, 'a:off'); ext = f(xfrm, 'a:ext')
    if off is None or ext is None:
        return out
    x = px(int(off.get('x'))); y = px(int(off.get('y')))
    w = px(int(ext.get('cx'))); h = px(int(ext.get('cy')))
    rot = int(xfrm.get('rot', 0)) / 60000.0
    flip = ('flipH' in xfrm.attrib, 'flipV' in xfrm.attrib)
    tr = ''
    if rot or any(flip):
        tr = 'transform:rotate(%.2fdeg)%s%s;' % (
            rot, ' scaleX(-1)' if flip[0] else '', ' scaleY(-1)' if flip[1] else '')
        tr = ('transform-origin:%.1fpx %.1fpx;' % (w / 2, h / 2)) + tr

    fill = fill_css(spPr)
    lc, lw = line_css(spPr)
    style = ['position:absolute', 'left:%.2fpx' % x, 'top:%.2fpx' % y,
             'width:%.2fpx' % w, 'height:%.2fpx' % h, 'box-sizing:border-box']
    geom = f(spPr, 'a:prstGeom')
    prst = geom.get('prst') if geom is not None else None
    cust = f(spPr, 'a:custGeom') is not None

    inner = ''
    if tag == 'pic':
        blip = sp.find('.//' + q('a:blip'))
        src = ''
        if blip is not None:
            rid = blip.get('{%s}embed' % NS['r'])
            src = ctx['rels'].get(rid, '')
        inner = ('<img src="%s" style="width:100%%;height:100%%;object-fit:cover;display:block">' % src)
    elif prst == 'ellipse':
        style.append('border-radius:50%')
        if fill and fill != 'none':
            style.append('background:' + fill)
        if lc:
            style.append('border:%.2fpx solid %s' % (lw[0], lc[0]))
    elif cust:
        svg = custgeom_svg(spPr, w, h, fill if fill and fill != 'none' else None,
                           (lc[0], '%.2f' % lw[0]) if lc else None)
        inner = svg or ''
    else:
        if fill and fill != 'none':
            style.append('background:' + fill)
        if lc:
            style.append('border:%.2fpx solid %s' % (lw[0], lc[0]))
        if prst == 'line':
            # a line shape: draw as a 1px div
            style = ['position:absolute', 'left:%.2fpx' % x, 'top:%.2fpx' % y,
                     'width:%.2fpx' % max(w, 0.5), 'height:%.2fpx' % max(h, 0.5),
                     'background:%s' % (lc[0] if lc else '#000')]
            tr = ''

    # text
    txBody = f(sp, 'p:txBody')
    if txBody is not None:
        tstyle, thtml = body_html(txBody)
        inner = '<div style="position:absolute;left:0;top:0;width:100%%;height:100%%;%s">%s</div>' % (tstyle, thtml)
        if prst == 'ellipse':
            style.append('overflow:hidden')

    style.append(tr)
    out.append('<div style="%s">%s</div>' % (';'.join(s for s in style if s), inner))
    return out


def render_slide(slide_xml, rels_map, idx):
    root = ET.fromstring(slide_xml)
    cSld = f(root, 'p:cSld')
    bg = ''
    bgPr = f(cSld, 'p:bg')
    if bgPr is not None:
        c = fill_css(f(bgPr, 'p:bgPr'))
        if c and c != 'none':
            bg = c
    spTree = f(cSld, 'p:spTree')
    ctx = {'rels': rels_map}
    body = []
    for child in spTree:
        if child.tag.split('}')[1] in ('sp', 'pic', 'grpSp', 'cxnSp', 'graphicFrame'):
            body.extend(render_shape(child, ctx))
    return ('<div class="slide" id="s%d" style="position:relative;width:1280px;height:720px;%s">'
            '<div class="lbl">%d</div>%s</div>'
            % (idx, ('background:' + bg + ';') if bg else 'background:#fff;', idx, ''.join(body)))


def main():
    src, out = sys.argv[1], sys.argv[2]
    want = sys.argv[3] if len(sys.argv) > 3 else None
    slides = []
    n = 1
    while os.path.exists(os.path.join(src, 'ppt/slides/slide%d.xml' % n)):
        n += 1
    n -= 1
    for i in range(1, n + 1):
        if want and str(i) not in want.split(','):
            continue
        xml = open(os.path.join(src, 'ppt/slides/slide%d.xml' % i), 'rb').read()
        rels = {}
        rp = os.path.join(src, 'ppt/slides/_rels/slide%d.xml.rels' % i)
        if os.path.exists(rp):
            rr = ET.fromstring(open(rp, 'rb').read())
            for rel in rr:
                tgt = (rel.get('Target') or '').replace('\\', '/')
                full = os.path.normpath(os.path.join(src, 'ppt/slides', tgt))
                if os.path.exists(full):
                    mime = 'image/png' if full.lower().endswith('.png') else 'image/jpeg'
                    data = base64.b64encode(open(full, 'rb').read()).decode()
                    rels[rel.get('Id')] = 'data:%s;base64,%s' % (mime, data)
        slides.append(render_slide(xml, rels, i))
    doc = """<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;background:#d8dde3;font-family:"Microsoft YaHei","PingFang SC",sans-serif;}
    .slide{margin:14px auto;box-shadow:0 3px 14px rgba(0,0,0,.25);overflow:hidden;}
    .lbl{position:absolute;left:-46px;top:4px;font:12px/1 Menlo;color:#666}
    </style></head><body>%s</body></html>""" % ''.join(slides)
    open(out, 'w', encoding='utf-8').write(doc)
    print('wrote', out, 'slides', len(slides))
    # single-slide pages for crisp screenshots
    split = os.environ.get('SPLIT_DIR')
    if split:
        os.makedirs(split, exist_ok=True)
        for s in slides:
            m = re.search(r'id="s(\d+)"', s)
            page = ('<!doctype html><html><head><meta charset="utf-8"><style>'
                    'body{margin:0;font-family:"Microsoft YaHei","PingFang SC",sans-serif}'
                    '.lbl{display:none}</style></head><body>%s</body></html>') % s
            open(os.path.join(split, 'slide%02d.html' % int(m.group(1))), 'w', encoding='utf-8').write(page)
        print('split pages ->', split)

main()
