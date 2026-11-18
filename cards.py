"""Recto doodle cards: one fact, one hand-drawn object. Used by post.py for slides with an "art".

The drawings use the same hand as the doodles in the Recto app (assets/doodles): a felt
marker with round ends, slight wobble, four-point sparkles and motion lines. Every card has
its own object and composition; only the headline face, palette, logo and source line repeat.
Cards are drawn at 2x and scaled down so the strokes stay smooth.
"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS, ASSETS = os.path.join(HERE, "fonts"), os.path.join(HERE, "assets")
CREAM, INK, RED, PAPER = "#F9E4CA", "#3C0016", "#F92424", "#FFF4E6"
S = 2
W, H = 1080, 1350
THEMES = {  # bg, ink, accent, logo
    "stock": (CREAM, INK, RED, "recto-orange.png"),
    "ink": (INK, CREAM, RED, "recto-cream.png"),
    "signal": (RED, CREAM, INK, "recto-ink.png"),
}
DISPLAY = "GCCommune.otf" if os.path.exists(os.path.join(FONTS, "GCCommune.otf")) else "LibreBaskerville-Bold.ttf"


def F(name, size): return ImageFont.truetype(os.path.join(FONTS, name), int(size * S))
def disp(s): return F(DISPLAY, s)
def serif(s): return F("LibreBaskerville-Regular.ttf", s)
def bold(s): return F("LibreBaskerville-Bold.ttf", s)   # figures: GC Commune's 1 reads as an l


class Pen:
    """A felt marker: wobbly, round-capped strokes like the doodles in the Recto app."""
    def __init__(self, d, color, w=10, seed=1):
        self.d, self.c, self.w = d, color, w * S
        self.r = random.Random(seed)

    def jit(self, p, amt):
        return (p[0] + self.r.uniform(-amt, amt), p[1] + self.r.uniform(-amt, amt))

    def _dots(self, pts, w):
        for p in pts:
            self.d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=self.c)

    def line(self, pts, w=None, wobble=2.5):
        """Freeform stroke through pts, smoothed (Catmull-Rom)."""
        w = w or self.w
        pts = [self.jit((x * S, y * S), wobble * S) for x, y in pts]
        P = [pts[0]] + pts + [pts[-1]]
        dense = []
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            for k in range(10):
                t = k / 10
                dense.append(tuple(0.5 * (2 * p1[j] + (p2[j] - p0[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                          + (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
        dense.append(P[-2])
        self.d.line(dense, fill=self.c, width=int(w), joint="curve")
        self._dots((dense[0], dense[-1]), w)

    def poly(self, pts, w=None, wobble=2.2, fill=None):
        """Closed shape with crisp corners: each edge a hand-drawn straight line."""
        w = w or self.w
        if fill:
            self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill)
        dense = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            for t in (0, .33, .66):
                dense.append(self.jit(((a[0] + (b[0] - a[0]) * t) * S, (a[1] + (b[1] - a[1]) * t) * S), wobble * S * (t > 0)))
        dense.append(dense[0])
        self.d.line(dense, fill=self.c, width=int(w), joint="curve")
        self._dots(dense[::3], w)

    def seg(self, a, b, w=None, wobble=1.5):
        self.line([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), b], w=w, wobble=wobble)

    def ring(self, cx, cy, rx, ry=None, w=None, fill=None, start=0, end=360):
        ry = ry or rx
        if fill:
            self.d.ellipse(((cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S), fill=fill)
        n = max(8, int((end - start) / 22))
        pts = [(cx + rx * math.cos(math.radians(start + (end - start) * i / n)),
                cy + ry * math.sin(math.radians(start + (end - start) * i / n))) for i in range(n + 1)]
        self.line(pts, w=w, wobble=1.2)

    def sparkle(self, x, y, r=28):
        pts = []
        for i in range(8):
            a = math.pi / 4 * i - math.pi / 2
            rr = r if i % 2 == 0 else r * .28
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        self.poly(pts, w=self.w * .55, wobble=.5)

    def motion(self, x, y, angle=0, length=60, n=3, gap=20):
        for i in range(n):
            ox, oy = -math.sin(angle) * gap * i, math.cos(angle) * gap * i
            l = length * (1 - .25 * i)
            self.seg((x + ox, y + oy), (x + ox + l * math.cos(angle), y + oy + l * math.sin(angle)), w=self.w * .6)

    def page(self, x, y, w, h, tilt=0, lines=5, fill=PAPER):
        cx, cy = x + w / 2, y + h / 2
        def rot(px, py):
            dx, dy = px - cx, py - cy
            return (cx + dx * math.cos(tilt) - dy * math.sin(tilt), cy + dx * math.sin(tilt) + dy * math.cos(tilt))
        self.poly([rot(x, y), rot(x + w, y), rot(x + w, y + h), rot(x, y + h)], fill=fill)
        for i in range(lines):
            ly = y + h * .2 + i * h * .12
            lw = w * (.45 if i == 0 else .62 if i % 3 else .5)
            self.seg(rot(x + w * .18, ly), rot(x + w * .18 + lw, ly), w=self.w * .8)


class Card:
    def __init__(self, slide, post):
        self.s = slide
        self.bg, self.ink, self.acc, self.logo = THEMES[slide.get("color", post.get("color", "stock"))]
        self.img = Image.new("RGB", (W * S, H * S), self.bg)
        self.d = ImageDraw.Draw(self.img)

    def pen(self, color=None, w=10, seed=1):
        return Pen(self.d, color or self.ink, w, seed)

    def text(self, xy, s, font, fill=None, anchor="la", spacing=10, align="left"):
        self.d.multiline_text((xy[0] * S, xy[1] * S), s, font=font, fill=fill or self.ink, anchor=anchor,
                              spacing=spacing * S, align=align)

    def title(self, y=96, size=104, x=84, fill=None):
        t = self.s["title"]
        while size > 56 and max(self.d.textlength(l, font=disp(size)) for l in t.split("\n")) > (W - 2 * x) * S:
            size -= 2
        self.text((x, y), t, disp(size), fill, "la", int(size * .2))

    def sub(self, y, size=28, fill=None, x=84):
        if self.s.get("sub"):
            self.text((x, y), self.s["sub"], serif(size), fill, "la", 12)

    def big(self, xy, s, size, fill=None, anchor="la"):
        self.text(xy, s, bold(size), fill, anchor)

    def footer(self):
        l = Image.open(os.path.join(ASSETS, self.logo)).convert("RGBA")
        l = l.resize((int(l.width * 36 * S / l.height), 36 * S))
        self.img.paste(l, (84 * S, (H - 84 - 36) * S), l)
        if self.s.get("source"):
            self.text((W - 84, H - 88), ("Source: " + self.s["source"]).upper(), bold(18), anchor="rd")

    def doodle(self, name, x, y, h, color=None, angle=0):
        """One of Recto's own doodles (make, page, read, send), tinted."""
        im = Image.open(os.path.join(ASSETS, "doodles", f"{name}.png")).convert("RGBA")
        im = im.resize((int(im.width * h * S / im.height), int(h * S)))
        tint = Image.new("RGBA", im.size, color or self.acc)
        tint.putalpha(im.split()[3])
        if angle:
            tint = tint.rotate(angle, expand=True, resample=Image.BICUBIC)
        self.img.paste(tint, (int(x * S), int(y * S)), tint)

    def render(self):
        getattr(self, "art_" + self.s["art"])()
        self.footer()
        return self.img.resize((W, H), Image.LANCZOS)

    # ------------------------------------------------------------------ the drawings
    def art_pages(self):
        self.title()
        p, r = self.pen(w=9, seed=3), self.pen(self.acc, 10, seed=8)
        for i in range(10):
            p.page(110 + i * 4, 560 - i * 12, 330, 440, tilt=-0.03 + i * .005, lines=0)
        p.page(150, 430, 330, 440, lines=6)
        r.page(560, 440, 250, 330, tilt=0.30)
        r.page(780, 590, 250, 330, tilt=0.58)
        r.motion(500, 520, angle=0.2, length=70)
        r.sparkle(940, 470, 30)
        self.sub(1100)

    def art_reading(self):
        self.title()
        p, r = self.pen(PAPER if self.bg == INK else self.ink, 9, seed=4), self.pen(self.acc, 11, seed=5)
        x, y, w, h = 400, 400, 480, 660
        q = self.pen(INK, 9, seed=4)
        q.page(x, y, w, h, lines=0)
        for i in range(4):
            q.seg((x + 60, y + 80 + i * 40), (x + w - 60 - (i % 2) * 90, y + 80 + i * 40), w=q.w * .8)
        r.poly([(x + 36, y + 40), (x + w - 30, y + 46), (x + w - 36, y + 270), (x + 34, y + 266)], w=r.w * .8)
        for i in range(3):
            q.seg((x + 60, y + 330 + i * 34), (x + w - 160, y + 330 + i * 34), w=q.w * .6)
        r.ring(x + w / 2, y + 540, 200, 70)
        q.seg((x + 120, y + 540), (x + w - 120, y + 540), w=q.w * .8)
        self.big((x - 40, y + 150), "38.2%", 60, self.acc, "rm")
        self.text((x - 40, y + 196), "on the intro", serif(26), anchor="ra")
        self.big((x - 40, y + 520), "27%", 60, self.acc, "rm")
        self.text((x - 40, y + 566), "on the price", serif(26), anchor="ra")
        r.sparkle(x + w + 60, y + 20, 28)
        self.sub(1110)

    def art_envelopes(self):
        self.title()
        a, b = self.pen(self.acc, 4, seed=6), self.pen(self.ink, 3, seed=7)
        for i in range(100):
            cx, cy = 84 + (i % 10) * 64, 420 + (i // 10) * 64
            pen = a if i < 29 else b
            pen.poly([(cx, cy), (cx + 50, cy), (cx + 50, cy + 36), (cx, cy + 36)], wobble=.8)
            pen.line([(cx, cy), (cx + 25, cy + 20), (cx + 50, cy)], wobble=.6)
        self.big((W - 84, 410), "29%", 120, self.acc, "ra")
        self.text((W - 84, 580), "of freelance\ninvoices are\npaid at least\na day late.", serif(28), anchor="ra", align="right")
        self.sub(1100)

    def art_stopwatch(self):
        self.title()
        p, r, q = self.pen(self.ink, 12, seed=9), self.pen(self.acc, 22, seed=10), self.pen(INK, 22, seed=11)
        cx, cy, rad = 540, 790, 270
        p.ring(cx, cy, rad, fill=PAPER)
        p.poly([(cx - 40, cy - rad - 70), (cx + 40, cy - rad - 70), (cx + 40, cy - rad - 20), (cx - 40, cy - rad - 20)])
        p.seg((cx + rad * .72, cy - rad * .78), (cx + rad * .86, cy - rad * .94))
        r.ring(cx, cy, rad - 42, start=-90, end=-90 + 360 * 25.3 / 30)
        q.ring(cx, cy, rad - 88, start=-90, end=-90 + 360 * 15.8 / 30)
        self.big((cx, cy + 30), "25.3", 76, RED, "ms")
        self.text((cx, cy + 60), "min", serif(28), INK, "ma")
        self.text((cx, cy + rad + 40), "25.3 minutes on proposals they sign. 15.8 on the ones they don't.", serif(26), anchor="ma")
        p.motion(cx + rad + 40, cy - 80, angle=-.3)
        self.sub(1180, 26)

    def art_plane(self):
        self.title()
        p = self.pen(self.ink, 6, seed=12)
        stops = [(150, 960), (520, 760), (900, 600)]
        for a, b in zip(stops, stops[1:]):
            for t in range(0, 10, 2):
                s0, s1 = t / 10, (t + 1) / 10
                p.seg((a[0] + (b[0] - a[0]) * s0, a[1] + (b[1] - a[1]) * s0 - 40 * math.sin(math.pi * s0)),
                      (a[0] + (b[0] - a[0]) * s1, a[1] + (b[1] - a[1]) * s1 - 40 * math.sin(math.pi * s1)))
        for (x, y), (v, n) in zip(stops, [("17 min", "to make"), ("34 min", "to open"), ("2.5 days", "to sign")]):
            last = n == "to sign"
            p.ring(x, y, 16, fill=self.acc if last else self.ink)
            anchor = "ra" if last else "ma"
            self.big((x + (40 if last else 0), y + 40), v, 46, self.acc if last else self.ink, anchor)
            self.text((x + (40 if last else 0), y + 100), n, serif(26), anchor=anchor)
        self.doodle("send", 780, 400, 140, self.acc, angle=8)
        self.sub(1150, 26)

    def art_printer(self):
        self.title()
        p, r = self.pen(self.ink, 11, seed=13), self.pen(self.acc, 12, seed=14)
        p.poly([(110, 640), (650, 640), (650, 880), (110, 880)], fill=self.bg)
        p.poly([(190, 520), (570, 520), (570, 640), (190, 640)])
        p.seg((150, 700), (230, 700))
        q = self.pen(INK, 8, seed=15)
        q.page(190, 840, 380, 280, lines=4)
        r.seg((290, 900), (470, 1060), w=r.w * 1.3)
        r.seg((470, 900), (290, 1060), w=r.w * 1.3)
        self.big((W - 84, 560), "84%", 130, self.acc, "ra")
        self.text((W - 84, 720), "less likely\nto win once\nit's printed.", serif(30), anchor="ra", align="right")
        r.sparkle(960, 470, 28)

    def art_invoice(self):
        self.title()
        p, r = self.pen(INK, 8, seed=15), self.pen(self.acc, 12, seed=16)
        x0, x1, y0, y1 = 110, 540, 410, 1130
        zig = [(x1 - i * 43, y1 + (14 if i % 2 else 0)) for i in range(11)]
        p.poly([(x0, y0), (x1, y0)] + zig, fill=PAPER)
        self.text((x0 + 40, y0 + 40), "INVOICE", bold(26), INK)
        for i in range(6):
            p.seg((x0 + 40, y0 + 130 + i * 66), (x0 + 190 + (i % 3) * 30, y0 + 130 + i * 66), w=p.w * .7)
            p.seg((x1 - 110, y0 + 130 + i * 66), (x1 - 40, y0 + 130 + i * 66), w=p.w * .7)
        p.seg((x0 + 40, y0 + 540), (x1 - 40, y0 + 540))
        self.text((x1 - 40, y0 + 570), "$22,300", bold(44), INK, "ra")
        st = Image.new("RGBA", (420 * S, 120 * S), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((6 * S, 6 * S, 414 * S, 114 * S), radius=24 * S, outline=RED, width=8 * S)
        sd.text((210 * S, 60 * S), "OVERDUE", font=bold(56), fill=RED, anchor="mm")
        st = st.rotate(14, expand=True, resample=Image.BICUBIC)
        self.img.paste(st, (150 * S, 700 * S), st)
        self.big((W - 84, 450), "3×", 150, self.acc, "ra")
        self.text((W - 84, 640), "more likely\nto be paid late\nthan an invoice\nunder $100.", serif(28), anchor="ra", align="right")
        r.sparkle(960, 1020, 30)

    def art_quote(self):
        r = self.pen(self.acc, 16, seed=17)
        self.text((70, 120), "\u201c", bold(380), self.acc)
        self.text((84, 400), self.s["quote"], serif(66), spacing=22)
        r.seg((84, 990), (360, 990), w=r.w * .4)
        self.text((84, 1020), self.s["sub"], serif(26), spacing=10)

    def art_chairs(self):
        self.title()
        p, r = self.pen(self.ink, 7, seed=18), self.pen(self.acc, 7, seed=19)
        def chair(pen, x, y, s):
            pen.seg((x, y), (x, y + s))
            pen.seg((x, y + s * .6), (x + s * .62, y + s * .6))
            pen.seg((x + s * .62, y + s * .6), (x + s * .62, y + s))
        for i in range(18):
            chair(p if i < 11 else r, 120 + (i % 6) * 150, 430 + (i // 6) * 180, 120)
        self.big((84, 990), "11", 100, self.ink)
        self.text((84, 1120), "people to win a pitch", serif(28))
        self.big((W - 84, 990), "18", 100, self.acc, "ra")
        self.text((W - 84, 1120), "to defend an account", serif(28), self.acc, "ra")

    def art_coins(self):
        self.title()
        r, p = self.pen(self.acc, 7, seed=20), self.pen(self.ink, 7, seed=21)
        for x, n, pen in ((300, 15, r), (760, 7, p)):
            for i in range(n):
                pen.ring(x, 1070 - i * 34, 130, 26, fill=self.bg)
        self.big((300, 480), "$406,092", 56, self.acc, "ms")
        self.text((300, 500), "to defend an account", serif(26), anchor="ma")
        self.big((760, 760), "$204,461", 56, self.ink, "ms")
        self.text((760, 780), "to win one from outside", serif(26), anchor="ma")
        r.sparkle(520, 420, 28)

    def art_jars(self):
        self.title(size=112)
        def jar(pen, x, y, s):
            pen.poly([(x, y + s * .2), (x + s * .1, y + s), (x + s * .9, y + s), (x + s, y + s * .2)])
            pen.seg((x - s * .05, y + s * .05), (x + s * 1.05, y + s * .05), w=pen.w * 1.3)
            pen.seg((x + s * .25, y + s * .55), (x + s * .75, y + s * .55), w=pen.w * .7)
        c = self.pen(self.ink, 5, seed=11)
        for i in range(24):
            jar(c, 84 + (i % 12) * 78, 420 + (i // 12) * 96, 52)
        self.text((84, 640), "24 jams on the table:  3% bought.", serif(30))
        rp = self.pen(self.acc, 11, seed=12)
        for i in range(6):
            jar(rp, 90 + i * 155, 760, 118)
        rp.sparkle(1000, 730, 30)
        self.text((84, 940), "6 jams on the table:  30% bought.", serif(30), self.acc)
        self.text((84, 1040), "Offer three packages, not seven.", bold(30))

    def art_snail(self):
        self.title()
        p, r = self.pen(self.ink, 10, seed=22), self.pen(self.acc, 9, seed=23)
        cx, cy = 520, 800
        p.line([(cx + (12 + 10 * t) * math.cos(t), cy + (12 + 10 * t) * math.sin(t)) for t in [i * .35 for i in range(48)]], wobble=1)
        p.line([(cx - 250, cy + 185), (cx - 60, cy + 185), (cx + 180, cy + 185), (cx + 300, cy + 170), (cx + 350, cy + 100), (cx + 330, cy + 40)])
        p.seg((cx + 330, cy + 40), (cx + 345, cy - 50))
        p.seg((cx + 300, cy + 45), (cx + 270, cy - 40))
        p.ring(cx + 345, cy - 58, 9, fill=self.ink)
        p.ring(cx + 270, cy - 48, 9, fill=self.ink)
        r.page(cx - 90, cy - 340, 150, 190, tilt=-.2, lines=3)
        r.motion(cx - 330, cy + 130, angle=math.pi, length=50)
        self.big((W - 84, 440), "6 days", 60, self.acc, "ra")
        self.text((W - 84, 520), "to sign, sent within\na day of the meeting", serif(26), anchor="ra", align="right")
        self.big((84, 1050), "12 days", 60)
        self.text((84, 1130), "when it waits three or four", serif(26))

    def art_tag(self):
        self.title()
        r, p = self.pen(self.acc, 12, seed=24), self.pen(self.ink, 8, seed=25)
        r.poly([(300, 560), (780, 520), (860, 770), (400, 1010), (250, 830)], fill=self.acc)
        r.ring(330, 640, 22, fill=self.bg)
        p.line([(330, 640), (260, 560), (200, 470), (230, 420)])
        self.text((530, 730), "62%", bold(130), CREAM, "mm")
        self.text((530, 820), "named price first", serif(28), CREAM, "mm")
        self.text((84, 1080), "Creative execution 45%.  The big idea 36%.  Reputation 35%.", serif(26))

    def art_coin(self):
        self.title()
        r = self.pen(self.acc, 12, seed=26)
        r.ring(620, 760, 220, fill=self.acc)
        r.ring(620, 760, 175, w=r.w * .6)
        self.text((620, 760), "71%", bold(120), CREAM, "mm")
        r.motion(330, 680, angle=math.pi, length=110, gap=34)
        r.sparkle(880, 520, 34)
        self.sub(1080)

    def art_note(self):
        self.title()
        p, r = self.pen(INK, 8, seed=27), self.pen(INK, 10, seed=28)
        p.poly([(120, 460), (560, 430), (590, 860), (150, 890)], fill="#FFE07A")
        self.text((190, 530), "Pay the\ninvoice", serif(60), INK, spacing=14)
        r.ring(340, 450, 24, fill=INK)
        p.seg((190, 770), (500, 752), w=p.w * .7)
        self.big((W - 84, 460), "90%", 130, self.ink, "ra")
        self.text((W - 84, 620), "of late invoices\nare paid within\na month of the\ndue date.", serif(28), anchor="ra", align="right")
        self.sub(1000)

    def art_signature(self):
        self.title(size=120)
        sg = self.pen(self.acc, 15, seed=31)
        pts = [(130 + t * 30 - 46 * math.sin(t), 760 - 70 * math.cos(t) - 40 * math.sin(t / 3.1))
               for t in [i / 119 * 7.4 * math.pi for i in range(120)]]
        sg.line(pts, wobble=1.5)
        sg.seg((110, 900), (900, 886), w=sg.w * .5)
        self.doodle("make", pts[-1][0] - 30, pts[-1][1] - 220, 240, self.ink)
        sg.sparkle(120, 600, 30)
        self.big((84, 960), "+65%", 120, self.ink)
        self.text((84, 1110), "close rate when the sender\nsigned before sending.", serif(28))

    def art_list(self):
        self.title()
        r, p = self.pen(self.acc, 7, seed=32), self.pen(self.ink, 7, seed=33)
        for i, it in enumerate(["The problem", "The approach", "Scope", "Timeline", "Proof", "Price", "Next step"]):
            y = 440 + i * 92
            r.ring(130, y + 26, 32)
            self.text((130, y + 28), str(i + 1), bold(30), self.acc, "mm")
            self.text((196, y + 26), it, serif(42), anchor="lm")
            p.line([(850, y + 26), (872, y + 46), (920, y)], wobble=1)
        r.sparkle(980, 420, 28)

    def art_glasses(self):
        self.big((540, 780), "12", 560, CREAM if self.bg == RED else self.acc, "mm")
        g = self.pen(INK, 13, seed=5)
        g.line([(250, 420), (330, 410), (420, 416), (540, 424), (660, 416), (760, 412), (830, 425)])
        g.ring(405, 480, 78, 66)
        g.ring(680, 482, 78, 66)
        g.line([(830, 425), (870, 400), (910, 412)])
        g.sparkle(230, 350, 34)
        g.motion(890, 350, angle=-0.6, length=60)
        self.title(size=96, fill=INK)
        self.sub(1110, fill=INK)

    def art_speech(self):
        self.title()
        p, r = self.pen(self.ink, 11, seed=34), self.pen(self.acc, 14, seed=35)
        p.poly([(130, 420), (950, 400), (960, 860), (420, 880), (300, 1000), (320, 880), (120, 870)], fill=PAPER)
        for i, t in enumerate(["7% words", "38% voice", "55% body"]):
            y = 540 + i * 100
            self.text((545, y), t, bold(56), INK, "mm")
            half = self.d.textlength(t, font=bold(56)) / S / 2
            r.seg((545 - half - 20, y + 4), (545 + half + 20, y - 2), w=r.w * .6)
        self.sub(1050, 26)

    def art_calendar(self):
        self.title(size=92)
        k, red = self.pen(self.ink, 8, seed=21), self.pen(self.acc, 7, seed=22)
        q = self.pen(INK, 8, seed=21)
        q.page(110, 500, 860, 560, lines=0)
        for i in range(3):
            k.seg((260 + i * 280, 470), (262 + i * 280, 540), w=k.w * 1.4)
        for i in range(20):
            cx, cy = 180 + (i % 5) * 160, 590 + (i // 5) * 112
            red.seg((cx, cy), (cx + 80, cy + 62), wobble=3)
            red.seg((cx + 78, cy + 2), (cx + 4, cy + 60), wobble=3)
        red.sparkle(970, 470, 30)
        self.sub(1110)

    def art_hourglass(self):
        self.title()
        for i, (v, n, share, c) in enumerate([("31%", "women", .31, self.acc), ("24%", "men", .24, self.ink), ("23%", "studios", .23, self.ink)]):
            x = 220 + i * 320
            p = self.pen(c, 8, seed=40 + i)
            p.seg((x - 90, 470), (x + 90, 470), w=p.w * 1.3)
            p.seg((x - 90, 900), (x + 90, 900), w=p.w * 1.3)
            p.line([(x - 70, 475), (x - 60, 600), (x - 8, 685), (x - 60, 770), (x - 70, 895)])
            p.line([(x + 70, 475), (x + 60, 600), (x + 8, 685), (x + 60, 770), (x + 70, 895)])
            h = 200 * share * 2.2
            self.d.polygon([((x - 8) * S, 682 * S), ((x + 8) * S, 682 * S), ((x + 8 + h * .3) * S, (682 - h) * S), ((x - 8 - h * .3) * S, (682 - h) * S)], fill=c)
            self.d.polygon([((x - 60) * S, 892 * S), ((x + 60) * S, 892 * S), (x * S, (892 - h * .8) * S)], fill=c)
            self.big((x, 950), v, 64, c, "ma")
            self.text((x, 1040), n, serif(28), anchor="ma")
        self.sub(1120, 26)

    def art_phone(self):
        self.title()
        p, r = self.pen(self.ink, 12, seed=50), self.pen(self.acc, 10, seed=51)
        p.poly([(580, 420), (920, 430), (910, 1130), (570, 1120)], fill=self.bg)
        p.seg((700, 460), (800, 462))
        q = self.pen(INK, 8, seed=52)
        q.page(620, 540, 250, 350, tilt=.05, lines=6)
        r.motion(480, 660, angle=0, length=60)
        self.big((84, 470), "37.7%", 100, self.acc)
        self.text((84, 620), "of proposals\nwere first\nopened on\na phone.", serif(32), spacing=12)
        r.sparkle(980, 390, 28)

    def art_loop(self):
        self.title()
        p = self.pen(self.ink, 16, seed=52)
        p.ring(540, 790, 290, start=-60, end=250)
        ax, ay = 540 + 290 * math.cos(math.radians(250)), 790 + 290 * math.sin(math.radians(250))
        p.seg((ax, ay), (ax + 70, ay - 10))
        p.seg((ax, ay), (ax + 20, ay + 70))
        self.big((540, 770), "+28.5%", 100, anchor="mm")
        self.text((540, 860), "monthly fees sold for more", serif(28), anchor="mm")
        self.text((540, 1150), "One-off fees: +16.3%", serif(28), anchor="mm")

    def art_juggle(self):
        self.title()
        p, r = self.pen(self.ink, 10, seed=53), self.pen(self.acc, 10, seed=54)
        for x, y in [(220, 470), (420, 430), (640, 430), (840, 470)]:
            p.ring(x, y, 62, fill=self.ink)
        for x, y in [(260, 930), (540, 1000), (820, 910)]:
            r.ring(x, y, 62)
            r.motion(x - 20, y - 150, angle=math.pi / 2, length=60, gap=20)
        self.big((84, 600), "4", 120)
        self.text((180, 650), "chunks we can hold (Cowan, 2001)", serif(28))
        self.text((84, 1110), "Miller's famous seven (1956) is three too many.", serif(28), self.acc)

    def art_table(self):
        self.title()
        p, r = self.pen(self.ink, 6, seed=55), self.pen(self.acc, 10, seed=56)
        y = 440
        for name, amt in [("Brand workshop", "$2,400"), ("Logo and identity", "$6,000"), ("Social templates × 12", "$1,800"), ("Revision rounds × 3", "$1,200")]:
            self.text((110, y), name, serif(34))
            self.text((970, y), amt, serif(34), anchor="ra")
            p.seg((110, y + 62), (970, y + 60), w=p.w * .7)
            y += 100
        self.text((110, y + 40), "Total", bold(34))
        self.text((970, y + 20), "$11,400", bold(80), self.acc, "ra")
        r.ring(800, y + 70, 220, 80)
        self.doodle("make", 250, y - 20, 110, self.acc, angle=-20)
        self.sub(1130)


def render(slide, post):
    if not hasattr(Card, "art_" + slide["art"]):
        raise SystemExit(f"Unknown art {slide['art']!r}.")
    return Card(slide, post).render()
