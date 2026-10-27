# Recto Engine

Posts to the **@just.recto** Threads and Instagram accounts and answers comments on both,
using the official Meta APIs and free GitHub Actions.

- **Threads, 7 posts a day.** 6 text posts from `queue.json`, started by cron-job.org (08:00, 10:30, 13:00, 15:30, 20:00,
  22:30 Baghdad time) and 1 image post from `photos-queue.json` at 18:00.
- **Instagram, 1 post a day.** The same 18:00 image post, with the same cards and caption.
- **Comments, every 30 minutes.** A knowledge-base bot answers questions about Recto on Threads
  and Instagram, in English, Kurdish or Arabic. Anything it doesn't know gets no reply.

## Writing posts
Read `VOICE.md` first: the Recto tone of voice, the five territories, the daily rhythm, the
facts we can use and the words we don't.

```json
[
  { "mood": "page", "text": "One post, max 500 characters." },

  { "mood": "pitch", "text": ["Thread opener.", "Part two.", "Part three."] },

  { "mood": "product", "kicker": "Brand kit", "color": "ink", "doodle": "make",
    "slides": [ { "title": "Big headline.", "body": "Optional smaller line." } ],
    "text": "The caption, above the image on Threads and under it on Instagram." }
]
```
- `mood`: `page`, `pitch`, `studio`, `script`, `open`, `product`, `late`. Only a label, to keep the mix balanced.
- `color` (image posts): `stock` (paper), `ink` (burgundy) or `signal` (red).
- `doodle` (optional): `make`, `page`, `read` or `send`, Recto's own doodles. Per post or per slide.
- `kicker`: the small label at the top of the card.
- `photos`: real photos instead of (or as well as) cards: `"photos": ["photos/desk.jpg"]`.
  Straightened, resized and stripped of location data before posting.
- 1 card = image post, 2 to 10 = carousel (Instagram stops at 10).
- Text posts go in `queue.json`, image posts in `photos-queue.json`.
- Check before committing: `python3 post.py preview` and `QUEUE=photos-queue.json python3 post.py preview`,
  then look at the cards in `preview/`.

The first batch is two weeks long: 84 text posts and 14 image posts.

## Setup (about an hour)

### 1. A separate Meta app for Recto
Recto gets its own app, separate from your personal and 33Studio apps.
1. developers.facebook.com > My Apps > **Create App**. Name: `Recto Social`.
2. Use case: **Access the Threads API**. Business: the Recto business portfolio if you have one.
3. Use cases > Access the Threads API > **Customize** > Permissions: add `threads_basic`,
   `threads_content_publish`, `threads_read_replies`, `threads_manage_replies`.
4. Same screen > **Settings**: put `https://justrecto.com/` in all three callback boxes. Save.
   Copy the **Threads App ID** and **Threads App Secret**.
5. App roles > Roles > Add people > **Threads Tester** > `just.recto`.
6. In Threads, logged in as just.recto: Settings > Account > Website permissions > Invites > **Accept**.

### 2. The Threads token
1. Log in to threads.net **as just.recto**.
2. In this folder: `python3 get_token.py`, paste the App ID, Secret and `https://justrecto.com/`,
   open the link, approve, paste the URL you land on. The long token it prints is `THREADS_TOKEN`.

### 3. The GitHub repo
1. Create a **public** repo named `recto-social` (public so Threads and Instagram can download
   the card images; tokens stay in Secrets).
2. Push this folder to it:
   ```
   git remote add origin https://github.com/alanbaban91/recto-social.git
   git push -u origin main
   ```

### 4. Secrets (repo > Settings > Secrets and variables > Actions > Secrets)
- `THREADS_TOKEN`: from step 2.
- `GH_PAT`: a fine-grained token with **Secrets: Read and write** on this repo only. It lets the
  refresh workflow renew both tokens on the 1st and 15th of each month.
- `BRAND_FONT_B64`: the Recto logo face (GC Commune) for card headlines. It's licensed, so it never
  goes in the public repo. In this folder: `base64 -i fonts/GCCommune.otf | pbcopy`, then paste.
  (It's already subset to Latin so it fits GitHub's 48 KB limit.) Without it, cards use Libre Baskerville.

### 5. Instagram
1. Make @just.recto a professional account (Settings > Account type and tools > Business).
2. In the Recto Social app: Use cases > **Add use cases** > *Manage messaging & content on Instagram*.
3. **API setup with Instagram login** > Permissions: `instagram_business_basic`,
   `instagram_business_content_publish`, `instagram_business_manage_comments`.
4. If asked: App roles > **Instagram Tester** > just.recto, then accept in Instagram (Settings >
   Website permissions > Apps and websites > Tester invites).
5. **Generate access tokens** > Add account > log in as just.recto > approve > copy.
   Save it as the `IG_TOKEN` secret. Until it's set, Instagram steps skip and Threads still runs.

### 6. Post times (cron-job.org)
GitHub's own schedule often starts runs 5 to 30 minutes late, so cron-job.org starts the posting
workflows at the exact minute instead.
1. GitHub > Settings > Developer settings > Fine-grained tokens > **Generate new token**.
   Name `recto cron`, repository `recto-social` only, permission **Actions: Read and write**.
2. On cron-job.org (free), create 3 jobs. All of them: method **POST**, timezone **Asia/Baghdad**,
   and under Advanced:
   - Headers: `Authorization: Bearer <the token>`, `Accept: application/vnd.github+json`
   - Request body: `{"ref":"main"}`

   | Job | URL ends in | Schedule |
   |---|---|---|
   | Recto text :00 | `/actions/workflows/post.yml/dispatches` | 08:00, 13:00, 20:00 |
   | Recto text :30 | `/actions/workflows/post.yml/dispatches` | 10:30, 15:30, 22:30 |
   | Recto image | `/actions/workflows/post-photos.yml/dispatches` | 18:00 |

   URL start: `https://api.github.com/repos/alanbaban91/recto-social`
3. Press **Test run** on each job: GitHub answers `204` and a run appears in the Actions tab.
   (A test run posts for real.)

The reply bot and token refresh stay on GitHub's schedule; a few minutes late doesn't matter there.

### 7. Test
1. Actions > **Post to Threads (Recto)** > Run workflow. The first text post goes live.
2. Actions > **Post image to Instagram + Threads (Recto)** > Run workflow. The first card post goes
   live on both.
3. Replies, safely: Settings > Secrets and variables > Actions > **Variables** > `DRY_RUN` = `1`.
   Leave a test comment ("how much is it?") from another account, run **Reply to comments (Recto)**,
   and read the log: it shows each comment and the reply it would send. Happy? Delete `DRY_RUN`.

## The reply bot
It answers when a comment matches a topic in its knowledge base: pricing and the free trial,
payment methods, Kurdish and Arabic, privacy and encryption, sharing and links, reading analytics,
PDF export, pasting from Illustrator, comparisons (Canva, DocSend...), brand kit and templates,
blocks (scope, pricing tables, signatures...), page sizes, Unsplash and icons, invoices, folio,
teams, how to start, bug reports, and thanks (never when the comment sounds doubtful).

- Opinions, tags, emoji and anything it doesn't know get **no reply**. Those are the conversations
  that build the community, so answer them yourself.
- Max 10 replies per platform per run; each comment answered once (`replied.json`).
- Topics, keywords and replies are at the top of `replies.py`. **When a price or feature changes in
  the app, change it there too**, then run `python3 test_replies.py`.

## Notes
- When a queue runs empty, the run fails on purpose and GitHub emails you. Add a new batch.
- Post times live in cron-job.org, not in the workflow files. If its token expires, posting stops
  and the job shows `401`: make a new token and paste it into the 3 jobs.
- If a thread breaks halfway, the opener stays live and is removed from the queue, so a rerun
  never double posts.
- Fonts: Libre Baskerville (SIL Open Font License, `fonts/OFL.txt`). GC Commune is licensed and stays
  out of git (`.gitignore`).
