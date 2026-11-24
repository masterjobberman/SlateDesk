"""Local ink export; GPL-2.0-or-later."""
from pathlib import Path
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

def segments(page):
    for stroke in page['strokes']:
        if len(stroke) == 1:
            yield stroke[0], stroke[0], max(8, 10 + stroke[0][2] / 2047 * 28)
        for a, b in zip(stroke, stroke[1:]):
            yield a, b, max(8, 10 + (a[2]+b[2]) / 4094 * 28)

def raster(page, longest=2000):
    scale = longest / max(page['width'], page['height'])
    im = Image.new('RGB', (max(1, round(page['width']*scale)), max(1, round(page['height']*scale))), 'white')
    draw = ImageDraw.Draw(im)
    for a,b,w in segments(page):
        width = max(1, round(w*scale))
        draw.line((a[0]*scale,a[1]*scale,b[0]*scale,b[1]*scale), fill='#172c38', width=width)
        r = width/2
        draw.ellipse((b[0]*scale-r,b[1]*scale-r,b[0]*scale+r,b[1]*scale+r), fill='#172c38')
    return im

def export(page, path):
    ext = Path(path).suffix.lower()
    if ext == '.png':
        raster(page).save(path)
    elif ext == '.svg':
        lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {page["width"]} {page["height"]}">', '<g stroke="#172c38" stroke-linecap="round">']
        for a,b,w in segments(page):
            if a[:2] == b[:2]:
                lines.append(f'<circle cx="{a[0]}" cy="{a[1]}" r="{w/2}" fill="#172c38" stroke="none"/>')
            else:
                lines.append(f'<path d="M {a[0]} {a[1]} L {b[0]} {b[1]}" stroke-width="{w}"/>')
        Path(path).write_text('\n'.join(lines + ['</g></svg>']), encoding='utf-8')
    elif ext == '.pdf':
        scale = 595.28 / page['width']
        c = canvas.Canvas(str(path), pagesize=(595.28, page['height']*scale))
        c.setLineCap(1)
        c.setStrokeColorRGB(.09,.17,.22)
        c.setFillColorRGB(.09,.17,.22)
        for a,b,w in segments(page):
            c.setLineWidth(w*scale)
            if a[:2] == b[:2]:
                c.circle(a[0]*scale,(page['height']-a[1])*scale,w*scale/2,stroke=0,fill=1)
            else:
                c.line(a[0]*scale,(page['height']-a[1])*scale,b[0]*scale,(page['height']-b[1])*scale)
        c.showPage()
        c.save()
    else:
        raise ValueError('Choose SVG, PNG or PDF.')
