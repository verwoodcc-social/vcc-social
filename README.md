# Verwood CC — Play-Cricket to social media

Turns Verwood CC's Play-Cricket results and fixtures into club-branded graphics and queues
them in Metricool (Facebook + Instagram) as **drafts**. Nothing goes live until someone
opens the draft in Metricool's planner and schedules or publishes it. (Metricool's
approval workflow needs a paid plan; drafts give the same check on the free plan.)

| Post | Run | Content | Mode |
|---|---|---|---|
| Fixtures | Friday 08:00 | All Verwood fixtures in the next 7 days (Fri–Thu) | `fixtures` |
| Results round-up | Monday 08:00 | All Verwood results from the previous 7 days (Mon–Sun) | `roundup` |
| Match result | Daily 07:00 | One post per match played **yesterday** that has a result and a scorecard | `matches` |

Each post is saved as a Metricool draft with a suggested publish time one hour after the run.
A match whose scorecard is entered after the 07:00 run the next day gets no individual
post, but still appears in Monday's round-up.

## How a run works

1. **Read Play-Cricket** in the club's Chrome (Play-Cricket blocks automated cloud readers):
   - Fixtures: open `https://verwood.play-cricket.com/Matches?tab=Weekly`, run `extract/weekly.js`, save output to `raw/fixtures.json`.
   - Results: open `https://verwood.play-cricket.com/Matches?tab=WeeklyResult`, run `extract/weekly.js`, save to `raw/results.json`.
   - Daily run only: run `python3 prepare.py matches raw/results.json` first; it prints yesterday's match ids
     (on stderr). For each id, open `https://verwood.play-cricket.com/website/results/<id>`, run
     `extract/scorecard.js`, save to `raw/scorecard_<id>.json`. If the output is cut off, re-read the `tables` in parts.
2. **Prepare**:
   - Friday: `python3 prepare.py fixtures raw/fixtures.json`
   - Monday: `python3 prepare.py roundup raw/results.json`
   - Daily: `python3 prepare.py matches raw/results.json raw/scorecard_*.json`

   Prints a JSON list of data files with captions. An empty list means nothing to post.
   Matches in progress or with no scorecard get no individual post.
3. **Render**: `python3 render.py data/<file>.json` → PNGs in `out/` (1080×1350; more than 6 rows becomes a carousel).
4. **Check** each PNG against the raw extract (teams, scores, result) before queueing.
5. **Publish images** to this repo under `posts/YYYY-MM-DD/` and use their raw.githubusercontent.com URLs.
6. **Save as a Metricool draft** (brand "Verwood Cricket Club", blogId 6985978) with
   `createScheduledPost` and `"draft": true`, networks Facebook (POST) + Instagram (POST), image URL(s) in `media`,
   alt text in `mediaAltText`, caption as `text`, publish time one hour after the run (Europe/London).
7. If there are no matches, post nothing.

## Rules

- **Juniors**: teams whose name contains U/Under + age, Girls, Boys, Daughters, Sons, All Stars or Dynamos
  show first name + surname initial only ("Ben T."). Open-age teams (e.g. Indoor C) show full names.
- Never post a score that isn't on Play-Cricket. If anything doesn't parse, skip that item and say so.

## Files

- `templates/` — `base.css` (club colours: navy #1A4192, silver #DBE2EA), `list.html`, `match.html`
- `assets/badge.svg` — the club badge (vector)
- `assets/fonts/` — Inter Display, embedded into every render
- `extract/` — page extractors to run in Chrome
- `data/sample_*.json` — example inputs
