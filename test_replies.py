"""Run: python3 test_replies.py  (checks the reply bot's knowledge base rules)"""
from replies import answer, language, REPLIES

CASES = [  # comment, expected topic (None = no reply), expected language
    ("How much is it?", "price", "en"), ("Is it free?", "price", "en"), ("how long is the free trial", "price", "en"),
    ("Can I pay with a visa card?", "pay", "en"), ("do you take FIB", "pay", "en"),
    ("Does it support Kurdish fonts?", "script", "en"), ("arabic right to left?", "script", "en"),
    ("Is my data private?", "privacy", "en"), ("is it end-to-end encrypted", "privacy", "en"),
    ("Can I make invoices too?", "invoice", "en"), ("what is folio", "folio", "en"),
    ("is folio in the free trial?", "folio", "en"), ("Can I see who opened it?", "track", "en"),
    ("does it do a page-turning book", "share", "en"), ("can clients leave client comments", "share", "en"),
    ("Does it export PDF?", "export", "en"), ("Can I paste from Illustrator?", "import", "en"),
    ("How is this different from Canva?", "compare", "en"), ("can I use my own fonts", "brand", "en"),
    ("does it have a pricing table block", "blocks", "en"), ("A4 or 16:9?", "size", "en"),
    ("is there an iOS app", "app", "en"), ("Is there a plan for our team", "team", "en"),
    ("How do I sign up?", "start", "en"), ("I'd love to try it", "start", "en"),
    ("It doesn't work on my laptop", "bug", "en"), ("Love this, so true", "thanks", "en"),
    ("great post but how much is it?", "price", "en"),
    ("نرخی چەندە؟", "price", "ku"), ("فۆنتی کوردی هەیە؟", "script", "ku"), ("دەستخۆش زۆر جوانە", "thanks", "ku"),
    ("کم السعر؟", "price", "ar"), ("هل يدعم الخط العربي؟", "script", "ar"), ("هل يدعم العربية؟", "script", "ar"),
    ("كيف أبدأ؟", "start", "ar"), ("شكرا عمل رائع", "thanks", "ar"), ("هل يوجد فاتورة؟", "invoice", "ar"),
    # no reply: opinions, tags, emoji, near misses
    ("This is important", None, None), ("I'll share this with my friend", None, None), ("@friend look", None, None),
    ("🔥🔥", None, None), ("the images are great but meh", None, None), ("any plans for the weekend?", None, None),
    ("nice vibes but meh", None, None), ("جوانە بەڵام", None, None), ("this is overrated", None, None),
]

for text, topic, lang in CASES:
    r = answer(text, "id")
    got = next((t for t, langs in REPLIES.items() for opts in langs.values() if r in opts), None) if r else None
    assert got == topic, f"{text!r}: expected {topic}, got {got}"
    assert r is None or language(text) == lang, f"{text!r}: wrong language"
for topic, langs in REPLIES.items():
    assert set(langs) == {"en", "ku", "ar"}, f"{topic}: missing a language"
    assert all(len(o) <= 500 for opts in langs.values() for o in opts), f"{topic}: reply over 500 chars"
print(f"all {len(CASES)} cases pass")
