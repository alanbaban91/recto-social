#!/usr/bin/env python3
"""Recto engine: publishes the next post in queue.json to the @just.recto Threads account.

A post is plain text, a thread (several connected posts), or text with branded
Recto cards (1 card = image post, 2+ cards = carousel) or real photos.

  python3 post.py render    # render next post's cards into media/ (if it has any)
  python3 post.py publish   # publish it (needs THREADS_TOKEN), then dequeue
  python3 post.py preview   # check every queued post; render all cards into preview/
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error
from PIL import Image, ImageDraw, ImageFont, ImageOps

SITE = "justrecto.com"
API = "https://graph.threads.net/v1.0"
MAX_LEN = 500                     # Threads text limit per post
QUEUE = os.environ.get("QUEUE", "queue.json")   # photos-queue.json for the daily image post
W, H, M = 1080, 1350, 96          # 4:5 portrait, outer margin
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS, ASSETS = os.path.join(HERE, "fonts"), os.path.join(HERE, "assets")

# Recto palette (same tokens as the app's globals.css): stock paper, ink burgundy, signal red
COLORS = {
    "stock":  dict(bg="#F9E4CA", ink="#3C0016", soft="#5C5449", muted="#8A7F6E", accent="#F92424", logo="recto-orange.png"),
    "ink":    dict(bg="#3C0016", ink="#F9E4CA", soft="#DCCDB4", muted="#8A7F6E", accent="#F92424", logo="recto-cream.png"),
    "signal": dict(bg="#F92424", ink="#F9E4CA", soft="#F9E4CA", muted="#3C0016", accent="#3C0016", logo="recto-cream.png"),
}
DOODLES = ["make", "page", "read", "send"]
# Headlines in the Recto logo face (GC Commune, licensed: never committed, restored from the
# BRAND_FONT_B64 secret in CI). Until it's there, Libre Baskerville Bold, Recto's UI face, stands in.
DISPLAY = "GCCommune.otf" if os.path.exists(os.path.join(FONTS, "GCCommune.otf")) else "LibreBaskerville-Bold.ttf"
BODY, LABEL = "LibreBaskerville-Regular.ttf", "LibreBaskerville-Bold.ttf"
LH = 1.0


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def clean(text):
    # drop emoji / symbols the fonts can't draw; curly apostrophes read less "default"
    return "".join(ch for ch in text if ord(ch) < 0x2190).replace("→", "").replace("'", "’")


def wrap(draw, text, fnt, width):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            test = (line + " " + w).strip()
            if draw.textlength(test, font=fnt) <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w
        lines.append(line)
    return lines


def block_height(fnt, lines, lh):
    return int(fnt.size * lh * len(lines))


def fit(draw, text, fontname, max_size, min_size, width, max_h, lh):
    size = max_size
    while size > min_size:
        f = font(fontname, size)
        lines = wrap(draw, text, f, width)
        if block_height(f, lines, lh) <= max_h:
            return f, lines
        size -= 4
    f = font(fontname, min_size)
    return f, wrap(draw, text, f, width)


def draw_lines(draw, x, y, lines, fnt, lh, fill):
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += int(fnt.size * lh)
    return y


def doodle(name, color, width, max_h, angle):
    """One of Recto's hand-drawn doodles, recoloured, scaled and slightly tilted."""
    m = Image.open(os.path.join(ASSETS, "doodles", f"{name}.png")).getchannel("A")
    scale = min(width / m.width, max_h / m.height)
    m = m.resize((int(m.width * scale), int(m.height * scale)), Image.LANCZOS).rotate(angle, Image.BICUBIC, expand=True)
    art = Image.new("RGBA", m.size, color)
    art.putalpha(m)
    return art


def arrow(d, x, y, color):
    d.line([x - 26, y, x, y], fill=color, width=3)
    d.line([x - 10, y - 9, x, y, x - 10, y + 9], fill=color, width=3, joint="curve")


def render_card(post, idx):
    """Recto card: kicker and page label on a hairline, big serif headline, a red doodle."""
    t = COLORS.get(post.get("color", "stock"), COLORS["stock"])
    slides = post["slides"]
    total, slide = len(slides), slides[idx]
    hero, last = idx == 0, idx == total - 1 and total > 1
    seed = sum(map(ord, slides[0]["title"]))
    name = slide.get("doodle", post.get("doodle", DOODLES[(seed + idx) % len(DOODLES)]))
    flip = (seed + idx) % 2                      # alternate which edge the doodle leans from

    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)
    small = font(LABEL, 28)
    inner = W - 2 * M
    title, body = clean(slide["title"]), clean(slide.get("body", ""))

    # --- top: kicker left, page label right ("recto" for odd pages, "verso" for even), hairline
    d.text((M, M), clean(post.get("kicker", "Recto")).upper(), font=small, fill=t["accent"])
    if total > 1:
        label = f"{'RECTO' if idx % 2 == 0 else 'VERSO'}  {idx + 1:02d} / {total:02d}"
        d.text((W - M - d.textlength(label, font=small), M), label, font=small, fill=t["muted"])
    d.line([M, M + 50, W - M, M + 50], fill=t["muted"], width=1)

    # --- footer: hairline, logo left, site or swipe/try-it right
    fy = H - M - 40
    d.line([M, fy - 30, W - M, fy - 30], fill=t["muted"], width=1)
    logo = Image.open(os.path.join(ASSETS, t["logo"])).convert("RGBA")
    logo = logo.resize((int(logo.width * 46 / logo.height), 46), Image.LANCZOS)
    img.paste(logo, (M, fy), logo)
    tag = "SWIPE" if hero and total > 1 else "TRY IT FREE" if last else SITE.upper()
    cy = fy + 26
    if tag != SITE.upper():
        arrow(d, W - M, cy, t["accent"])
        d.text((W - M - 42 - d.textlength(tag, font=small), cy), tag, font=small, fill=t["accent"], anchor="lm")
    else:
        d.text((W - M - d.textlength(tag, font=small), cy), tag, font=small, fill=t["ink"], anchor="lm")

    doodle_color = t["accent"] if post.get("color", "stock") != "signal" else t["ink"]
    if hero or last:
        art = doodle(name, doodle_color, W * 0.62, 400, 5 if flip else -5)
        img.paste(art, (W - art.width - 40 if flip else 40, M + 110), art)
        text_top = M + 110 + art.height + 40
        bf, blines = font(BODY, 40), []
        if body:
            bf, blines = fit(d, body, BODY, 40, 28, inner - 40, 280, 1.4)
        body_h = block_height(bf, blines, 1.4) + (48 if blines else 0)
        tf, tlines = fit(d, title, DISPLAY, 150, 64, inner, fy - 70 - text_top - body_h, LH)
        y = fy - 70 - body_h - block_height(tf, tlines, LH)
        y = draw_lines(d, M, y, tlines, tf, LH, t["ink"])
        if blines:
            draw_lines(d, M, y + 48, blines, bf, 1.4, t["soft"])
    else:
        # step number in the accent colour, doodle low in the corner
        nf = font(DISPLAY, 180)
        nb = d.textbbox((M, M + 110), f"{idx:02d}", font=nf, anchor="la")
        d.text((M, M + 110), f"{idx:02d}", font=nf, fill=t["accent"], anchor="la")
        art = doodle(name, doodle_color, W * 0.45, 260, -6 if flip else 6)
        ay = fy - 60 - art.height
        img.paste(art, (W - M - art.width if flip else M, ay), art)
        tf, tlines = fit(d, title, DISPLAY, 112, 60, inner, 380, LH)
        y = draw_lines(d, M, nb[3] + 50, tlines, tf, LH, t["ink"])
        if body:
            bf, blines = fit(d, body, BODY, 40, 28, inner - 40, ay - y - 80, 1.4)
            draw_lines(d, M, y + 40, blines, bf, 1.4, t["soft"])
    return img


def render_post(post, folder, prefix):
    os.makedirs(folder, exist_ok=True)
    names = []
    for i in range(len(post.get("slides", []))):
        name = f"{prefix}-{i + 1:02d}.jpg"
        render_card(post, i).save(os.path.join(folder, name), "JPEG", quality=92, optimize=True)
        names.append(name)
    return names


def parts(post):
    """The post's text as a list: [main post, reply 1, reply 2, ...]."""
    text = post["text"]
    return [text] if isinstance(text, str) else text


def check(post, n):
    for i, p in enumerate(parts(post)):
        if not p.strip():
            sys.exit(f"Post {n}, part {i + 1} is empty.")
        if len(p) > MAX_LEN:
            sys.exit(f"Post {n}, part {i + 1} is {len(p)} chars (max {MAX_LEN}). Shorten it:\n{p}")
    for ph in post.get("photos", []):
        if not os.path.isfile(ph) or not ph.lower().endswith((".jpg", ".jpeg", ".png")):
            sys.exit(f"Post {n}: photo {ph} is missing or not a .jpg/.png file.")
    if not 0 <= len(post.get("slides", [])) + len(post.get("photos", [])) <= 20:
        sys.exit(f"Post {n} has more than 20 images.")


def copy_photos(post, folder, prefix):
    """Real photos from photos/: upright, max 1440px, JPEG, no EXIF (drops phone GPS data)."""
    names = []
    for i, ph in enumerate(post.get("photos", []), 1):
        im = ImageOps.exif_transpose(Image.open(ph)).convert("RGB")
        im.thumbnail((1440, 1800))
        name = f"{prefix}-photo-{i:02d}.jpg"
        im.save(os.path.join(folder, name), "JPEG", quality=90)
        names.append(name)
    return names


def load(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# ---------------- Threads API ----------------
def api(method, path, params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        url, data = url + "?" + data.decode(), None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Threads API error {e.code}: {e.read().decode()}")


def wait_public(url):
    for _ in range(40):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(5)
    sys.exit(f"Image never became public: {url}")


def wait_ready(cid, token):
    for _ in range(36):
        res = api("GET", cid, {"fields": "status,error_message", "access_token": token})
        if res.get("status") == "FINISHED":
            return
        if res.get("status") in ("ERROR", "EXPIRED"):
            sys.exit(f"Container {cid} failed: {res}")
        time.sleep(5)
    sys.exit(f"Container {cid} not ready in time")


def publish(params, token):
    cid = api("POST", "me/threads", {**params, "access_token": token})["id"]
    wait_ready(cid, token)
    return api("POST", "me/threads_publish", {"creation_id": cid, "access_token": token})["id"]


def media_urls(names):
    repo = os.environ.get("GITHUB_REPOSITORY") or sys.exit("GITHUB_REPOSITORY is not set.")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return [f"https://raw.githubusercontent.com/{repo}/{branch}/media/{n}" for n in names]


def cmd_render():
    queue = load(QUEUE, [])
    if not queue:
        # Fails on purpose so GitHub emails you: time to add a new batch.
        sys.exit(f"{QUEUE} is empty. Add a new batch.")
    check(queue[0], 1)
    for f in os.listdir("media"):
        if f.endswith(".jpg"):
            os.remove(os.path.join("media", f))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")
    names = copy_photos(queue[0], "media", f"post-{stamp}") + render_post(queue[0], "media", f"post-{stamp}")
    save("media/next.json", names)
    print(f"Prepared {len(names)} image(s)." if names else "Text post, nothing to render.")


def cmd_publish():
    token = os.environ.get("THREADS_TOKEN") or sys.exit("THREADS_TOKEN is not set.")
    queue, names = load(QUEUE, []), load("media/next.json", [])
    post, texts = queue[0], parts(queue[0])

    if not names:
        root = publish({"media_type": "TEXT", "text": texts[0]}, token)
    else:
        urls = media_urls(names)
        for u in urls:
            wait_public(u)
        if len(urls) == 1:
            root = publish({"media_type": "IMAGE", "image_url": urls[0], "text": texts[0]}, token)
        else:
            children = []
            for u in urls:
                child = api("POST", "me/threads", {"media_type": "IMAGE", "image_url": u,
                                                   "is_carousel_item": "true", "access_token": token})["id"]
                wait_ready(child, token)
                children.append(child)
            root = publish({"media_type": "CAROUSEL", "children": ",".join(children), "text": texts[0]}, token)

    # The main post is live now, so dequeue it even if a reply fails (no double posting on rerun).
    ids, error = [root], None
    try:
        for reply in texts[1:]:
            ids.append(publish({"media_type": "TEXT", "text": reply, "reply_to_id": ids[-1]}, token))
    except SystemExit as e:
        error = f"Main post is live but the thread stopped after {len(ids)} part(s): {e}"

    posted = load("posted.json", [])
    posted.append({"ids": ids, "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), **post})
    save("posted.json", posted)
    save(QUEUE, queue[1:])
    for n in names + ["next.json"]:
        p = os.path.join("media", n)
        if os.path.exists(p):
            os.remove(p)
    if error:
        sys.exit(error)
    print(f"Published {len(ids)} part(s) (id {root}). {len(queue) - 1} posts left in {QUEUE}.")


def cmd_preview():
    queue = load(QUEUE, [])
    for i, post in enumerate(queue, 1):
        check(post, i)
        render_post(post, "preview", f"{i:02d}-{post.get('mood', 'post')}")
    print(f"All {len(queue)} posts in {QUEUE} pass the length check. Cards written to preview/")


if __name__ == "__main__":
    {"render": cmd_render, "publish": cmd_publish, "preview": cmd_preview}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
