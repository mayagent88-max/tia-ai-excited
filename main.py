#!/usr/bin/env python3
"""ai-excited-01 entry: a golden koi bursting out of its gilded frame.

Pure Python 3.13 standard library only. Fully deterministic: every run
writes byte-identical PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
Draws a bold flat-poster illustration with scanline polygon / ellipse fills
and a hand-rolled PNG encoder (struct + zlib).
"""
import math
import os
import random
import struct
import zlib

W = H = 1024
SEED = 20261116

# ---------------------------------------------------------------- canvas
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def fill_row(self, y, rgb):
        self.px[y * self.w * 3:(y + 1) * self.w * 3] = bytes(rgb) * self.w

    def hspan(self, y, x0, x1, rgb):
        if y < 0 or y >= self.h:
            return
        x0 = clamp(x0, 0, self.w - 1)
        x1 = clamp(x1, 0, self.w - 1)
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        self.px[i:(y * self.w + x1 + 1) * 3] = bytes(rgb) * (x1 - x0 + 1)

    def ellipse(self, cx, cy, rx, ry, rgb):
        if rx <= 0 or ry <= 0:
            return
        for yy in range(max(0, int(cy - ry)), min(self.h, int(cy + ry) + 1)):
            dy = (yy - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            self.hspan(yy, int(cx - dx), int(cx + dx), rgb)

    def circle(self, cx, cy, r, rgb):
        self.ellipse(cx, cy, r, r, rgb)

    def poly(self, pts, rgb):
        n = len(pts)
        if n < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)))
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            if len(xs) >= 2:
                xs.sort()
                for k in range(0, len(xs) - 1, 2):
                    self.hspan(y, int(xs[k]), int(xs[k + 1]), rgb)

    def thick_line(self, x1, y1, x2, y2, w, rgb):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length * w / 2.0, dx / length * w / 2.0
        self.poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                   (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], rgb)


def rot(pts, cx, cy, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s,
             cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def rect_corners(cx, cy, w, h, deg):
    hw, hh = w / 2.0, h / 2.0
    return rot([(cx - hw, cy - hh), (cx + hw, cy - hh),
                (cx + hw, cy + hh), (cx - hw, cy + hh)], cx, cy, deg)


# ---------------------------------------------------------------- font
# 5x7 bitmap glyphs, one word only: SPLASH!
FONT = {
    'S': ("01110", "10001", "10000", "01110", "00001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
}


def draw_text(cv, text, x, y, scale, rgb):
    for ch in text:
        glyph = FONT[ch]
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == '1':
                    for dy in range(scale):
                        cv.hspan(y + r * scale + dy,
                                 x + c * scale, x + (c + 1) * scale - 1, rgb)
        x += 6 * scale


# ---------------------------------------------------------------- palette
NAVY_TOP = (8, 20, 50)
NAVY_BOT = (16, 58, 96)
VIGNETTE = (3, 8, 24)
GOLD = (212, 158, 44)
GOLD_DARK = (140, 95, 25)
GOLD_BRIGHT = (255, 205, 60)
INDIGO = (24, 52, 110)
INDIGO_DEEP = (18, 40, 90)
BLUE_MID = (38, 84, 150)
FOAM = (245, 250, 255)
KOI = (228, 138, 28)
KOI_LIGHT = (255, 190, 90)
KOI_DARK = (195, 100, 18)
KOI_FIN = (250, 165, 55)
CYAN_PALE = (190, 230, 255)
CYAN_LIGHT = (150, 200, 240)
DARK = (8, 12, 30)
CRACK = (60, 35, 8)


def draw(cv):
    rng = random.Random(SEED)

    # --- background: vertical gradient, dark navy -> teal-blue
    for y in range(H):
        t = y / (H - 1)
        rgb = tuple(int(NAVY_TOP[i] + (NAVY_BOT[i] - NAVY_TOP[i]) * t)
                    for i in range(3))
        cv.fill_row(y, rgb)

    # --- vignette: dark ellipses in the corners (subtle, extreme corners only)
    cv.ellipse(-90, -90, 170, 170, VIGNETTE)
    cv.ellipse(W + 90, -90, 170, 170, VIGNETTE)
    cv.ellipse(-90, H + 90, 180, 180, VIGNETTE)
    cv.ellipse(W + 90, H + 90, 180, 180, VIGNETTE)

    # --- gold dust + tiny stars
    for _ in range(220):
        x = rng.uniform(0, W)
        y = rng.uniform(0, H)
        r = rng.choice([1, 1, 2, 2, 3])
        cv.circle(x, y, r, rng.choice([(255, 200, 60), (230, 170, 50),
                                       (255, 220, 110)]))
    for _ in range(40):
        cv.circle(rng.uniform(0, W), rng.uniform(0, H), 1, (220, 235, 255))

    # --- the framed painting (centre 560,470, tilted -8 degrees)
    fx, fy, fdeg = 560, 470, -8
    outer = rect_corners(fx, fy, 660, 660, fdeg)
    inner = rect_corners(fx, fy, 560, 560, fdeg)
    cv.poly(outer, GOLD)                      # outer gold slab
    cv.poly(inner, INDIGO)                    # painting area

    # --- ukiyo-e wave inside the painting (spill is covered by the border)
    cv.ellipse(560, 600, 300, 185, INDIGO_DEEP)
    cv.ellipse(500, 480, 280, 150, BLUE_MID)
    cv.ellipse(470, 445, 230, 110, INDIGO)
    # foam crest: a continuous curling band sweeping up-right, tapering
    crest = [(330, 540), (370, 500), (420, 465), (480, 435), (545, 415),
             (610, 400), (670, 395), (725, 400), (770, 415)]
    for i in range(len(crest) - 1):
        cv.thick_line(crest[i][0], crest[i][1], crest[i + 1][0],
                      crest[i + 1][1], 30 - i * 2, FOAM)
    for i, (cx, cy) in enumerate(crest):
        cv.circle(cx, cy, 22 - i, FOAM)
    cv.circle(790, 445, 9, FOAM)
    for _ in range(25):
        cv.circle(rng.uniform(360, 780), rng.uniform(400, 540),
                  rng.choice([2, 3]), FOAM)

    # --- frame border: 4 gold quads over the spill, + dark inner bevel
    bevel = rect_corners(fx, fy, 584, 584, fdeg)
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        cv.poly([outer[a], outer[b], inner[b], inner[a]], GOLD)
        cv.poly([inner[a], inner[b], bevel[b], bevel[a]], GOLD_DARK)

    # --- koi tail: two broad fan lobes at the tail end (stay inside frame)
    cv.poly([(340, 700), (270, 630), (205, 595), (270, 695), (330, 732)],
            (240, 150, 40))
    cv.poly([(335, 735), (270, 800), (245, 812), (295, 790), (340, 755)],
            (230, 130, 30))

    # --- koi body: tapered polygon along a diagonal spine
    tx0, ty0, tx1, ty1 = 330, 720, 845, 295
    dx, dy = tx1 - tx0, ty1 - ty0
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length          # spine direction
    nx, ny = -uy, ux                            # perpendicular (belly side)
    steps = 26

    def spine(t):
        return (tx0 + dx * t, ty0 + dy * t)

    def width(t):
        return 170.0 * (math.sin(math.pi * (0.12 + 0.76 * t)) ** 0.9)

    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        sx, sy = spine(t)
        w = width(t) / 2.0
        left.append((sx - nx * w, sy - ny * w))
        right.append((sx + nx * w, sy + ny * w))
    cv.poly(left + right[::-1], KOI)

    # belly band (pale gold, lower side)
    belly_l, belly_r = [], []
    for i in range(steps + 1):
        t = i / steps
        sx, sy = spine(t)
        w = width(t) / 2.0
        belly_l.append((sx + nx * w * 0.15, sy + ny * w * 0.15))
        belly_r.append((sx + nx * w * 0.95, sy + ny * w * 0.95))
    cv.poly(belly_l + belly_r[::-1], KOI_LIGHT)

    # scale dots (darker orange, sparser, upper half of the body)
    for i in range(4, steps, 2):
        t = i / steps
        sx, sy = spine(t)
        w = width(t) / 2.0
        for s in range(-3, 4):
            off = s * w / 4.0
            if abs(off) < w * 0.8:
                cv.circle(sx + nx * off, sy + ny * off, 7, KOI_DARK)

    # dark back stripe along the top edge
    back_l, back_r = [], []
    for i in range(steps + 1):
        t = i / steps
        sx, sy = spine(t)
        w = width(t) / 2.0
        back_l.append((sx - nx * w * 0.35, sy - ny * w * 0.35))
        back_r.append((sx - nx * w * 0.55, sy - ny * w * 0.55))
    cv.poly(back_l + back_r[::-1], (210, 110, 20))

    # dorsal fin: zigzag along the top edge
    fin = []
    for i in range(8, 20):
        t = i / 26.0
        sx, sy = spine(t)
        w = width(t) / 2.0
        fin.append((sx - nx * w * 0.5, sy - ny * w * 0.5))
        fin.append((sx - nx * w * 0.95, sy - ny * w * 0.95))
    cv.poly(fin, KOI_FIN)

    # pectoral fin, tucked under the body, angled back
    px, py = spine(0.62)
    pw = width(0.62) / 2.0
    cv.poly([(px + nx * pw * 0.3, py + ny * pw * 0.3),
             (px + nx * pw * 1.1, py + ny * pw * 0.8),
             (px + nx * pw * 0.9, py + ny * pw * 1.3),
             (px + nx * pw * 0.1, py + ny * pw * 0.9)], (255, 185, 95))

    # --- head: big eye, open mouth, barbels (head sits at the frame edge)
    cv.circle(828, 282, 26, (255, 255, 255))
    cv.circle(836, 286, 13, (20, 10, 5))
    cv.circle(820, 274, 6, (255, 255, 255))
    cv.ellipse(855, 305, 18, 11, (90, 25, 5))
    cv.thick_line(858, 312, 895, 345, 5, (255, 205, 120))
    cv.thick_line(848, 318, 868, 352, 5, (255, 205, 120))

    # --- crack at the breach point, drawn over the frame edge so it reads
    cv.thick_line(852, 340, 880, 302, 9, CRACK)
    cv.thick_line(880, 302, 862, 266, 8, CRACK)
    cv.thick_line(862, 266, 894, 238, 8, CRACK)
    cv.thick_line(856, 362, 890, 326, 8, CRACK)
    cv.thick_line(890, 326, 872, 298, 7, CRACK)

    # --- water explosion at the breach (880, 330): droplets fan up-right,
    # --- kept clear of the head so the eye and mouth stay visible
    bx, by = 880, 330
    for _ in range(45):
        ang = math.radians(rng.uniform(-100, 25))
        r = rng.uniform(40, 280)
        size = rng.uniform(3, 10)
        x = bx + math.cos(ang) * r
        y = by + math.sin(ang) * r
        col = rng.choice([(255, 255, 255), CYAN_PALE, CYAN_LIGHT])
        cv.ellipse(x, y, size * (1 + abs(math.cos(ang))),
                   size * (1 + abs(math.sin(ang))), col)
    for _ in range(4):
        cv.circle(bx + rng.uniform(-10, 70), by + rng.uniform(-10, 70),
                  rng.uniform(10, 16), (255, 255, 255))
    # motion streaks (up and right only, clear of the head)
    for ang_deg in (-60, -30, 0, -90, 20):
        a = math.radians(ang_deg)
        x2 = bx + math.cos(a) * rng.uniform(100, 160)
        y2 = by + math.sin(a) * rng.uniform(100, 160)
        cv.thick_line(bx, by, x2, y2, rng.choice([5, 6, 8]), (255, 255, 255))

    # --- gold frame shards flying out (up-right only, clear of the head)
    for _ in range(9):
        ang = math.radians(rng.uniform(-110, 20))
        r = rng.uniform(50, 210)
        cx = bx + math.cos(ang) * r
        cy = by + math.sin(ang) * r
        s = rng.uniform(10, 26)
        a2 = rng.uniform(0, 360)
        pts = [(cx + s * math.cos(math.radians(a2 + k * 120)),
                cy + s * math.sin(math.radians(a2 + k * 120))) for k in range(3)]
        cv.poly(pts, rng.choice([GOLD, GOLD_BRIGHT, GOLD_DARK]))

    # --- tiny museum guard, bottom-left, arms thrown up
    cv.ellipse(170, 935, 55, 14, (10, 20, 50))            # puddle
    cv.thick_line(160, 880, 155, 935, 10, DARK)            # legs
    cv.thick_line(180, 880, 185, 935, 10, DARK)
    cv.poly([(150, 815), (190, 815), (196, 885), (144, 885)], DARK)  # body
    cv.thick_line(155, 825, 120, 770, 9, DARK)             # raised arms
    cv.thick_line(185, 825, 220, 770, 9, DARK)
    cv.circle(170, 800, 13, DARK)                          # head

    # --- the word, top-left, gold with a dark shadow
    draw_text(cv, "SPLASH!", 65, 65, 11, (5, 12, 30))
    draw_text(cv, "SPLASH!", 60, 60, 11, GOLD_BRIGHT)


# ---------------------------------------------------------------- png
def chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += cv.px[y * W * 3:(y + 1) * W * 3]
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def main():
    cv = Canvas(W, H)
    draw(cv)
    data = encode_png(cv)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
