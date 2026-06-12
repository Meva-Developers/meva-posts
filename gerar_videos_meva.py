#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de vídeos MP4 animados — Método MEVA
Posts 1-3: código digita, texto desliza  |  Posts 4-6: elementos surgem em sequência
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy import ImageSequenceClip
import os
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
DURATION = 7.0       # segundos por vídeo
N_FRAMES = int(DURATION * FPS)

BG        = (10,  10,  10)
RED       = (232, 25,  44)
WHITE     = (255, 255, 255)
GRAY      = (160, 160, 160)
DARK_GRAY = (80,  80,  80)
CODE_BG   = (18,  18,  18)
YELLOW    = (255, 214,  0)
CYAN      = (100, 210, 255)
COMMENT   = (106, 153,  85)
KEYWORD   = (86,  156, 214)
STRING    = (206, 145, 120)

LOGO_PATH = "/home/user/logo.png"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SANS      = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MONO      = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

OUT_DIR = f"/home/user/{DATE_STR}_{DAY_NAME}"
os.makedirs(OUT_DIR, exist_ok=True)

def fnt(path, size): return ImageFont.truetype(path, size)

# ── Animação ──────────────────────────────────────────────────────────────────
def clamp01(x):   return max(0.0, min(1.0, x))
def ease_out(t):  t = clamp01(t); return 1 - (1-t)**3
def phase(t, s, e): return clamp01((t - s) / max(e - s, 0.001))
def pulse(t, hz=0.8): return 0.82 + 0.18 * math.sin(t * 2 * math.pi * hz)

# ── Primitivos de layer RGBA ──────────────────────────────────────────────────
def lyr():       return Image.new("RGBA", (W, H), (0, 0, 0, 0))
def ai(a):       return int(255 * clamp01(a))

def _tw(text, font):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bb = d.textbbox((0, 0), text, font=font)
    return bb[2]-bb[0], bb[3]-bb[1]

def fit_font(path, text, base_size, max_width, min_size=32, step=2):
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

def put_glow(img, text, y, font, color, a=1.0, yo=0, r=10):
    if a < 0.01: return img
    x = cx(text, font)
    G = lyr()
    ImageDraw.Draw(G).text((x, y+yo), text, font=font, fill=(*color, ai(a*0.85)))
    G = G.filter(ImageFilter.GaussianBlur(radius=r))
    img = put(img, G)
    T = lyr(); ImageDraw.Draw(T).text((x, y+yo), text, font=font, fill=(*color, ai(a)))
    return put(img, T)

def put_border(img, a=1.0):
    L = lyr(); d = ImageDraw.Draw(L); v = ai(a)
    d.rectangle([0,0,W,8],     fill=(*RED,v))
    d.rectangle([0,H-8,W,H],   fill=(*RED,v))
    d.rectangle([0,8,6,H-8],   fill=(*RED,v))
    d.rectangle([W-6,8,W,H-8], fill=(*RED,v))
    return put(img, L)

def put_footer(img, a=1.0):
    L = lyr(); d = ImageDraw.Draw(L); v = ai(a)
    f  = fnt(SANS, 24); fy = H - 55
    d.line([30, fy-12, W-30, fy-12], fill=(*RED,v), width=2)
    d.text((30, fy), "@metodomeva  ·  +55 11 91855-6529", font=f, fill=(*GRAY,v))
    rt = "portaldoaluno.metodomeva.com.br"
    rtw, _ = _tw(rt, f)
    d.text((W-30-rtw, fy), rt, font=f, fill=(*GRAY,v))
    return put(img, L)

def put_logo(img, a=1.0):
    if a < 0.01: return img
    logo = Image.open(LOGO_PATH).convert("RGBA")
    h = 90; ratio = h / logo.height
    logo = logo.resize((int(logo.width*ratio), h), Image.LANCZOS)
    r,g,b,ac = logo.split(); ac = ac.point(lambda x: int(x*a))
    logo = Image.merge("RGBA",(r,g,b,ac))
    img.paste(logo, (22,18), logo)
    return img

def put_divider(img, y, a=1.0):
    if a < 0.01: return img
    L = lyr(); ImageDraw.Draw(L).line([60,y,W-60,y], fill=(*RED,ai(a)), width=2)
    return put(img, L)

def put_badge(img, text, cy, fsz, a=1.0, xo=0):
    if a < 0.01: return img
    f = fnt(SANS_BOLD, fsz); w,h_ = _tw(text,f)
    bx1=(W-w)//2-20+xo; bx2=(W+w)//2+20+xo; v=ai(a)
    L = lyr(); d = ImageDraw.Draw(L)
    d.rounded_rectangle([bx1,cy,bx2,cy+fsz+14], radius=20, fill=(*RED,v))
    d.text(((W-w)//2+xo, cy+(fsz+14-h_)//2), text, font=f, fill=(*WHITE,v))
    return put(img, L)

# ── Código ────────────────────────────────────────────────────────────────────
JAVA_KW = {
    "public","private","protected","class","interface","enum","void","return",
    "new","static","final","import","package","extends","implements","throws",
    "throw","try","catch","if","else","for","while","boolean","int","long",
    "String","List","Optional","ResponseEntity","HttpStatus","Override",
}

def tok_color(line):
    s = line.strip()
    if s.startswith(("//","*","/*")): return COMMENT
    if s.startswith("@"):             return YELLOW
    for kw in JAVA_KW:
        if kw in s:                  return KEYWORD
    if '"' in s or "'" in s:         return STRING
    return WHITE

def _code_display(lines, n_chars):
    """Converte n_chars em lista de (linha, qtd_chars_a_mostrar)."""
    result = []
    remaining = n_chars
    for line in lines:
        if remaining <= 0:
            break
        ln = len(line)
        if ln == 0:                          # linha vazia conta como 1 char
            result.append(("", 0))
            remaining -= 1
        elif remaining >= ln:
            result.append((line, ln))
            remaining -= ln
        else:
            result.append((line, remaining))
            remaining = 0
    return result

def put_code(img, lines, n_chars, y0, fsz=26, xm=60, t=0, typing_done=False):
    f   = fnt(MONO, fsz); fh = fsz+10; pad = 22
    mw  = max((_tw(ln,f)[0] for ln in lines if ln.strip()), default=400)
    bw  = min(mw+pad*2, W-xm*2)
    bh  = len(lines)*fh + pad*2
    bx1 = (W-bw-pad*2)//2; bx2 = bx1+bw+pad*2
    L   = lyr(); d = ImageDraw.Draw(L)
    d.rounded_rectangle([bx1,y0,bx2,y0+bh], radius=12, fill=(*CODE_BG,255))
    d.rounded_rectangle([bx1,y0,bx2,y0+bh], radius=12, outline=(*RED,255), width=2)
    fln  = fnt(MONO, fsz-6)
    disp = _code_display(lines, n_chars)
    cursor_on = (int(t * 4) % 2 == 0) and not typing_done  # pisca 2Hz

    for i, (line, nshow) in enumerate(disp):
        ty = y0+pad+i*fh
        d.text((bx1+8, ty+3), str(i+1).rjust(2), font=fln, fill=(*DARK_GRAY,180))
        if nshow > 0:
            partial = line[:nshow]
            d.text((bx1+pad+18, ty), partial, font=f, fill=(*tok_color(line),255))
            # cursor na última linha sendo digitada
            if i == len(disp)-1 and cursor_on:
                pw = _tw(partial, f)[0]
                cx_ = bx1+pad+18+pw+2
                d.rectangle([cx_, ty+2, cx_+3, ty+fsz-2], fill=(*WHITE,220))

    return put(img, L)

# ── Renderizadores ────────────────────────────────────────────────────────────

def render_code_post(t, cfg):
    img = Image.new("RGBA", (W, H), (*BG, 255))
    img = put_border(img)
    img = put_footer(img)

    # Logo fade-in 0.0..0.5s
    img = put_logo(img, ease_out(phase(t, 0.0, 0.5)))

    # Badge desliza da esquerda 0.3..0.9s
    ba = ease_out(phase(t, 0.3, 0.9))
    img = put_badge(img, cfg["badge"], 222, 26, ba, xo=int((1-ba)*-320))

    # Título sobe com glow 0.6..1.3s — fonte se ajusta para nunca cortar
    ta = ease_out(phase(t, 0.6, 1.3))
    title_font = fit_font(SANS_BOLD, cfg["title"], 56, W - 140)
    img = put_glow(img, cfg["title"], 98, title_font, WHITE, ta,
                   yo=int((1-ta)*55), r=10)

    # Subtítulo fade+sobe 1.1..1.7s
    sa = ease_out(phase(t, 1.1, 1.7))
    subtitle_font = fit_font(SANS, cfg["subtitle"], 32, W - 140)
    img = put_ctxt(img, cfg["subtitle"], 165, subtitle_font, GRAY, sa,
                   yo=int((1-sa)*25))

    # Divisor 1.3..1.7s
    img = put_divider(img, 213, ease_out(phase(t, 1.3, 1.7)))

    # Código digita letra a letra — ~25 chars/s, cursor piscando
    code        = cfg["code"]
    total_chars = sum(max(len(ln), 1) for ln in code)
    CHARS_PER_S = 60                             # 2 chars/frame @ 30fps
    type_end    = 1.8 + total_chars / CHARS_PER_S
    ct          = phase(t, 1.8, type_end)
    if ct > 0:
        n_chars      = int(ct * total_chars)
        typing_done  = (t >= type_end)
        img = put_code(img, code, n_chars, cfg["code_y"], cfg["code_fsz"],
                       t=t, typing_done=typing_done)

    return np.array(img.convert("RGB"))


def render_post4(t, cfg):
    img = Image.new("RGBA", (W, H), (*BG, 255))

    # Grade sutil
    G = lyr(); d = ImageDraw.Draw(G)
    for x in range(0, W, 60): d.line([(x,0),(x,H)], fill=(20,20,20,255), width=1)
    for y in range(0, H, 60): d.line([(0,y),(W,y)], fill=(20,20,20,255), width=1)
    img = put(img, G)

    # Círculos pulsando
    C = lyr(); d = ImageDraw.Draw(C)
    p = pulse(t, 0.4); cx_, cy_ = W//2, H//2+20
    for r_, base_a in [(300,12),(250,18),(200,25)]:
        d.ellipse([(cx_-r_,cy_-r_),(cx_+r_,cy_+r_)], fill=(*RED, int(base_a*p)))
    img = put(img, C)

    img = put_border(img)
    img = put_footer(img)
    img = put_logo(img, ease_out(phase(t, 0.0, 0.5)))

    # Título com glow vermelho 0.4..1.1s
    ta = ease_out(phase(t, 0.4, 1.1))
    img = put_glow(img, "MÉTODO MEVA", 118, fnt(SANS_BOLD,82), RED, ta,
                   yo=int((1-ta)*60), r=16)

    img = put_divider(img, 226, ease_out(phase(t, 1.0, 1.4)))

    # Subtítulo 1.1..1.7s — fonte se ajusta para nunca cortar
    sa = ease_out(phase(t, 1.1, 1.7))
    f_l1 = fit_font(SANS_BOLD, cfg["subtitle1"], 56, W - 140)
    f_l2 = fit_font(SANS_BOLD, cfg["subtitle2"], 56, W - 140)
    f_ti = f_l1 if f_l1.size <= f_l2.size else f_l2
    yo   = int((1-sa)*30)
    img  = put_ctxt(img, cfg["subtitle1"], 244, f_ti, WHITE, sa, yo)
    img  = put_ctxt(img, cfg["subtitle2"], 318, f_ti, WHITE, sa, yo)

    img = put_divider(img, 398, ease_out(phase(t, 1.5, 1.9)))

    # Bullets surgem 1.9..3.9s (cada 0.5s)
    bullets = cfg["bullets"]
    for i, b in enumerate(bullets):
        s0 = 1.9 + i * 0.5
        ba = ease_out(phase(t, s0, s0+0.45))
        f_b = fit_font(SANS, b, 34, W - 140)
        w_, _ = _tw(b, f_b)
        img = put_text(img, b, (W-w_)//2, 424+i*68+int((1-ba)*30), f_b, WHITE, ba)

    img = put_divider(img, 710, ease_out(phase(t, 3.9, 4.3)))

    # CTA pulsando 4.2..4.8s
    ca = ease_out(phase(t, 4.2, 4.8))
    img = put_badge(img, cfg["cta"], 736, 32, ca * pulse(t))

    # Site com glow cyan 4.7..5.2s
    sita = ease_out(phase(t, 4.7, 5.2))
    img = put_glow(img, "portaldoaluno.metodomeva.com.br",
                   826, fnt(SANS_BOLD,29), CYAN, sita, r=8)

    # @metodomeva com glow vermelho 5.0..5.5s
    ara = ease_out(phase(t, 5.0, 5.5))
    img = put_glow(img, "@metodomeva", 888, fnt(SANS_BOLD,36), RED, ara, r=12)

    return np.array(img.convert("RGB"))


def render_post5(t, cfg):
    img = Image.new("RGBA", (W, H), (*BG, 255))

    # Diagonais
    D = lyr(); d = ImageDraw.Draw(D)
    for i in range(-10, 30):
        x = i*80
        d.line([(x,0),(x+400,H)], fill=(20,20,20,255), width=1)
    img = put(img, D)

    img = put_border(img)
    img = put_footer(img)
    img = put_logo(img, ease_out(phase(t, 0.0, 0.5)))

    # Tag desliza da esquerda 0.3..0.8s
    tga = ease_out(phase(t, 0.3, 0.8))
    img = put_badge(img, "  POR QUE JAVA EM 2026?  ", 108, 28,
                    tga, xo=int((1-tga)*-320))

    img = put_divider(img, 162, ease_out(phase(t, 0.7, 1.0)))

    # Headline 3 linhas — fonte se ajusta para nunca cortar
    h1a = ease_out(phase(t, 0.8, 1.5))
    f_h1 = fit_font(SANS_BOLD, cfg["headline1"], 70, W - 140)
    img = put_glow(img, cfg["headline1"], 180, f_h1, WHITE,
                   h1a, yo=int((1-h1a)*50), r=8)

    h2a = ease_out(phase(t, 1.1, 1.8))
    f_h2 = fit_font(SANS_BOLD, cfg["headline2"], 70, W - 140)
    img = put_glow(img, cfg["headline2"], 264, f_h2, RED,
                   h2a, yo=int((1-h2a)*40), r=14)

    h3a = ease_out(phase(t, 1.4, 2.0))
    f_h3 = fit_font(SANS_BOLD, cfg["headline3"], 48, W - 140)
    img = put_ctxt(img, cfg["headline3"], 348, f_h3, WHITE,
                   h3a, yo=int((1-h3a)*30))

    img = put_divider(img, 414, ease_out(phase(t, 1.9, 2.2)))

    # Stats surgem um a um 2.2..4.2s (cada 0.5s)
    stats = cfg["stats"]
    for i, s in enumerate(stats):
        s0 = 2.2 + i*0.5
        sta = ease_out(phase(t, s0, s0+0.4))
        f_st = fit_font(SANS, s, 30, W - 140)
        sw, _ = _tw(s, f_st)
        img = put_text(img, s, (W-sw)//2, 440+i*66+int((1-sta)*28), f_st, WHITE, sta)

    img = put_divider(img, 718, ease_out(phase(t, 4.2, 4.5)))

    # CTA pulsando 4.4..5.0s
    ca = ease_out(phase(t, 4.4, 5.0))
    img = put_badge(img, cfg["cta"], 744, 32, ca * pulse(t))

    sita = ease_out(phase(t, 4.9, 5.4))
    img = put_glow(img, "portaldoaluno.metodomeva.com.br",
                   834, fnt(SANS_BOLD,29), CYAN, sita, r=8)

    ara = ease_out(phase(t, 5.2, 5.7))
    img = put_glow(img, "@metodomeva", 896, fnt(SANS_BOLD,36), RED, ara, r=12)

    return np.array(img.convert("RGB"))

def render_post6(t, cfg):
    """Renderiza o POST6 usando a mesma estrutura elegante do POST4."""
    return render_post4(t, cfg)


# ── Gerador de vídeo ──────────────────────────────────────────────────────────

CHARS_PER_S = 60   # 2 chars/frame @ 30fps

def video_duration(cfg):
    """Calcula duração necessária para o vídeo de código."""
    if cfg is None or "code" not in cfg:
        return 7.0
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
    
    # Adicionada a garantia do post6.mp4 no array de compactação
    entregaveis = ["post1.mp4","post2.mp4","post3.mp4","post4.mp4","post5.mp4","post6.mp4","legendas.txt"]
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in entregaveis:
            fp = f"{OUT_DIR}/{fn}"
            if os.path.exists(fp):
                z.write(fp, fn)
                
    kb_zip = os.path.getsize(zip_path) // 1024
    print(f"\n✅ Todos os arquivos salvos em: {OUT_DIR}/")
    print(f"📦 ZIP pronto: {zip_path}  ({kb_zip} KB)\n")
