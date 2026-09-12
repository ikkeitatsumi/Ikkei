# Render the generated HTML (pdf/*.html) to compact PDFs using non-embedded Adobe Japan1 CID fonts.
import re, html, glob, os, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

class CIDFontUTF16(UnicodeCIDFont):
    def __init__(self, face):
        UnicodeCIDFont.__init__(self, face)
        self.encoding = 'UniJIS-UTF16-H'
    def addObjects(self, doc):
        UnicodeCIDFont.addObjects(self, doc)
        # patch encoding name in the generated Type0 font object
        for k, v in list(doc.idToObject.items()):
            if getattr(v, 'Encoding', None) in ('UniJIS-UCS2-H',) and getattr(v, 'BaseFont', '').startswith(self.face.name):
                v.Encoding = 'UniJIS-UTF16-H'

MIN, GOT = 'HeiseiMin-W3', 'HeiseiKakuGo-W5'
pdfmetrics.registerFont(CIDFontUTF16(MIN))
pdfmetrics.registerFont(CIDFontUTF16(GOT))

def css(style):
    d = {}
    for part in style.split(';'):
        if ':' in part:
            k, v = part.split(':', 1); d[k.strip()] = v.strip()
    return d

def pt(v):
    v = v.strip()
    if v.endswith('pt'): return float(v[:-2])
    return float(v)

def para(text, st):
    d = css(st)
    align = {'center': TA_CENTER, 'right': TA_RIGHT}.get(d.get('text-align', 'left'), TA_LEFT)
    fs = pt(d.get('font-size', '10.5pt'))
    lh = float(d.get('line-height', '1.33'))
    font = GOT if 'IPAGothic' in d.get('font-family', '') else MIN
    m = d.get('margin', '0 0 5pt 0').split()
    before, after = pt(m[0]), pt(m[2]) if len(m) > 2 else 0
    left = pt(d['padding-left']) if 'padding-left' in d else 0
    ti = pt(d['text-indent']) if 'text-indent' in d else 0
    ps = ParagraphStyle('p', fontName=font, fontSize=fs, leading=fs * lh, alignment=align,
                        spaceBefore=before, spaceAfter=after, leftIndent=left, firstLineIndent=ti, wordWrap='CJK')
    t = html.unescape(text).replace('&', '&amp;').replace('<', '&lt;').replace('\u3000', '\u00a0\u00a0')
    if t.strip() == '': t = '&nbsp;'
    return Paragraph(t, ps)

def table(block):
    d = css(re.search(r'<table style="([^"]*)"', block).group(1))
    widthpct = float(d.get('width', '100%').rstrip('%')) / 100
    fs = pt(d.get('font-size', '10pt'))
    cols = [float(x) / 100 for x in re.findall(r'<col style="width:([\d.]+)%">', block)]
    avail = (210 - 50) * mm * widthpct
    colw = [avail * c for c in cols]
    rows, styles = [], []
    trs = re.findall(r'<tr>(.*?)</tr>', block, flags=re.S)
    for ri, tr in enumerate(trs):
        cells = re.findall(r'<(th|td) style="([^"]*)">(.*?)</\1>', tr, flags=re.S)
        row = []
        for ci, (tag, st, txt) in enumerate(cells):
            cd = css(st)
            align = {'center': TA_CENTER, 'right': TA_RIGHT}.get(cd.get('text-align', 'left'), TA_LEFT)
            font = GOT if (tag == 'th' or 'IPAGothic' in cd.get('font-family', '')) else MIN
            ps = ParagraphStyle('c', fontName=font, fontSize=fs, leading=fs * 1.17, alignment=align, wordWrap='CJK')
            t = html.unescape(txt).replace('&', '&amp;').replace('<', '&lt;').replace('\u3000', '\u00a0\u00a0')
            row.append(Paragraph(t if t.strip() else '&nbsp;', ps))
            if tag == 'th': styles.append(('BACKGROUND', (ci, ri), (ci, ri), colors.HexColor('#e7e6e6')))
        rows.append(row)
    ts = TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                     ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                     ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)] + styles)
    t = Table(rows, colWidths=colw, repeatRows=1 if trs and '<th' in trs[0] else 0, hAlign='LEFT')
    t.setStyle(ts)
    return [t, Spacer(1, 5)]

def build(html_path, out_path):
    src = open(html_path, encoding='utf-8').read()
    body = re.search(r'<body>(.*)</body>', src, flags=re.S).group(1)
    tokens = re.findall(r'(<p style="[^"]*">.*?</p>|<table .*?</table>|<div style="page-break-after:always"></div>)', body, flags=re.S)
    story = []
    for tok in tokens:
        if tok.startswith('<p'):
            m = re.match(r'<p style="([^"]*)">(.*?)</p>', tok, flags=re.S); story.append(para(m.group(2), m.group(1)))
        elif tok.startswith('<table'):
            story += table(tok)
        else:
            story.append(PageBreak())
    title = os.path.basename(out_path)[:-4]
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=25 * mm, rightMargin=25 * mm, topMargin=25 * mm, bottomMargin=25 * mm, title=title, author='株式会社Golder')
    doc.build(story)
    return os.path.getsize(out_path)

if __name__ == '__main__':
    os.makedirs('pdf_rl', exist_ok=True)
    for f in sorted(glob.glob('pdf/0[1-6]*.html')):
        out = os.path.join('pdf_rl', os.path.basename(f)[:-5] + '.pdf')
        print(build(f, out), out)
