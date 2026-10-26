#!/usr/bin/env python3
"""Recto reply bot: answers new comments on Threads and Instagram from a knowledge base of
Recto facts (pricing, payment, Kurdish and Arabic, privacy, sharing, invoices, folio...)
in English, Kurdish or Arabic. No AI: a comment that matches nothing gets no reply,
which is safer than a wrong one.

  python3 replies.py            # reply to new comments (needs THREADS_TOKEN; IG_TOKEN optional)
  DRY_RUN=1 python3 replies.py  # print the replies it would send, post nothing

Every fact below must match the app (src/lib/plans.ts, src/config/payments.ts, src/lib/site.ts).
After changing a price or a feature there, change it here and run: python3 test_replies.py
"""
import os, re, sys, zlib
from post import api, publish, load, save
import ig

SEEN = "replied.json"
MAX_REPLIES = 10      # per platform per run, so a spam wave can't flood the account
RECENT_POSTS = 20     # how many of our latest posts to check for comments
KURDISH = set("ڕڵێۆەپچژگڤ")   # ڕ ڵ ێ ۆ ە پ چ ژ گ ڤ
END = r"(?![a-z])"    # whole English words; Kurdish/Arabic stems may take endings (کوردی -> کوردییە)

# The knowledge base: (topic, keywords). Checked in this order, the first match wins, so the
# specific topics come before the broad ones ("is folio in the free trial?" is a folio question).
TOPICS = [
    ("bug", r"\b(bug|broken|not working|doesn.?t work|isn.?t working|won.?t (load|open|export|save)|error|crash\w*|can.?t (log ?in|sign ?in|login)|lost my|کار ناکات|هەڵە|کێشە|لا يعمل|مشكلة|خطأ)"),
    ("pay", r"\b(how (do|can) i pay|pay with|payment|paypal|visa|mastercard|credit card|card payment|fib|fastpay|superqi|crypto|usdt|پارەدان|پارە بدەم|چۆن پارە|الدفع|ادفع|أدفع|طريقة الدفع)" + END),
    ("folio", r"\b(folio|brand guidelines?|identity presentation|present (a|my|the) (brand|identity)|فۆلیۆ|فوليو)" + END),
    ("price", r"\b(price|prices|pricing(?! tables?)|cost|costs|how much|is it free|free trial|for free|subscription|trial|نرخ|نرخی|چەندە|بەخۆڕایی|بێ پارە|سعر|السعر|اسعار|کم(?!\w)|أسعار|كم(?!\w)|بكم(?!\w)|مجان\w*|اشتراك)" + END),
    ("script", r"\b(kurdish|sorani|arabic|farsi|persian|rtl|right[ -]to[ -]left|کوردی|کوردیی|عەرەبی|فارسی|فۆنت|كردي|الكردية|عربي|العربية|خطوط|الخطوط|خط عربي|خط كردي|الخط العربي|الخط الكردي)" + END),
    ("privacy", r"\b(privacy|private|encrypt\w*|end[ -]to[ -]end|secure|security|safe|my data|confidential|nda|پاراستن|نهێنی|ئاسایش|خصوصية|آمن|تشفير|أمان)" + END),
    ("invoice", r"\b(invoice|invoices|invoicing|billing|bill (a|my) client|receipt|فاکتۆر|فاکتور|پسوولە|وەسڵ|فاتورة|فواتير)" + END),
    ("track", r"\b(track\w*|analytics|who (viewed|opened|read)|opened it|read receipts?|time per page|views|بینەر|کێ بینی|تتبع|من شاهد|مشاهدات|إحصائيات)" + END),
    ("share", r"\b(share (it|a|the|my) (doc\w*|proposal|deck|file)|share link|how (do|can) i share|send (it )?to (a |my |the )?client|live link|flip ?book|page[ -]turn\w*|magazine|present\w*|slideshow|password|expiry|expire|client comments?|comment on the page|بڵاوکردنەوە|ناردن بۆ کڕیار|مشاركة|عرض تقديمي)" + END),
    ("export", r"\b(pdf|export\w*|print\w*|png|cmyk|bleed|چاپ|پی دی ئێف|طباعة|تصدير)" + END),
    ("import", r"\b(illustrator|ai file|paste from|import (from|my|a|an)|importing|can i import|psd|photoshop|ئیلەستریتەر|اليستريتور|إليستريتور)" + END),
    ("compare", r"\b(canva|pitch\.com|docsend|indesign|keynote|powerpoint|google slides|qwilr|pandadoc|better than|alternative|vs\.?|كانفا|کانڤا)" + END),
    ("brand", r"\b(brand kit|my brand|my logo|my fonts?|my own fonts?|custom fonts?|upload (my )?fonts?|my colou?rs|templates?|on[ -]brand|براند|قالب|قوالب|تێمپلەیت)" + END),
    ("blocks", r"\b(proposal|pitch deck|deck|case stud\w*|rate card|pricing table|timeline|scope|signature|e-?sign|contract|terms|testimonial\w*|پێشنیار|پڕۆپۆزەڵ|عرض سعر|مقترح|دراسة حالة|توقيع|عقد)" + END),
    ("size", r"\b(a4|a3|a5|16:9|16x9|letter size|square|custom size|page size|instagram size|قەبارە|مقاس|حجم الصفحة)" + END),
    ("assets", r"\b(unsplash|stock photos?|icons|illustrations|where (do|did) (you|i) get (the )?(images|photos)|أيقونات)" + END),
    ("app", r"\b(ios|android|app store|play store|mobile app|iphone app|desktop app|install|on (my|the) phone|ئەپ|ئەپڵیکەیشن|تطبيق|تثبيت)" + END),
    ("team", r"\b(for (a|my|our) (team|studio|agency)|teams|team plan|agency plan|seats|multiple users|collaborat\w*|enterprise|بۆ تیم|للفريق|للشركات)" + END),
    ("start", r"\b(sign ?up|where can i (try|get|find)|how (do|can) i (start|get|try|use)|(love|like|want) to try|link\?|link please|website\?|join|دەستپێبکەم|چۆن بەکاری بێنم|لینک|وين الرابط|كيف أبدأ|أريد أن أجرب)" + END),
    ("thanks", r"\b(thank\w*|love|great|beautiful|nice|brilliant|gorgeous|clean|well said|so true|facts|need this|needed this|سوپاس|جوان|دەستخۆش|دەست خۆش|بژی|شكرا|شكراً|جميل|رائع|مبدع|حلو)" + END),
]

# Doubt or criticism: never answer these with a cheerful thank-you (keywords can't read tone).
DOUBT = r"\b(but|not|meh|bad|ugly|worst|hate|boring|overrated|scam|expensive|بەڵام|خراپ|ناشیرین|گرانە|لكن|سيء|سيئ|غالي)" + END

TRIAL = "7-day free trial, no card needed"
# Several wordings per answer, picked per comment, so the profile doesn't fill with copies.
REPLIES = {
    "bug": {
        "en": ["Sorry about that. Tell us what happened at justrecto.com/contact and we'll fix it."],
        "ku": ["ببورە بۆ ئەمە. پێمان بڵێ چی ڕوویدا لە justrecto.com/contact و چاکی دەکەینەوە."],
        "ar": ["نعتذر عن ذلك. أخبرنا بما حدث على justrecto.com/contact وسنصلحه."],
    },
    "pay": {
        "en": ["You can pay with FIB, SuperQi, FastPay or crypto. Card payments are coming soon."],
        "ku": ["دەتوانیت بە FIB، SuperQi، FastPay یان کریپتۆ پارە بدەیت. پارەدان بە کارت بەم زووانە."],
        "ar": ["يمكنك الدفع عبر FIB أو SuperQi أو FastPay أو العملات الرقمية. الدفع بالبطاقة قريبًا."],
    },
    "folio": {
        "en": ["folio is part of Recto Studio. Upload the logo, guidelines and mockups, and one click turns them into an animated presentation page in that brand, built on your device. justrecto.com"],
        "ku": ["folio بەشێکە لە Recto Studio. لۆگۆ و ڕێنماییەکانی براند و ماکئەپەکان باربکە، بە یەک کلیک دەبنە پەڕەیەکی پێشکەشکردنی جووڵاو بە هەمان براند. justrecto.com"],
        "ar": ["folio جزء من Recto Studio. ارفع الشعار ودليل الهوية والموكابات، وبنقرة واحدة تصبح صفحة عرض متحركة بنفس الهوية. justrecto.com"],
    },
    "price": {
        "en": [f"There's a {TRIAL}. After that, Studio is $15 for a month, $39 for 3 months or $135 for a year. justrecto.com",
               f"Start with the {TRIAL}. Studio is then $15 a month, or $135 for the whole year. justrecto.com"],
        "ku": ["٧ ڕۆژ تاقیکردنەوەی بەخۆڕایی، بێ کارت. دواتر Studio مانگێک 15 دۆلار، ٣ مانگ 39 دۆلار، ساڵێک 135 دۆلار. justrecto.com"],
        "ar": ["تجربة مجانية لمدة 7 أيام بدون بطاقة. بعدها Studio بسعر 15 دولار لشهر، 39 دولار لثلاثة أشهر أو 135 دولار للسنة. justrecto.com"],
    },
    "script": {
        "en": ["Yes. Recto has Arabic and Kurdish faces among its 60+ fonts, any text box can run right-to-left next to English, and it warns you when a font can't show a Kurdish letter."],
        "ku": ["بەڵێ. Recto فۆنتی کوردی و عەرەبی هەیە، هەر بۆکسێکی نووسین دەتوانێت لە ڕاستەوە بۆ چەپ بێت لە تەنیشت ئینگلیزی، و ئاگادارت دەکاتەوە کاتێک فۆنتێک پیتێکی کوردی نیشان نادات."],
        "ar": ["نعم. يضم Recto خطوطًا عربية وكردية ضمن أكثر من 60 خطًا، ويمكن لأي مربع نص أن يكون من اليمين إلى اليسار بجانب الإنجليزية."],
    },
    "privacy": {
        "en": ["Documents are end-to-end encrypted. We only hold scrambled bytes, so nothing is readable until you publish a link, and that link can carry a password or an expiry date."],
        "ku": ["بەڵگەنامەکان لە سەرەتاوە تا کۆتایی شفرە کراون. ئێمە تەنها داتای شفرەکراو هەڵدەگرین، و هیچ شتێک ناخوێندرێتەوە تا لینکێک بڵاو نەکەیتەوە."],
        "ar": ["المستندات مشفرة من طرف إلى طرف. نحن نحتفظ ببيانات مشفرة فقط، فلا يُقرأ شيء حتى تنشر رابطًا، ويمكن حمايته بكلمة مرور أو تاريخ انتهاء."],
    },
    "invoice": {
        "en": ["Yes, invoices live in Recto too: your logo, a drawn signature or stamp, saved client details, partial payments, and a status from draft to sent, viewed, overdue and paid."],
        "ku": ["بەڵێ، فاکتۆر لە Recto دایە: لۆگۆکەت، واژۆ یان مۆر، زانیاری کڕیار پاشەکەوت دەکرێت، پارەدانی بەش بەش، و دۆخی نێردراو، بینراو و دراو."],
        "ar": ["نعم، الفواتير موجودة في Recto: شعارك، توقيع أو ختم، بيانات العميل محفوظة، دفعات جزئية، وحالة من مسودة إلى مرسلة ومشاهدة ومدفوعة."],
    },
    "track": {
        "en": ["Every share link shows who viewed, how long they spent on each page and how far they got."],
        "ku": ["هەر لینکێک پیشانت دەدات کێ بینیویەتی، چەند لە هەر پەڕەیەک ماوەتەوە و تا کوێ خوێندوویەتەوە."],
        "ar": ["كل رابط يُظهر من شاهد، وكم بقي على كل صفحة، وإلى أين وصل في القراءة."],
    },
    "share": {
        "en": ["Publish a link and it opens as a magazine spread, a page-turning book or plain slides. It updates when you edit, can carry a password or expiry, and clients pin comments to the page without an account."],
        "ku": ["لینکێک بڵاوبکەرەوە، وەک گۆڤار، کتێبی لاپەڕە هەڵدراو یان سلاید دەکرێتەوە. کاتێک دەستکاری دەکەیت نوێ دەبێتەوە، و کڕیار بێ ئەکاونت کۆمێنت لەسەر پەڕەکە دادەنێت."],
        "ar": ["انشر رابطًا فيُفتح كمجلة أو كتاب تُقلب صفحاته أو شرائح. يتحدث عند التعديل، ويمكن حمايته بكلمة مرور، ويعلّق العميل على الصفحة بدون حساب."],
    },
    "export": {
        "en": ["Any document exports as a print-ready PDF at its exact page size, or as PNGs of each page."],
        "ku": ["هەر بەڵگەنامەیەک وەک PDF ی ئامادەی چاپ بە قەبارەی ڕاستەقینەی پەڕەکە، یان وەک PNG بۆ هەر پەڕەیەک دەردەکرێت."],
        "ar": ["أي مستند يُصدَّر كملف PDF جاهز للطباعة بمقاس الصفحة نفسه، أو كصور PNG لكل صفحة."],
    },
    "import": {
        "en": ["Copy from Illustrator and paste straight onto the page in Recto."],
        "ku": ["لە ئیلەستریتەر کۆپی بکە و ڕاستەوخۆ لەسەر پەڕەکەی Recto پەیستی بکە."],
        "ar": ["انسخ من Illustrator والصق مباشرة على الصفحة في Recto."],
    },
    "compare": {
        "en": ["Recto is made for client documents: real pages like a design tool, your brand applied in one click, and tracked links with comments built in. Try it for 7 days free at justrecto.com"],
        "ku": ["Recto بۆ بەڵگەنامەی کڕیار دروستکراوە: پەڕەی ڕاستەقینە، براندەکەت بە یەک کلیک، و لینکی بەدواداچوون لەگەڵ کۆمێنت. ٧ ڕۆژ بەخۆڕایی تاقی بکەرەوە justrecto.com"],
        "ar": ["Recto مصمم لمستندات العملاء: صفحات حقيقية، هويتك بنقرة واحدة، وروابط متتبَّعة مع تعليقات. جرّبه مجانًا 7 أيام على justrecto.com"],
    },
    "brand": {
        "en": ["Save your logos, colours and fonts once in a brand kit, then apply them to a whole document in one click. The templates start from your brand, not ours."],
        "ku": ["لۆگۆ و ڕەنگ و فۆنتەکانت یەک جار لە براند کیت پاشەکەوت بکە، پاشان بە یەک کلیک لەسەر هەموو بەڵگەنامەکە جێبەجێیان بکە."],
        "ar": ["احفظ شعاراتك وألوانك وخطوطك مرة واحدة في Brand Kit، ثم طبّقها على المستند كله بنقرة واحدة."],
    },
    "blocks": {
        "en": ["Recto has ready-made blocks for it: scope, timeline, case studies with before/after and metrics, testimonials, a payment schedule, numbered terms, a signature block, and pricing tables that total themselves."],
        "ku": ["Recto بلۆکی ئامادەی هەیە: سنووری کار، خشتەی کات، کەیس ستەدی، پێشکەوتنی پارەدان، مەرجەکان، واژۆ، و خشتەی نرخ کە خۆی کۆ دەکاتەوە."],
        "ar": ["في Recto كتل جاهزة: نطاق العمل، الجدول الزمني، دراسات الحالة، جدول الدفعات، الشروط، التوقيع، وجداول أسعار تحسب المجموع تلقائيًا."],
    },
    "size": {
        "en": ["You design on real pages: A4, 16:9, square or any custom size."],
        "ku": ["لەسەر پەڕەی ڕاستەقینە دیزاین دەکەیت: A4، 16:9، چوارگۆشە یان هەر قەبارەیەکی تایبەت."],
        "ar": ["تصمم على صفحات حقيقية: A4 أو 16:9 أو مربع أو أي مقاس مخصص."],
    },
    "assets": {
        "en": ["You can search Unsplash photos, icons and illustrations from inside the editor."],
        "ku": ["دەتوانیت لەناو ئێدیتەرەکەدا بەدوای وێنەی Unsplash، ئایکۆن و ئیلوستراسیۆندا بگەڕێیت."],
        "ar": ["يمكنك البحث عن صور Unsplash والأيقونات والرسومات من داخل المحرر."],
    },
    "app": {
        "en": ["Recto runs in the browser, nothing to install. Open justrecto.com and start."],
        "ku": ["Recto لە وێبگەڕدا کار دەکات، پێویست بە دابەزاندن ناکات. justrecto.com بکەرەوە و دەست پێبکە."],
        "ar": ["يعمل Recto في المتصفح، لا حاجة للتثبيت. افتح justrecto.com وابدأ."],
    },
    "team": {
        "en": ["For a studio or team, tell us what you need at justrecto.com/contact and we'll set it up with you."],
        "ku": ["بۆ ستۆدیۆ یان تیم، پێمان بڵێ چیت پێویستە لە justrecto.com/contact."],
        "ar": ["للاستوديوهات والفرق، أخبرنا بما تحتاجه على justrecto.com/contact."],
    },
    "start": {
        "en": [f"justrecto.com. There's a {TRIAL}.", f"Right here: justrecto.com, {TRIAL}."],
        "ku": ["justrecto.com. ٧ ڕۆژ تاقیکردنەوەی بەخۆڕایی، بێ کارت."],
        "ar": ["justrecto.com. تجربة مجانية لمدة 7 أيام بدون بطاقة."],
    },
    "thanks": {
        "en": ["Thank you. That means a lot.", "Appreciated. Glad it landed.", "Thank you for reading."],
        "ku": ["زۆر سوپاس، زۆر بەنرخە بۆمان."],
        "ar": ["شكرًا جزيلًا، هذا يعني لنا الكثير."],
    },
}


def language(text):
    if any("؀" <= ch <= "ۿ" for ch in text):
        return "ku" if KURDISH & set(text) else "ar"
    return "en"


def answer(text, comment_id=""):
    """The reply for a comment, or None when it matches no topic."""
    low = text.lower()
    for topic, pattern in TOPICS:
        if topic == "thanks" and re.search(DOUBT, low):
            return None
        if re.search(pattern, low):
            options = REPLIES[topic][language(text)]
            return options[zlib.crc32(comment_id.encode()) % len(options)]
    return None


def handle(comments, me, seen, dry, send):
    """Reply to the comments we haven't seen; returns how many were sent."""
    sent = read = 0
    for c in comments:
        read += 1
        if sent >= MAX_REPLIES:
            break
        if c["id"] in seen or c.get("username") == me or not c.get("text"):
            if dry:
                print(f"(ignored: {'already answered' if c['id'] in seen else 'our own' if c.get('username') == me else 'no text'}) {c}")
            continue
        reply = answer(c["text"], c["id"])
        print(f"@{c.get('username')}: {c['text']}\n  -> {reply or '(skipped)'}\n")
        if reply and not dry:
            send(c["id"], reply)
            sent += 1
        if not dry:
            seen.add(c["id"])
            save(SEEN, sorted(seen))   # save as we go, so a crash never double-replies
    print(f"Read {read} comment(s).")
    return sent


def threads_comments(token):
    posts = api("GET", "me/threads", {"fields": "id", "limit": RECENT_POSTS, "access_token": token}).get("data", [])
    for p in posts:
        yield from api("GET", f"{p['id']}/conversation", {"fields": "id,text,username", "access_token": token}).get("data", [])


def instagram_comments(token):
    posts = ig.api("GET", "me/media", {"fields": "id", "limit": RECENT_POSTS, "access_token": token}).get("data", [])
    for p in posts:
        yield from ig.api("GET", f"{p['id']}/comments", {"fields": "id,text,username", "access_token": token}).get("data", [])


def main():
    token = os.environ.get("THREADS_TOKEN") or sys.exit("THREADS_TOKEN is not set.")
    dry = os.environ.get("DRY_RUN") == "1"
    seen = set(load(SEEN, []))

    me = api("GET", "me", {"fields": "username", "access_token": token})["username"]
    sent = handle(threads_comments(token), me, seen, dry,
                  lambda cid, text: publish({"media_type": "TEXT", "text": text, "reply_to_id": cid}, token))
    print(f"Threads: {sent} replies {'would be ' if dry else ''}sent.")

    ig_token = os.environ.get("IG_TOKEN")
    if not ig_token:
        print("IG_TOKEN is not set; skipping Instagram comments.")
        return
    ig_me = ig.api("GET", "me", {"fields": "username", "access_token": ig_token})["username"]
    sent = handle(instagram_comments(ig_token), ig_me, seen, dry,
                  lambda cid, text: ig.api("POST", f"{cid}/replies", {"message": text, "access_token": ig_token}))
    print(f"Instagram: {sent} replies {'would be ' if dry else ''}sent.")


if __name__ == "__main__":
    main()
