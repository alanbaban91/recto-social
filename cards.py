"""Recto data cards: one fact, one shape. Used by post.py for slides that carry a "layout".

Every card shares the same frame (territory label, context, hairlines, headline in the logo
face, logo and source in the footer). Only the shape in the middle changes, and every shape
is drawn from paper: pages, spreads, contents pages, invoices, pricing tables, calendars.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS, ASSETS = os.path.join(HERE, "fonts"), os.path.join(HERE, "assets")
W, H, M = 1080, 1350, 84
CREAM, INK, RED = "#F9E4CA", "#3C0016", "#F92424"
THEMES = {  # bg, ink, accent, faint (lines and empty shapes), logo, muted (faded but readable text)
    "stock": (CREAM, INK, RED, "#D9C2A5", "recto-orange.png", "#8A7F6E"),
    "ink": (INK, CREAM, RED, "#6B3A47", "recto-cream.png", "#B89A94"),
    "signal": (RED, CREAM, INK, "#FB7A6E", "recto-cream.png", "#FFD2C7"),
}
DISPLAY = "GCCommune.otf" if os.path.exists(os.path.join(FONTS, "GCCommune.otf")) else "LibreBaskerville-Bold.ttf"


def F(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)

def disp(s): return F(DISPLAY, s)
def serif(s): return F("LibreBaskerville-Regular.ttf", s)
def bold(s): return F("LibreBaskerville-Bold.ttf", s)
def num(s): return F("LibreBaskerville-Bold.ttf", s)   # GC Commune's 1 reads as l, so figures stay in Baskerville


def width(d, text, font):
    return d.textlength(text, font=font)


def fit_lines(d, text, maker, big, small, max_w):
    """Largest size from big to small where every line of text fits max_w."""
    for size in range(big, small - 1, -2):
        f = maker(size)
        if all(width(d, line, f) <= max_w for line in text.split("\n")):
            return f, size
    return maker(small), small


class Card:
    def __init__(self, slide, post):
        self.s = slide
        self.bg, self.ink, self.acc, self.faint, self.logo, self.muted = THEMES[slide.get("color", post.get("color", "stock"))]
        self.img = Image.new("RGB", (W, H), self.bg)
        self.d = ImageDraw.Draw(self.img)
        self.frame(post.get("kicker", ""), slide.get("context", ""), slide.get("source", ""))
        self.top = self.headline(slide.get("title", ""), slide.get("title_max", 112))

    def frame(self, kicker, context, source):
        d, f = self.d, bold(22)
        d.text((M, M), kicker.upper(), font=f, fill=self.acc)
        d.text((W - M, M), context.upper(), font=f, fill=self.ink, anchor="ra")
        d.line((M, M + 44, W - M, M + 44), fill=self.ink, width=2)
        d.line((M, H - 150, W - M, H - 150), fill=self.ink, width=2)
        logo = Image.open(os.path.join(ASSETS, self.logo)).convert("RGBA")
        logo = logo.resize((int(logo.width * 40 / logo.height), 40))
        self.img.paste(logo, (M, H - 120), logo)
        if source:
            d.text((W - M, H - 112), ("Source: " + source).upper(), font=bold(20), fill=self.ink, anchor="ra")

    def headline(self, text, big):
        if not text:
            return M + 90
        f, size = fit_lines(self.d, text, disp, big, 56, W - 2 * M)
        self.d.multiline_text((M, M + 92), text, font=f, fill=self.ink, spacing=int(size * 0.08))
        box = self.d.multiline_textbbox((M, M + 92), text, font=f, spacing=int(size * 0.08))
        return box[3]

    # The body area every shape draws inside.
    @property
    def area(self):
        return M, self.top + 70, W - M, H - 200

    # ---- shared brand shapes ----
    def page(self, x0, y0, x1, y1, fill=None, outline=None, ear=None, w=3):
        """A sheet with its top-right corner folded: the recto is the right-hand page."""
        ear = ear if ear is not None else int((x1 - x0) * 0.22)
        pts = [(x0, y0), (x1 - ear, y0), (x1, y0 + ear), (x1, y1), (x0, y1)]
        self.d.polygon(pts, fill=fill, outline=outline, width=w if outline else 0)
        fold = [(x1 - ear, y0), (x1 - ear, y0 + ear), (x1, y0 + ear)]
        self.d.polygon(fold, fill=self.bg if fill else None, outline=outline or self.bg, width=w)
        if fill and not outline:
            self.d.line(fold[:2] + fold[2:], fill=self.bg, width=w)

    def big(self, xy, text, size, fill, anchor="la"):
        self.d.text(xy, text, font=num(size), fill=fill, anchor=anchor)

    def small(self, xy, text, fill=None, anchor="la", size=28):
        self.d.text(xy, text, font=serif(size), fill=fill or self.ink, anchor=anchor)

    def label(self, xy, text, fill=None, anchor="la", size=22):
        self.d.text(xy, text.upper(), font=bold(size), fill=fill or self.ink, anchor=anchor)

    # ---- layouts ----
    def count(self):
        """n pages in a row; the last k are the ones that cost you."""
        s, (x0, y0, x1, y1) = self.s, self.area
        n, k = s["n"], s["k"]
        gap = 14 if n <= 14 else 8
        pw = (x1 - x0 - gap * (n - 1)) / n
        ph = min(pw * 1.414, 150)
        y = y0 + max(10, ((y1 - y0) - (ph + 300)) / 2)
        for i in range(n):
            px = x0 + i * (pw + gap)
            if i < n - k:
                self.page(px, y, px + pw, y + ph, fill=self.ink, ear=int(pw * .3))
            else:
                self.page(px, y, px + pw, y + ph, outline=self.acc, ear=int(pw * .3), w=4)
        yb = y + ph + 40
        self.big((x0, yb), s["left"], 150, self.ink)
        self.big((x1, yb), s["right"], 150, self.acc, "ra")
        self.small((x0, yb + 200), s["left_label"])
        self.small((x1, yb + 200), s["right_label"], self.acc, "ra")

    def chart(self):
        """One A4 sheet cut into bands at the real proportions."""
        s, (x0, y0, x1, y1) = self.s, self.area
        ph = y1 - y0
        pw = int(ph / 1.414)
        px = (W - pw) // 2
        y = y0
        fills = [self.ink, self.acc, self.bg]
        texts = [self.bg, self.bg if self.bg != RED else CREAM, self.ink]
        if self.bg == INK:
            fills, texts = [CREAM, RED, INK], [INK, CREAM, CREAM]
        for i, (value, name, share) in enumerate(s["bands"]):
            h = ph * share
            self.d.rectangle((px, y, px + pw, y + h), fill=fills[i % 3])
            self.label((px + 40, y + 30), name, texts[i % 3])
            self.big((px + 36, y + h - 28), value, min(104, int(h * .55)), texts[i % 3], "ld")
            y += h
        self.d.rectangle((px, y0, px + pw, y1), outline=self.ink, width=3)
        ear = int(pw * .14)
        self.d.polygon([(px + pw - ear, y0), (px + pw, y0), (px + pw, y0 + ear)], fill=self.bg)
        self.d.line((px + pw - ear, y0, px + pw - ear, y0 + ear, px + pw, y0 + ear), fill=self.ink, width=3)

    def versus(self):
        """Rows of page-width bars; the longest is a full line of type."""
        s, (x0, y0, x1, y1) = self.s, self.area
        rows = s["rows"]
        top = max(r[2] for r in rows)
        step = (y1 - y0) / len(rows)
        for i, (value, name, amount) in enumerate(rows):
            y = y0 + i * step
            hot = i == s.get("hot", 0)
            c = self.acc if hot else self.ink
            self.big((x0, y + 4), value, int(min(118, step * .42)), c)
            self.label((x0, y + step * .5), name, c)
            by = y + step * .5 + 40
            self.d.rectangle((x0, by, x0 + (x1 - x0) * amount / top, by + 22), fill=c)
            self.d.rectangle((x0, by, x1, by + 22), outline=self.faint, width=2)

    def timeline(self):
        """A proposal's journey: one rule, the stops on it, the last one in red."""
        s, (x0, y0, x1, y1) = self.s, self.area
        stops = s["stops"]
        y = y0 + (y1 - y0) * .5
        self.d.line((x0, y, x1, y), fill=self.ink, width=4)
        step = (x1 - x0) / (len(stops) - 1)
        for i, (value, name) in enumerate(stops):
            x = x0 + i * step
            last = i == len(stops) - 1
            c = self.acc if last else self.ink
            r = 20 if last else 14
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=c)
            side = "l" if i == 0 else "r" if last else "m"
            self.big((x, y - 50), value, 66, c, side + "s")
            self.label((x, y + 46), name, c, side + "a")
        if s.get("note"):
            self.small((x0, y1 - 40), s["note"], size=30)

    def spread(self):
        """An open book: the verso fades, the recto carries the fact."""
        s, (x0, y0, x1, y1) = self.s, self.area
        mid = W // 2
        ph = y1 - y0
        self.d.rectangle((x0, y0, mid - 6, y1), outline=self.faint, width=3)
        self.page(mid + 6, y0, x1, y1, fill=self.ink, ear=70)
        self.label((x0 + 32, y0 + 36), "Verso", self.muted)
        self.label((mid + 38, y0 + 36), "Recto", self.bg)
        lf, _ = fit_lines(self.d, s["left"], serif, 34, 22, mid - x0 - 70)
        self.d.multiline_text((x0 + 32, y0 + ph * .45), s["left"], font=lf, fill=self.muted, spacing=10)
        bf, _ = fit_lines(self.d, s["right_big"], num, 150, 60, x1 - mid - 76)
        self.d.text((mid + 38, y0 + ph * .38), s["right_big"], font=bf, fill=self.acc if self.bg != RED else CREAM)
        rf, _ = fit_lines(self.d, s["right"], serif, 32, 22, x1 - mid - 76)
        self.d.multiline_text((mid + 38, y0 + ph * .38 + 190), s["right"], font=rf, fill=self.bg, spacing=10)
        self.small((mid - 24, y1 - 20), s.get("verso_no", "10"), self.faint, "rd", 22)
        self.small((mid + 24, y1 - 20), s.get("recto_no", "11"), self.bg, "ld", 22)

    def grid(self):
        """total squares, the first k filled: a share you can count."""
        s, (x0, y0, x1, y1) = self.s, self.area
        total, k, cols = s["total"], s["k"], s.get("cols", 10)
        rows = -(-total // cols)
        gap = 10
        cell = min((x1 - x0 - 300 - gap * (cols - 1)) / cols, (y1 - y0 - gap * (rows - 1)) / rows)
        for i in range(total):
            cx = x0 + (i % cols) * (cell + gap)
            cy = y0 + (i // cols) * (cell + gap)
            if i < k:
                self.d.rectangle((cx, cy, cx + cell, cy + cell), fill=self.acc)
            else:
                self.d.rectangle((cx, cy, cx + cell, cy + cell), outline=self.faint, width=3)
        gx = x0 + cols * (cell + gap) + 30
        self.big((x1, y0 - 12), s["big"], 132, self.acc, "ra")
        f, _ = fit_lines(self.d, s["label"], serif, 28, 20, x1 - gx)
        self.d.multiline_text((x1, y0 + 160), s["label"], font=f, fill=self.ink, spacing=10, align="right", anchor="ra")

    def invoice(self):
        """An invoice page with a status stamp."""
        s, (x0, y0, x1, y1) = self.s, self.area
        px0, px1 = x0 + 60, x1 - 60
        self.page(px0, y0, px1, y1, fill=CREAM if self.bg != CREAM else "#FFF4E6", outline=self.ink, ear=80)
        ink = INK
        self.label((px0 + 44, y0 + 44), "Invoice", ink, size=26)
        self.small((px0 + 44, y0 + 86), s.get("number", "No. 0142"), ink, size=22)
        y = y0 + 170
        for item, amount in s["rows"]:
            self.small((px0 + 44, y), item, ink, size=26)
            self.small((px1 - 44, y), amount, ink, "ra", 26)
            self.d.line((px0 + 44, y + 46, px1 - 44, y + 46), fill="#D9C2A5", width=2)
            y += 70
        self.label((px0 + 44, y + 20), "Total", ink, size=24)
        self.big((px1 - 44, y + 4), s["total"], 54, ink, "ra")
        stamp = s["status"].upper()
        sf = bold(40)
        sw = width(self.d, stamp, sf) + 60
        sx, sy = px0 + 44, y1 - 210
        self.d.rounded_rectangle((sx, sy, sx + sw, sy + 76), radius=38, outline=RED, width=5)
        self.d.text((sx + sw / 2, sy + 38), stamp, font=sf, fill=RED, anchor="mm")
        self.big((px1 - 44, y1 - 50), s["big"], 120, RED, "rd")
        self.small((px0 + 44, y1 - 74), s["label"], ink, size=24)

    def quote(self):
        """One sentence on a page, with a red margin rule and a page number."""
        s, (x0, y0, x1, y1) = self.s, self.area
        self.page(x0, y0, x1, y1, fill=None, outline=self.ink, ear=90)
        self.d.line((x0 + 90, y0, x0 + 90, y1), fill=self.acc, width=3)
        f, _ = fit_lines(self.d, s["quote"], serif, 74, 34, x1 - x0 - 200)
        self.d.multiline_text((x0 + 130, y0 + 140), s["quote"], font=f, fill=self.ink, spacing=24)
        af, _ = fit_lines(self.d, s["by"], serif, 26, 18, x1 - x0 - 200)
        self.d.multiline_text((x0 + 130, y1 - 130), s["by"], font=af, fill=self.ink, spacing=8)
        self.small((x1 - 40, y1 - 30), s.get("page_no", "11"), self.acc, "rd", 24)

    def contents(self):
        """A contents page: numbered sections with dotted leaders."""
        s, (x0, y0, x1, y1) = self.s, self.area
        items = s["items"]
        step = (y1 - y0) / len(items)
        f = serif(40)
        for i, name in enumerate(items):
            y = y0 + i * step + step / 2
            hot = i in s.get("hot", [])
            c = self.acc if hot else self.ink
            self.d.text((x0, y), f"{i + 1:02d}", font=num(30), fill=self.acc, anchor="lm")
            self.d.text((x0 + 80, y), name, font=f, fill=c, anchor="lm")
            lx = x0 + 100 + width(self.d, name, f)
            for dx in range(int(lx), int(x1 - 70), 16):
                self.d.ellipse((dx, y + 12, dx + 4, y + 16), fill=self.faint)
            self.d.text((x1, y), str(s.get("pages", [])[i] if s.get("pages") else i + 1), font=num(30), fill=c, anchor="rm")

    def calendar(self):
        """A working month, Monday to Friday; the red days are the ones spent chasing."""
        s, (x0, y0, x1, y1) = self.s, self.area
        days, k = s.get("days", 20), s["k"]
        cols, gap = 5, 14
        for i, dname in enumerate("MTWTF"):
            cw = (x1 - x0 - gap * 4) / 5
            self.label((x0 + i * (cw + gap) + cw / 2, y0), dname, self.ink, "ma")
        rows = -(-days // cols)
        cw = (x1 - x0 - gap * 4) / 5
        ch = min(cw * .72, (y1 - y0 - 60 - gap * (rows - 1)) / rows)
        for i in range(days):
            cx = x0 + (i % cols) * (cw + gap)
            cy = y0 + 50 + (i // cols) * (ch + gap)
            hot = i < k
            self.d.rectangle((cx, cy, cx + cw, cy + ch), fill=self.acc if hot else None, outline=None if hot else self.faint, width=3)
            self.d.text((cx + 16, cy + 12), str(i + 1), font=bold(24), fill=CREAM if hot else self.faint)
        if s.get("note"):
            self.small((x0, y1 - 10), s["note"], size=28)

    def pricing(self):
        """A pricing table that totals itself."""
        s, (x0, y0, x1, y1) = self.s, self.area
        rows = s["rows"]
        cols = [x0, x1 - 400, x1 - 230, x1]
        self.label((cols[0], y0), "Item", self.ink)
        self.label((cols[1], y0), "Qty", self.ink, "ra")
        self.label((cols[2], y0), "Rate", self.ink, "ra")
        self.label((cols[3], y0), "Amount", self.ink, "ra")
        self.d.line((x0, y0 + 44, x1, y0 + 44), fill=self.ink, width=2)
        y = y0 + 80
        for i, (item, qty, rate) in enumerate(rows):
            hot = i == s.get("hot", -1)
            c = self.acc if hot else self.ink
            self.small((cols[0], y), item, c, size=30)
            self.small((cols[1], y), str(qty), c, "ra", 30)
            self.small((cols[2], y), f"${rate:,}", c, "ra", 30)
            self.small((cols[3], y), f"${qty * rate:,}", c, "ra", 30)
            self.d.line((x0, y + 58, x1, y + 58), fill=self.faint, width=2)
            y += 86
        total = sum(q * r for _, q, r in rows)
        self.label((x0, y + 40), "Total", self.ink, size=26)
        self.big((x1, y + 10), f"${total:,}", 96, self.acc, "ra")
        if s.get("note"):
            self.small((x0, y1 - 10), s["note"], size=28)

    def phone(self):
        """You designed for A4. They met it on a phone."""
        s, (x0, y0, x1, y1) = self.s, self.area
        ph = y1 - y0
        aw = int(ph * .8 / 1.414)
        self.page(x0, y0 + ph * .2, x0 + aw, y1, outline=self.faint, ear=50)
        self.label((x0, y0 + ph * .2 - 40), s.get("left_label", "A4, as designed"), self.muted)
        ly = y0 + ph * .2 + 90
        for i in range(9):
            lw = (aw - 80) * (0.55 if i in (0, 4) else 0.9)
            self.d.rectangle((x0 + 36, ly, x0 + 36 + lw, ly + (14 if i in (0, 4) else 6)), fill=self.faint)
            ly += 44 if i in (0, 3) else 30
        fw, fh = int(ph * .48), ph
        fx = x1 - fw
        self.d.rounded_rectangle((fx, y0, x1, y1), radius=56, fill=self.ink)
        self.d.rounded_rectangle((fx + 18, y0 + 18, x1 - 18, y1 - 18), radius=42, fill=self.bg)
        self.d.rounded_rectangle((fx + fw / 2 - 50, y0 + 34, fx + fw / 2 + 50, y0 + 56), radius=11, fill=self.ink)
        self.big((fx + fw / 2, y0 + fh * .42), s["big"], 108, self.acc, "mm")
        f, _ = fit_lines(self.d, s["label"], serif, 28, 20, fw - 80)
        self.d.multiline_text((fx + fw / 2, y0 + fh * .42 + 90), s["label"], font=f, fill=self.ink, spacing=10, align="center", anchor="ma")


LAYOUTS = {n for n in dir(Card) if not n.startswith("_") and n not in
           ("frame", "headline", "area", "page", "big", "small", "label")}


def render(slide, post):
    if slide["layout"] not in LAYOUTS:
        raise SystemExit(f"Unknown layout {slide['layout']!r}. Use one of: {', '.join(sorted(LAYOUTS))}")
    c = Card(slide, post)
    getattr(c, slide["layout"])()
    return c.img
