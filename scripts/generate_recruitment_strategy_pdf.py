from pathlib import Path
import re, textwrap
ROOT = Path(__file__).resolve().parents[1]
MD = ROOT/'docs'/'estrategia-go-to-market-recrutamento.md'
PDF = ROOT/'docs'/'estrategia-go-to-market-recrutamento.pdf'
PAGE_W, PAGE_H = 595, 842
LEFT, TOP, BOTTOM = 50, 790, 50
FONT_SIZE = 9.5
LEADING = 13
MAX_CHARS = 92

def clean(s):
    s = re.sub(r'\*\*(.*?)\*\*', r'\1', s)
    s = s.replace('—','-').replace('–','-').replace('“','"').replace('”','"').replace('’',"'")
    return s

def lines_from_md(text):
    out=[]
    in_code=False
    for raw in text.splitlines():
        line=clean(raw.rstrip())
        if line.startswith('```'):
            in_code=not in_code; continue
        if not line or line=='---':
            out.append(('blank','')); continue
        if line.startswith('# '): out += [('blank',''),('title',line[2:]),('blank','')]; continue
        if line.startswith('## '): out += [('blank',''),('h1',line[3:])]; continue
        if line.startswith('### '): out += [('blank',''),('h2',line[4:])]; continue
        if line.startswith('- '): line='- '+line[2:]
        prefix=''
        if line.startswith('|'):
            if set(line.replace('|','').replace(':','').replace('-','').strip()) == set(): continue
            line=' | '.join(c.strip() for c in line.strip('|').split('|'))
        for part in textwrap.wrap(line, width=MAX_CHARS, subsequent_indent='  ' if line.startswith('- ') else '') or ['']:
            out.append(('body',part))
    return out

def esc_pdf(s):
    return s.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')

def make_pdf(pages):
    objs=[]
    def add(obj): objs.append(obj); return len(objs)
    font_id=add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    page_ids=[]
    content_ids=[]
    for page in pages:
        parts=['BT /F1 9.5 Tf 50 790 Td']
        y=TOP
        first=True
        for typ, text in page:
            size = 18 if typ=='title' else 13 if typ=='h1' else 11 if typ=='h2' else FONT_SIZE
            lead = 22 if typ=='title' else 17 if typ=='h1' else 15 if typ=='h2' else LEADING
            if typ=='blank':
                parts.append(f'0 -{LEADING} Td'); y-=LEADING; continue
            if first:
                parts.append(f'/F1 {size} Tf')
                first=False
            else:
                parts.append(f'/F1 {size} Tf 0 -{lead} Td')
                y-=lead
            safe=esc_pdf(text.encode('latin-1','replace').decode('latin-1'))
            parts.append(f'({safe}) Tj')
        parts.append('ET')
        stream='\n'.join(parts).encode('latin-1')
        content_ids.append(add(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream'))
        page_ids.append(None)
    pages_id_placeholder=len(objs)+len(pages)+1
    for idx,cid in enumerate(content_ids):
        page_ids[idx]=add(f'<< /Type /Page /Parent {pages_id_placeholder} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {cid} 0 R >>'.encode())
    kids=' '.join(f'{pid} 0 R' for pid in page_ids)
    pages_id=add(f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'.encode())
    catalog_id=add(f'<< /Type /Catalog /Pages {pages_id} 0 R >>'.encode())
    assert pages_id==pages_id_placeholder
    pdf=bytearray(b'%PDF-1.4\n')
    offsets=[]
    for i,obj in enumerate(objs,1):
        offsets.append(len(pdf)); pdf+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(pdf); pdf+=f'xref\n0 {len(objs)+1}\n0000000000 65535 f \n'.encode()
    for off in offsets: pdf+=f'{off:010d} 00000 n \n'.encode()
    pdf+=f'trailer << /Size {len(objs)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return pdf

items=lines_from_md(MD.read_text(encoding='utf-8'))
pages=[]; current=[]; y=TOP
for typ,text in items:
    lead = 22 if typ=='title' else 17 if typ=='h1' else 15 if typ=='h2' else LEADING
    if y-lead < BOTTOM and current:
        pages.append(current); current=[]; y=TOP
    current.append((typ,text)); y-=lead
if current: pages.append(current)
PDF.write_bytes(make_pdf(pages))
print(f'Generated {PDF} ({len(pages)} pages)')
