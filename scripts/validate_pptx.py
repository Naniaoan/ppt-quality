#!/usr/bin/env python3
"""Structural validation for a .pptx that was edited/rebuilt by hand.

Usage: python3 validate_pptx.py deck.pptx [original.pptx]

Checks: zip integrity, every XML part parses, every relationship resolves,
PNG/JPEG content types exist for embedded images, shape ids unique per slide,
no shape outside the canvas, and (with --original) text that disappeared.
"""
import sys
import zipfile
import posixpath
from xml.etree import ElementTree as ET

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
E = 914400.0


def xml_texts(root):
    out = []
    for p in root.iter(A + 'p'):
        s = ''.join(t.text or '' for t in p.iter(A + 't')).strip()
        if s:
            out.append(s)
    return out


def check(path, original=None):
    problems = []
    z = zipfile.ZipFile(path)
    if z.testzip() is not None:
        problems.append('zip corrupt')
    for n in z.namelist():
        if n.endswith(('.xml', '.rels')):
            try:
                ET.fromstring(z.read(n))
            except Exception as e:
                problems.append('xml parse fail %s: %s' % (n, e))

    names = set(z.namelist())
    for n in z.namelist():
        if not n.endswith('.rels'):
            continue
        base = posixpath.dirname(posixpath.dirname(n))
        for rel in ET.fromstring(z.read(n)):
            if rel.get('TargetMode') == 'External':
                continue
            tgt = posixpath.normpath(posixpath.join(base, rel.get('Target')))
            if tgt not in names:
                problems.append('dangling rel %s -> %s' % (n, tgt))

    ct = z.read('[Content_Types].xml').decode('utf-8', 'ignore')
    for media, ext in [('media', 'png'), ('media', 'jpg'), ('media', 'jpeg')]:
        if any(n.startswith('ppt/%s/' % media) and n.lower().endswith('.' + ext) for n in names):
            if 'Extension="%s"' % ext not in ct:
                problems.append('missing Default for .%s in [Content_Types].xml' % ext)

    slides = sorted(n for n in names if n.startswith('ppt/slides/slide') and n.endswith('.xml'))
    for n in slides:
        root = ET.fromstring(z.read(n))
        ids = [e.get('id') for e in root.iter(P + 'cNvPr')]
        if len(ids) != len(set(ids)):
            problems.append('%s: duplicate shape ids' % n)
        tree = root.find(P + 'cSld').find(P + 'spTree')
        for sp in tree:
            xf = sp.find('.//' + A + 'xfrm')
            if xf is None:
                continue
            o, e = xf.find(A + 'off'), xf.find(A + 'ext')
            if o is None or e is None:
                continue
            x, y = int(o.get('x')) / E, int(o.get('y')) / E
            w, h = int(e.get('cx')) / E, int(e.get('cy')) / E
            if x < -0.02 or y < -0.02 or x + w > 13.36 or y + h > 7.52:
                problems.append('%s: shape outside canvas at (%.2f, %.2f)' % (n, x, y))

    if original:
        oz = zipfile.ZipFile(original)
        for n in slides:
            if n not in oz.namelist():
                continue
            old = xml_texts(ET.fromstring(oz.read(n)))
            new = ''.join(''.join(xml_texts(ET.fromstring(z.read(n)))))
            gone = [t for t in old if len(t) >= 8 and t not in new]
            if gone:
                print('  %s lost %d line(s): %s' % (n.split('/')[-1], len(gone), gone[:3]))
    return problems


if __name__ == '__main__':
    p = sys.argv[1]
    orig = sys.argv[2] if len(sys.argv) > 2 else None
    probs = check(p, orig)
    print('OK' if not probs else 'ISSUES:\n- ' + '\n- '.join(probs))
    sys.exit(1 if probs else 0)
