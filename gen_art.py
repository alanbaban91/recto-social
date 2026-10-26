#!/usr/bin/env python3
"""Generate cover illustrations with Gemini for image posts that have an "art_prompt".

Each post's art_prompt describes only the scene. The Recto style (STYLE below, taken from
the moodboard in Affinity) is added to every prompt, so the whole feed looks like one series.
Gemini makes the picture only; post.py sets the headline, logo and labels on top, so no
AI-made text ever reaches a card.

Run on your Mac (needs GEMINI_API_KEY), check the images in art/, then commit them:
  python3 gen_art.py            # generate art for queued posts that don't have it yet
  python3 gen_art.py 3          # regenerate post 3 (0-based) in photos-queue.json
"""
import base64, json, os, sys, urllib.request, urllib.error
from post import load, save

MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
QUEUE = "photos-queue.json"
STYLE = (
    "Style: bold flat vector cartoon illustration in a contemporary editorial ad-campaign style. "
    "Characters are stylised and playful, with simple geometric faces and big, chunky, expressive hands; "
    "flat solid colour shapes with no outlines and only minimal cel shading. Exaggerated, dynamic perspective "
    "(hands and objects reaching toward the viewer), radiating burst shapes and speed lines for energy, and "
    "small sticker-like doodles floating around: sparkles, squiggles, stars, dots, arrows. "
    "Vivid, saturated, joyful colour: signal red #F92424, deep burgundy #3C0016 and warm cream #F9E4CA lead, "
    "with pops of sunny yellow, violet, bubblegum pink and teal. Clean composition with one clear focal point. "
    "Absolutely no text, letters, numbers, words, logos, brand marks or watermarks anywhere in the image. "
    "Original characters and setting; do not copy any existing artwork."
)


def generate(prompt, path):
    key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY is not set.")
    body = {
        "contents": [{"parts": [{"text": f"{prompt}\n\n{STYLE}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "4:3"}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Gemini error {e.code}: {e.read().decode()[:500]}")
    for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            open(path, "wb").write(base64.b64decode(part["inlineData"]["data"]))
            return
    sys.exit(f"Gemini returned no image: {json.dumps(res)[:500]}")


def main():
    queue = load(QUEUE, [])
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    os.makedirs("art", exist_ok=True)
    for i, post in enumerate(queue):
        if not post.get("art_prompt") or (only is not None and i != only):
            continue
        slug = "".join(c if c.isalnum() else "-" for c in post["kicker"].lower()).strip("-")
        path = post.get("art") or f"art/{slug}.png"
        if os.path.exists(path) and only is None:
            continue
        print(f"{i}: {post['kicker']} ...", flush=True)
        generate(post["art_prompt"], path)
        post["art"] = path
        save(QUEUE, queue)   # save as we go, so a failure halfway keeps what's done
    print("Done. Check art/, then run: QUEUE=photos-queue.json python3 post.py preview")


if __name__ == "__main__":
    main()
