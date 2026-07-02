#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de vídeos MP4 animados — Método MEVA (v5 — identidade visual "Movimento")
Posts 1-3: editor de código com syntax highlight real, digitação letra a letra
Posts 4-6: abertura cinematográfica com a logo + linha do tempo conectada (Ciclo MEVA)
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy import ImageSequenceClip
import os
import re
import math
import zipfile
import datetime, importlib, sys

def _carregar_conteudo():
    hoje = datetime.date.today().isoformat()          # ex: "2026-06-07"
    modulo = f"conteudo_{hoje}"
    try:
        return importlib.import_module(modulo)
    except ModuleNotFoundError:
        print(f"[ERRO] Arquivo '{modulo}.py' não encontrado para hoje ({hoje}).")
        print("       Peça à IA para gerar os conteúdos da semana.")
        sys.exit(1)

_c = _carregar_conteudo()
DATE_STR   = _c.DATE_STR
DAY_NAME   = _c.DAY_NAME
POSTS_CODE = _c.POSTS_CODE
POST4      = _c.POST4
POST5      = _c.POST5
POST6      = getattr(_c, "POST6", None) # Proteção caso pegue um arquivo antigo com 5 posts
LEGENDAS   = _c.LEGENDAS

# ── Constantes ────────────────────────────────────────────────────────────────
W, H     = 1080, 1080
FPS      = 30
N_FRAMES_DEFAULT = int(7.0 * FPS)

# Identidade visual — cores calibradas a partir da logo oficial
BG_TOP    = (14,  8,  14)
BG_BOTTOM = (4,   3,   6)
RED       = (246, 20,  69)     # vermelho oficial da logo (setas do "M")
WHITE     = (255, 255, 255)
GRAY      = (168, 165, 172)
DARK_GRAY = (90,  85,  92)
CODE_BG   = (16,  16,  20)
YELLOW    = (255, 209, 102)
CYAN      = (110, 214, 255)
COMMENT   = (110, 153, 114)
KEYWORD   = (99,  179, 237)
STRING    = (214, 152, 127)
TYPE_CLR  = (156, 214, 255)
NUMBER    = (255, 176, 120)

LOGO_PATH = "/home/user/logo.png"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SANS      = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MONO      = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

OUT_DIR = f"/home/user/{DATE_STR}_{DAY_NAME}"
os.makedirs(OUT_DIR, exist_ok=True)

_font_cache = {}
def fnt(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]

# ── Animação ──────────────────────────────────────────────────────────────────
def clamp01(x):   return max(0.0, min(1.0, x))
def ease_out(t):  t = clamp01(t); return 1 - (1-t)**3
def phase(t, s, e): return clamp01((t - s) / max(e - s, 0.001))
def pulse(t, hz=0.75): return 0.85 + 0.15 * math.sin(t * 2 * math.pi * hz)

# ── Primitivos de layer RGBA ──────────────────────────────────────────────────
def lyr():       return Image.new("RGBA", (W, H), (0, 0, 0, 0))
def ai(a):       return int(255 * clamp01(a))

def _tw(text, font):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bb = d.textbbox((0, 0), text, font=font)
    return bb[2]-bb[0], bb[3]-bb[1]

def fit_font(path, text, base_size, max_width, min_size=28, step=2):
    """Reduz o tamanho da fonte até o texto caber em max_width — evita títulos cortados."""
    size = base_size
    while size > min_size and _tw(text, fnt(path, size))[0] > max_width:
        size -= step
    return fnt(path, size)

def cx(text, font): w, _ = _tw(text, font); return (W - w) // 2

def put(img, lyr_): return Image.alpha_composite(img, lyr_)

def put_text(img, text, x, y, font, color, a=1.0):
    if a < 0.01: return img
    L = lyr(); ImageDraw.Draw(L).text((x,y), text, font=font, fill=(*color, ai(a)))
    return put(img, L)

def put_ctxt(img, text, y, font, color, a=1.0, yo=0):
    return put_text(img, text, cx(text, font), y+yo, font, color, a)

def put_glow(img, text, y, font, color, a=1.0, yo=0, r=12):
    if a < 0.01: return img
    x = cx(text, font)
    G = lyr()
    ImageDraw.Draw(G).text((x, y+yo), text, font=font, fill=(*color, ai(a*0.8)))
    G = G.filter(ImageFilter.GaussianBlur(radius=r))
    img = put(img, G)
    T = lyr(); ImageDraw.Draw(T).text((x, y+yo), text, font=font, fill=(*color, ai(a)))
    return put(img, T)

def put_tag(img, text, cy, fsz, a=1.0, tracking=4, xo=0):
    """Rótulo pequeno com espaçamento entre letras dentro de uma pílula com contorno —
    usado como selo/eyebrow acima dos títulos, em todos os tipos de post."""
    if a < 0.01: return img
    f = fnt(SANS_BOLD, fsz)
    widths = [_tw(ch, f)[0] for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    pad = 24
    bx1 = (W - total)//2 - pad + xo; bx2 = (W + total)//2 + pad + xo
    v = ai(a)
    L = lyr(); d = ImageDraw.Draw(L)
    d.rounded_rectangle([bx1, cy, bx2, cy+fsz+16], radius=20, outline=(*RED, v), width=2)
    x = (W - total)//2 + xo
    for ch, w in zip(text, widths):
        d.text((x, cy+8), ch, font=f, fill=(*WHITE, v))
        x += w + tracking
    return put(img, L)

def put_badge(img, text, cy, fsz, a=1.0, xo=0):
    """Pílula preenchida em vermelho — usada nos CTAs."""
    if a < 0.01: return img
    f = fnt(SANS_BOLD, fsz); w,h_ = _tw(text,f)
    bx1=(W-w)//2-24+xo; bx2=(W+w)//2+24+xo; v=ai(a)
    L = lyr(); d = ImageDraw.Draw(L)
    d.rounded_rectangle([bx1,cy,bx2,cy+fsz+18], radius=24, fill=(*RED,v))
    d.text(((W-w)//2+xo, cy+(fsz+18-h_)//2), text, font=f, fill=(*WHITE,v))
    return put(img, L)

def put_divider(img, y, a=1.0, short=False):
    if a < 0.01: return img
    x1, x2 = (260, W-260) if short else (70, W-70)
    L = lyr(); d = ImageDraw.Draw(L)
    mx = W // 2
    d.line([x1, y, mx-8, y], fill=(*DARK_GRAY, ai(a*0.7)), width=2)
    d.line([mx+8, y, x2, y], fill=(*DARK_GRAY, ai(a*0.7)), width=2)
    d.ellipse([mx-5, y-5, mx+5, y+5], fill=(*RED, ai(a)))
    return put(img, L)

def put_footer(img, a=1.0):
    L = lyr(); d = ImageDraw.Draw(L); v = ai(a)
    f  = fnt(SANS, 23); fy = H - 52
    d.line([30, fy-12, W-30, fy-12], fill=(*RED,ai(a*0.45)), width=2)
    txt = "@metodomeva  ·  +55 11 91855-6529"
    tw_, _ = _tw(txt, f)
    d.text(((W-tw_)//2, fy), txt, font=f, fill=(*GRAY,v))
    return put(img, L)

_logo_cache = {}
def _logo(h):
    if h not in _logo_cache:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        ratio = h / logo.height
        _logo_cache[h] = logo.resize((int(logo.width*ratio), h), Image.LANCZOS)
    return _logo_cache[h]

def put_logo_corner(img, a=1.0):
    if a < 0.01: return img
    logo = _logo(84)
    r,g,b,ac = logo.split(); ac = ac.point(lambda x: int(x*a))
    logo = Image.merge("RGBA",(r,g,b,ac))
    L = lyr(); L.paste(logo, (26, 20), logo)
    return put(img, L)

def put_logo_center(img, h, center, a=1.0):
    if a < 0.01: return img
    logo = _logo(h)
    r,g,b,ac = logo.split(); ac = ac.point(lambda x: int(x*a))
    logo = Image.merge("RGBA",(r,g,b,ac))
    x = center[0] - logo.width // 2
    y = center[1] - logo.height // 2
    L = lyr(); L.paste(logo, (x, y), logo)
    return put(img, L)

# ── Fundo estilizado (gradiente + vinheta + grid + speed-lines) ───────────────
_yy, _xx = np.mgrid[0:H, 0:W]
_cxp, _cyp = W/2, H*0.4
_dist = np.sqrt((_xx-_cxp)**2 + (_yy-_cyp)**2) / (W*0.8)
_vig  = np.clip(1 - _dist*0.55, 0.42, 1.0)[..., None]
_ys   = np.linspace(0, 1, H).reshape(H, 1, 1)
_grad = (np.array(BG_TOP)*(1-_ys) + np.array(BG_BOTTOM)*_ys)
_grad = np.repeat(_grad, W, axis=1)
_BASE_GRADIENT = Image.fromarray(np.clip(_grad*_vig, 0, 255).astype(np.uint8)).convert("RGBA")

def stylized_bg(t, intensity=1.0):
    """Fundo com gradiente + vinheta + grid de pontos + linhas diagonais em movimento
    (o motivo das setas da logo). intensity controla a força visual (mais discreto
    nos posts de código para não competir com a leitura do código)."""
    img = _BASE_GRADIENT.copy()
    d = ImageDraw.Draw(img)
    dot_a = int(9 * intensity)
    for x in range(-20, W+20, 58):
        for y in range(-20, H+20, 58):
            d.ellipse([x-1,y-1,x+1,y+1], fill=(255,255,255,dot_a))
    offset = (t * 120) % 260
    line_a = int(18 * intensity)
    for i in range(-3, 12):
        x0 = i*260 - offset
        d.line([(x0, H+60),(x0+460, -60)], fill=(*RED, line_a), width=3)
    return img

# ── Editor de código (syntax highlight real) ───────────────────────────────────
_TOKEN_RE = re.compile(r"""
    (?P<comment>//.*$)
  | (?P<annotation>@\w+)
  | (?P<string>"(?:[^"\\]|\\.)*")
  | (?P<keyword>\b(?:public|private|protected|class|interface|enum|void|return|new|
        static|final|import|package|extends|implements|throws|throw|try|catch|if|else|
        for|while|boolean|int|long|double|float|char|byte|short|record|var)\b)
  | (?P<type>\b(?:String|List|Map|Set|Optional|ResponseEntity|HttpStatus|Override|Long|
        Integer|Double|Boolean|Comparator|Collectors|Collections|Pageable|Page|
        PageRequest|Sort|FilterChain|HttpServletRequest|HttpServletResponse|
        IOException|OncePerRequestFilter|[A-Z]\w*)\b)
  | (?P<number>\b\d+(?:\.\d+)?[fFdDlL]?\b)
""", re.VERBOSE)

_TOKEN_COLOR = {
    "comment": COMMENT, "annotation": YELLOW, "string": STRING,
    "keyword": KEYWORD, "type": TYPE_CLR, "number": NUMBER,
}

def tokenize_line(line):
    """Retorna lista [(texto, cor), ...] cobrindo a linha inteira (inclui espaços),
    preservando os índices originais para o efeito de digitação letra a letra."""
    segs = []
    pos = 0
    for m in _TOKEN_RE.finditer(line):
        if m.start() > pos:
            segs.append((line[pos:m.start()], WHITE))
        kind = m.lastgroup
        segs.append((m.group(), _TOKEN_COLOR.get(kind, WHITE)))
        pos = m.end()
    if pos < len(line):
        segs.append((line[pos:], WHITE))
    return segs or [("", WHITE)]

def _slice_segments(segs, nshow):
    out, remaining = [], nshow
    for text, color in segs:
        if remaining <= 0: break
        if len(text) <= remaining:
            out.append((text, color)); remaining -= len(text)
        else:
            out.append((text[:remaining], color)); remaining = 0
    return out

_FNAME_RE = re.compile(r"\b(?:class|interface|enum|record)\s+(\w+)")
def guess_filename(lines):
    for ln in lines:
        m = _FNAME_RE.search(ln)
        if m:
            return f"{m.group(1)}.java"
    return "Metodo.java"

def put_code(img, lines, n_chars, y0, fsz=26, xm=60, t=0, typing_done=False):
    f     = fnt(MONO, fsz); fh = fsz+10; pad = 22; header_h = 40
    f_fname = fnt(MONO_BOLD, 20)
    mw    = max((_tw(ln,f)[0] for ln in lines if ln.strip()), default=400)
    bw    = min(mw+pad*2, W-xm*2)
    bh    = len(lines)*fh + pad*2
    bx1   = (W-bw-pad*2)//2; bx2 = bx1+bw+pad*2
    by0   = y0; by1 = y0 + header_h + bh

    L = lyr(); d = ImageDraw.Draw(L)
    # sombra suave
    S = lyr(); ds = ImageDraw.Draw(S)
    ds.rounded_rectangle([bx1, by0+6, bx2, by1+6], radius=14, fill=(0,0,0,140))
    S = S.filter(ImageFilter.GaussianBlur(14))
    img = put(img, S)

    d.rounded_rectangle([bx1, by0, bx2, by1], radius=14, fill=(*CODE_BG,255))
    d.rounded_rectangle([bx1, by0, bx2, by0+header_h], radius=14,
                         fill=(24,24,29,255))
    d.rectangle([bx1, by0+header_h-14, bx2, by0+header_h], fill=(24,24,29,255))
    d.rounded_rectangle([bx1, by0, bx2, by1], radius=14, outline=(*RED,200), width=2)
    d.line([bx1+2, by0+header_h, bx2-2, by0+header_h], fill=(0,0,0,120), width=1)

    # "traffic lights" do editor + nome do arquivo
    for i, c in enumerate([(90,90,96), (90,90,96), RED]):
        cx_ = bx1 + 26 + i*22
        d.ellipse([cx_-6, by0+header_h//2-6, cx_+6, by0+header_h//2+6], fill=(*c,255))
    fname = guess_filename(lines)
    d.text((bx1+26+3*22+14, by0+(header_h-20)//2), fname, font=f_fname,
           fill=(*GRAY,255))

    fln  = fnt(MONO, fsz-6)
    disp_n = _code_display_counts(lines, n_chars)
    cursor_on = (int(t * 4) % 2 == 0) and not typing_done

    body_y0 = by0 + header_h
    for i, (line, nshow) in enumerate(disp_n):
        ty = body_y0+pad+i*fh
        d.text((bx1+8, ty+3), str(i+1).rjust(2), font=fln, fill=(*DARK_GRAY,180))
        if nshow > 0:
            segs = _slice_segments(tokenize_line(line), nshow)
            x = bx1+pad+18
            for text, color in segs:
                if text:
                    d.text((x, ty), text, font=f, fill=(*color,255))
                    x += _tw(text, f)[0]
            if i == len(disp_n)-1 and cursor_on:
                d.rectangle([x+2, ty+2, x+5, ty+fsz-2], fill=(*WHITE,220))

    return put(img, L)

def _code_display_counts(lines, n_chars):
    result = []
    remaining = n_chars
    for line in lines:
        if remaining <= 0:
            break
        ln = len(line)
        if ln == 0:
            result.append(("", 0)); remaining -= 1
        elif remaining >= ln:
            result.append((line, ln)); remaining -= ln
        else:
            result.append((line, remaining)); remaining = 0
    return result

# ── Cards conectados (linha do tempo — usados nos posts 4, 5 e 6) ─────────────
def _split_bullet(text):
    """Remove prefixo de ícone (✔ ★ ✦ ➤ ◆) e separa 'Título — descrição' se houver
    o travessão; retorna (icone_ou_None, titulo, descricao_ou_None)."""
    icon = None
    s = text.strip()
    if s and not s[0].isalnum():
        parts = s.split(None, 1)
        icon = parts[0]
        s = parts[1] if len(parts) > 1 else ""
    if " — " in s:
        titulo, desc = s.split(" — ", 1)
    else:
        titulo, desc = s, None
    return icon, titulo.strip(), (desc.strip() if desc else None)

def put_step_card(img, index_label, item_text, y0, a, xo=0, h=78):
    if a < 0.01: return img
    icon, titulo, desc = _split_bullet(item_text)
    # Ícones distintos (★ ✦ ➤ ◆ do POST5) têm prioridade visual sobre a numeração —
    # são parte obrigatória da identidade da marca e nunca podem sumir do vídeo.
    label = icon if (icon and icon != "✔") else index_label
    x1, x2 = 90+xo, 990+xo
    v = ai(a)
    L = lyr(); d = ImageDraw.Draw(L)
    d.rounded_rectangle([x1,y0,x2,y0+h], radius=14, fill=(255,255,255,int(10*a)))
    d.rounded_rectangle([x1,y0,x1+6,y0+h], radius=3, fill=(*RED,v))
    f_idx = fnt(SANS_BOLD, 26)
    d.text((x1+30, y0+h//2-16), label, font=f_idx, fill=(*RED,v))
    tx = x1 + 96
    if desc:
        f_t = fit_font(SANS_BOLD, titulo, 26, x2-tx-24)
        f_d = fit_font(SANS, desc, 21, x2-tx-24)
        d.text((tx, y0+12), titulo, font=f_t, fill=(*WHITE,v))
        d.text((tx, y0+44), desc, font=f_d, fill=(*GRAY,v))
    else:
        f_t = fit_font(SANS_BOLD, titulo, 27, x2-tx-24)
        _, th = _tw(titulo, f_t)
        d.text((tx, y0+(h-th)//2-4), titulo, font=f_t, fill=(*WHITE,v))
    return put(img, L)

def put_connector(img, y_from, y_to, a):
    if a < 0.01: return img
    x = 90 + 30
    L = lyr(); d = ImageDraw.Draw(L)
    y_mid = y_from + (y_to - y_from) * a
    d.line([x, y_from, x, y_mid], fill=(*RED, ai(a*0.5)), width=2)
    return put(img, L)

def render_step_flow(img, t, items, y0, start_t, stagger=0.42, item_dur=0.4, h=78, gap=14):
    positions = [y0 + i*(h+gap) for i in range(len(items))]
    for i, item in enumerate(items):
        s0 = start_t + i*stagger
        ca = ease_out(phase(t, s0, s0+item_dur))
        img = put_step_card(img, f"0{i+1}", item, positions[i], ca, xo=int((1-ca)*-60), h=h)
        if i > 0:
            conn_a = ease_out(phase(t, s0-0.15, s0+0.1))
            img = put_connector(img, positions[i-1]+h, positions[i], conn_a)
    end_t = start_t + (len(items)-1)*stagger + item_dur
    bottom_y = positions[-1] + h
    return img, end_t, bottom_y

# ── Abertura cinematográfica com a logo (posts 4, 5 e 6) ──────────────────────
def render_intro(img, t, bg_intensity=1.0):
    bg_a = ease_out(phase(t, 0.0, 0.85))
    styl = stylized_bg(t, bg_intensity)
    r,g,b,a_ = styl.split(); a_ = a_.point(lambda v: int(v*bg_a))
    img = put(img, Image.merge("RGBA", (r,g,b,a_)))

    if t < 0.55:
        a_big = ease_out(phase(t, 0.0, 0.42))
    else:
        a_big = 1 - ease_out(phase(t, 0.55, 0.95))
    if a_big > 0.01:
        pr = 300 + 20*math.sin(t*2*math.pi*0.8)
        G = lyr(); dg = ImageDraw.Draw(G)
        dg.ellipse([W/2-pr, H*0.4-pr, W/2+pr, H*0.4+pr], fill=(*RED, int(30*a_big)))
        G = G.filter(ImageFilter.GaussianBlur(60))
        img = put(img, G)
        img = put_logo_center(img, 260, (W//2, int(H*0.4)), a_big)

    a_corner = ease_out(phase(t, 0.55, 0.95))
    img = put_logo_corner(img, a_corner)
    return img

# ── Renderizadores ────────────────────────────────────────────────────────────

def render_code_post(t, cfg):
    img = Image.new("RGBA", (W, H), (*BG_BOTTOM, 255))
    bg_a = ease_out(phase(t, 0.0, 0.7))
    styl = stylized_bg(t, intensity=0.4)
    r,g,b,a_ = styl.split(); a_ = a_.point(lambda v: int(v*bg_a))
    img = put(img, Image.merge("RGBA", (r,g,b,a_)))

    img = put_logo_corner(img, ease_out(phase(t, 0.0, 0.5)))
    img = put_footer(img, ease_out(phase(t, 0.3, 0.8)))

    # Título sobe com glow 0.6..1.3s — fonte se ajusta para nunca cortar
    ta = ease_out(phase(t, 0.6, 1.3))
    title_font = fit_font(SANS_BOLD, cfg["title"], 54, W - 140)
    img = put_glow(img, cfg["title"], 98, title_font, WHITE, ta, yo=int((1-ta)*45), r=10)

    # Subtítulo fade+sobe 1.1..1.7s
    sa = ease_out(phase(t, 1.1, 1.7))
    subtitle_font = fit_font(SANS, cfg["subtitle"], 30, W - 140)
    img = put_ctxt(img, cfg["subtitle"], 163, subtitle_font, GRAY, sa, yo=int((1-sa)*22))

    img = put_divider(img, 210, ease_out(phase(t, 1.3, 1.6)), short=True)

    # Selo com o nome da feature — logo acima do editor de código, 1.5..1.9s
    ba = ease_out(phase(t, 1.5, 1.9))
    img = put_tag(img, cfg["badge"].strip().upper(), 222, 20, ba, xo=int((1-ba)*-320))

    # Código digita letra a letra — ~60 chars/s, cursor piscando, syntax highlight real
    code        = cfg["code"]
    total_chars = sum(max(len(ln), 1) for ln in code)
    CHARS_PER_S = 60
    type_end    = 1.8 + total_chars / CHARS_PER_S
    ct          = phase(t, 1.8, type_end)
    if ct > 0:
        n_chars      = int(ct * total_chars)
        typing_done  = (t >= type_end)
        img = put_code(img, code, n_chars, cfg["code_y"], cfg["code_fsz"],
                       t=t, typing_done=typing_done)

    return np.array(img.convert("RGB"))


def render_post4(t, cfg):
    img = Image.new("RGBA", (W, H), (*BG_BOTTOM, 255))
    img = render_intro(img, t, bg_intensity=1.0)
    img = put_footer(img, ease_out(phase(t, 0.3, 0.8)))

    ta = ease_out(phase(t, 0.9, 1.4))
    img = put_glow(img, "MÉTODO MEVA", 128, fnt(SANS_BOLD, 66), RED, ta, yo=int((1-ta)*40), r=14)
    img = put_divider(img, 208, ease_out(phase(t, 1.25, 1.55)), short=True)

    sa = ease_out(phase(t, 1.35, 1.9))
    f_l1 = fit_font(SANS_BOLD, cfg["subtitle1"], 52, W - 140)
    f_l2 = fit_font(SANS_BOLD, cfg["subtitle2"], 52, W - 140)
    f_ti = f_l1 if f_l1.size <= f_l2.size else f_l2
    yo   = int((1-sa)*26)
    img  = put_ctxt(img, cfg["subtitle1"], 246, f_ti, WHITE, sa, yo)
    img  = put_ctxt(img, cfg["subtitle2"], 314, f_ti, WHITE, sa, yo)

    img = put_divider(img, 388, ease_out(phase(t, 1.85, 2.15)))

    img, end_t, bottom_y = render_step_flow(img, t, cfg["bullets"], 420, start_t=2.15)

    img = put_divider(img, bottom_y+22, ease_out(phase(t, end_t, end_t+0.3)))

    cta_start = end_t + 0.15
    ca = ease_out(phase(t, cta_start, cta_start+0.4))
    cpulse = pulse(t) if t > cta_start+0.4 else 1.0
    img = put_badge(img, cfg["cta"], bottom_y+56, 30, ca*cpulse)

    site_start = cta_start + 0.45
    sita = ease_out(phase(t, site_start, site_start+0.4))
    img = put_glow(img, "portaldoaluno.metodomeva.com.br", bottom_y+118,
                   fnt(SANS_BOLD,26), CYAN, sita, r=8)

    return np.array(img.convert("RGB"))


def render_post5(t, cfg):
    img = Image.new("RGBA", (W, H), (*BG_BOTTOM, 255))
    img = render_intro(img, t, bg_intensity=1.0)
    img = put_footer(img, ease_out(phase(t, 0.3, 0.8)))

    tga = ease_out(phase(t, 0.9, 1.3))
    img = put_tag(img, "POR QUE JAVA EM 2026?", 128, 22, tga)
    img = put_divider(img, 190, ease_out(phase(t, 1.15, 1.45)), short=True)

    h1a = ease_out(phase(t, 1.25, 1.85))
    f_h1 = fit_font(SANS_BOLD, cfg["headline1"], 62, W - 140)
    img = put_glow(img, cfg["headline1"], 218, f_h1, WHITE, h1a, yo=int((1-h1a)*40), r=8)

    h2a = ease_out(phase(t, 1.5, 2.1))
    f_h2 = fit_font(SANS_BOLD, cfg["headline2"], 62, W - 140)
    img = put_glow(img, cfg["headline2"], 292, f_h2, RED, h2a, yo=int((1-h2a)*36), r=14)

    h3a = ease_out(phase(t, 1.75, 2.25))
    f_h3 = fit_font(SANS_BOLD, cfg["headline3"], 42, W - 140)
    img = put_ctxt(img, cfg["headline3"], 366, f_h3, GRAY, h3a, yo=int((1-h3a)*26))

    img = put_divider(img, 424, ease_out(phase(t, 2.15, 2.45)))

    img, end_t, bottom_y = render_step_flow(img, t, cfg["stats"], 452, start_t=2.45)

    img = put_divider(img, bottom_y+22, ease_out(phase(t, end_t, end_t+0.3)))

    cta_start = end_t + 0.15
    ca = ease_out(phase(t, cta_start, cta_start+0.4))
    cpulse = pulse(t) if t > cta_start+0.4 else 1.0
    img = put_badge(img, cfg["cta"], bottom_y+56, 30, ca*cpulse)

    site_start = cta_start + 0.45
    sita = ease_out(phase(t, site_start, site_start+0.4))
    img = put_glow(img, "portaldoaluno.metodomeva.com.br", bottom_y+118,
                   fnt(SANS_BOLD,26), CYAN, sita, r=8)

    return np.array(img.convert("RGB"))


def render_post6(t, cfg):
    """POST6 usa a mesma estrutura do POST4 (mesma identidade visual)."""
    return render_post4(t, cfg)


# ── Gerador de vídeo ──────────────────────────────────────────────────────────

CHARS_PER_S = 60   # 2 chars/frame @ 30fps
CULTURE_DURATION = 9.4   # posts 4, 5 e 6 — inclui a abertura cinematográfica

def video_duration(cfg):
    """Calcula duração necessária para cada vídeo."""
    if cfg is None or "code" not in cfg:
        return CULTURE_DURATION
    total_chars = sum(max(len(ln), 1) for ln in cfg["code"])
    return 1.8 + total_chars / CHARS_PER_S + 1.5   # +1.5s de pausa final

def make_video(render_fn, cfg, out_path):
    dur    = video_duration(cfg)
    nf     = int(dur * FPS)
    name   = os.path.basename(out_path)
    print(f"  Renderizando {name} ({nf} frames, {dur:.1f}s)...", flush=True)
    frames = []
    for i in range(nf):
        t = i / FPS
        frames.append(render_fn(t, cfg) if cfg is not None else render_fn(t))
    clip = ImageSequenceClip(frames, fps=FPS)
    clip.write_videofile(out_path, codec="libx264", audio=False,
                         ffmpeg_params=["-crf","18","-preset","fast"],
                         logger=None)
    kb = os.path.getsize(out_path) // 1024
    print(f"  ✔ {name} ({kb} KB)")


# ── Legendas no estilo moderno ────────────────────────────────────────────────

def create_legendas():
    with open(f"{OUT_DIR}/legendas.txt", "w", encoding="utf-8") as f:
        f.write(LEGENDAS)
    print("  ✔ legendas.txt gerado")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n🎬 Gerando vídeos MP4 para {DATE_STR}_{DAY_NAME} ...\n")

    # Renderiza os posts de código (1 a 3)
    for idx, cfg in enumerate(POSTS_CODE, start=1):
        make_video(render_code_post, cfg, f"{OUT_DIR}/post{idx}.mp4")

    # Renderiza os posts do ecossistema/cultura (4, 5 e 6)
    make_video(render_post4, POST4, f"{OUT_DIR}/post4.mp4")
    make_video(render_post5, POST5, f"{OUT_DIR}/post5.mp4")

    if POST6:
        make_video(render_post6, POST6, f"{OUT_DIR}/post6.mp4")

    create_legendas()

    # ── ZIP com tudo ─────────────────────────────────────────────────────────
    zip_path = f"/home/user/{DATE_STR}_{DAY_NAME}.zip"

    entregaveis = ["post1.mp4","post2.mp4","post3.mp4","post4.mp4","post5.mp4","post6.mp4","legendas.txt"]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in entregaveis:
            fp = f"{OUT_DIR}/{fn}"
            if os.path.exists(fp):
                z.write(fp, fn)

    kb_zip = os.path.getsize(zip_path) // 1024
    print(f"\n✅ Todos os arquivos salvos em: {OUT_DIR}/")
    print(f"📦 ZIP pronto: {zip_path}  ({kb_zip} KB)\n")
