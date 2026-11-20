"""Converts text to SVG path data with fontTools (kerning via the font's GPOS pair tables)."""
import json, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

def kern_table(font):
    pairs = {}
    if "GPOS" not in font: return pairs
    for lookup in font["GPOS"].table.LookupList.Lookup:
        for st in lookup.SubTable:
            if lookup.LookupType == 9: st = st.ExtSubTable
            if getattr(st, "LookupType", lookup.LookupType) != 2 or not hasattr(st, "Format"): continue
            cov = st.Coverage.glyphs
            if st.Format == 1:
                for i, first in enumerate(cov):
                    for pvr in st.PairSet[i].PairValueRecord:
                        v = pvr.Value1.XAdvance if pvr.Value1 and hasattr(pvr.Value1, "XAdvance") else 0
                        pairs.setdefault((first, pvr.SecondGlyph), v or 0)
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs; c2 = st.ClassDef2.classDefs
                for first in cov:
                    rec = st.Class1Record[c1.get(first, 0)]
                    for second, k2 in c2.items():
                        v = rec.Class2Record[k2].Value1
                        x = getattr(v, "XAdvance", 0) if v else 0
                        if x: pairs.setdefault((first, second), x)
    return pairs

def layout(path, text, x, y, size, ls=0.0):
    font = TTFont(path)
    gs = font.getGlyphSet(); cmap = font.getBestCmap(); upm = font["head"].unitsPerEm
    kern = kern_table(font); s = size / upm
    names = [cmap[ord(c)] for c in text]
    pen = SVGPathPen(gs); cx = x
    for i, n in enumerate(names):
        gs[n].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
        cx += gs[n].width * s + ls * size
        if i + 1 < len(names): cx += kern.get((n, names[i + 1]), 0) * s
    return {"d": pen.getCommands(), "width": cx - x}

if __name__ == "__main__":
    jobs = json.loads(sys.argv[1])
    print(json.dumps([layout(**j) for j in jobs]))
