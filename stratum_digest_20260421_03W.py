#!/usr/bin/env python3
"""
STRATUM v0.4 — GitHub Actions Version
Keys from GitHub Secrets via environment variables.
"""

import json, smtplib, feedparser, requests, re, time
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION  (keys injected by subclass files)
# ══════════════════════════════════════════════════════════════════

import os
ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
NEWSAPI_KEY          = os.environ["NEWSAPI_KEY"]
TWITTER_BEARER_TOKEN = os.environ["TWITTER_BEARER_TOKEN"]
TELEGRAM_BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID     = os.environ["TELEGRAM_CHAT_ID"]
GMAIL_FROM           = os.environ["GMAIL_FROM"]
GMAIL_TO             = os.environ["GMAIL_TO"]
GMAIL_PASS           = os.environ["GMAIL_PASS"]

# Bluesky — no auth needed for public feed reading
BLUESKY_HANDLES = [
    "bbc.com",
    "reuters.com",
    "apnews.com",
    "ft.com",
    "bloomberg.com",
    "theguardian.com",
    "aljazeera.com",
    "nikkei.com",
    "dw.com",
]
BLUESKY_WEIGHT = 82

# ══════════════════════════════════════════════════════════════════
#  LOAD SOURCES FROM sources.json
# ══════════════════════════════════════════════════════════════════

def load_sources():
    try:
        with open("sources.json", "r") as f:
            cfg = json.load(f)
        print("  ✓ Loaded sources.json")
        return cfg
    except FileNotFoundError:
        print("  ⚠ sources.json not found — using empty source lists")
        return {"newsapi_sources": [], "rss_sources": [], "twitter_accounts": [], "bluesky_handles": [], "telegram_channels": []}
    except Exception as e:
        print(f"  ✗ Error loading sources.json: {e}")
        return {"newsapi_sources": [], "rss_sources": [], "twitter_accounts": [], "bluesky_handles": [], "telegram_channels": []}

SOURCES            = load_sources()
NEWSAPI_SOURCES    = SOURCES.get("newsapi_sources", [])
RSS_SOURCES        = SOURCES.get("rss_sources", [])
TWITTER_ACCOUNTS   = SOURCES.get("twitter_accounts", [])
BLUESKY_HANDLES    = [s["handle"] for s in SOURCES.get("bluesky_handles", [])]
TELEGRAM_CHANNELS  = SOURCES.get("telegram_channels", [])


MAX_PER_SOURCE     = 8
MAX_TOTAL_ITEMS    = 150
MAX_TWEETS_PER_RUN = 50
MAX_BREAKING_SHOWN = 40

RSS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def parse_entry_time(entry):
    """Extract published datetime from feedparser entry. Returns UTC datetime or None."""
    for field in ("published_parsed", "updated_parsed"):
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None

def is_recent(entry, max_hours):
    """Return True if entry was published within max_hours."""
    pub = parse_entry_time(entry)
    if pub is None:
        return True   # No timestamp → don't filter out (assume recent)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours)
    return pub >= cutoff

# ══════════════════════════════════════════════════════════════════
#  INGESTION — NEWSAPI
# ══════════════════════════════════════════════════════════════════

def fetch_newsapi():
    items      = []
    source_ids = ",".join(s["id"] for s in NEWSAPI_SOURCES)
    source_map = {s["id"]: s for s in NEWSAPI_SOURCES}
    try:
        r    = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={"sources": source_ids, "pageSize": MAX_PER_SOURCE * len(NEWSAPI_SOURCES), "apiKey": NEWSAPI_KEY},
            timeout=10
        )
        data = r.json()
        if data.get("status") != "ok":
            print(f"  ⚠ NewsAPI: {data.get('message','unknown')}")
            return []
        for article in data.get("articles", []):
            src_id   = article.get("source", {}).get("id", "")
            src_name = article.get("source", {}).get("name", src_id)
            meta     = source_map.get(src_id, {"weight": 85})
            title    = (article.get("title") or "").strip()
            if title and "[Removed]" not in title:
                items.append({
                    "source":      src_name,
                    "weight":      meta["weight"],
                    "type":        "WIRE/PUB",
                    "source_type": "news",
                    "title":       title,
                    "summary":     (article.get("description") or "")[:300],
                    "url":         article.get("url", ""),
                    "platform":    "newsapi",
                })
        print(f"  ✓ NewsAPI: {len(items)} articles")
    except Exception as e:
        print(f"  ✗ NewsAPI failed: {e}")
    return items


# ══════════════════════════════════════════════════════════════════
#  INGESTION — RSS (with recency filter)
# ══════════════════════════════════════════════════════════════════

def fetch_rss():
    items = []
    for src in RSS_SOURCES:
        count   = 0
        skipped = 0
        max_h   = src.get("hours", 24)
        try:
            r    = requests.get(src["url"], headers=RSS_HEADERS, timeout=12)
            feed = feedparser.parse(r.content)
            if not feed.entries:
                feed = feedparser.parse(src["url"])

            for entry in feed.entries[:MAX_PER_SOURCE * 2]:  # Fetch more, filter down
                if not is_recent(entry, max_h):
                    skipped += 1
                    continue
                title = (entry.get("title") or "").strip()
                if title:
                    summary = entry.get("summary") or entry.get("description") or ""
                    summary = re.sub(r"<[^>]+>", " ", summary)[:300].strip()
                    items.append({
                        "source":      src["name"],
                        "weight":      src["weight"],
                        "type":        "RSS",
                        "source_type": "news",
                        "title":       title,
                        "summary":     summary,
                        "url":         entry.get("link", ""),
                        "platform":    "rss",
                    })
                    count += 1
                    if count >= MAX_PER_SOURCE:
                        break

            age_tag = f"{max_h}h"
            print(f"  ✓ {src['name']}: {count} items (filter: {age_tag}, skipped {skipped} old)")
        except Exception as e:
            print(f"  ✗ {src['name']}: {e}")
    return items


# ══════════════════════════════════════════════════════════════════
#  INGESTION — BLUESKY
# ══════════════════════════════════════════════════════════════════

def fetch_bluesky():
    """Fetch recent posts from BlueSky public API — no auth needed."""
    items   = []
    cutoff  = datetime.now(timezone.utc) - timedelta(hours=24)

    for handle in BLUESKY_HANDLES:
        try:
            # Resolve handle to DID
            r = requests.get(
                "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle",
                params={"handle": handle}, timeout=8
            )
            if r.status_code != 200:
                continue
            did = r.json().get("did")
            if not did:
                continue

            # Fetch author feed
            r2 = requests.get(
                "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed",
                params={"actor": did, "limit": 20}, timeout=8
            )
            if r2.status_code != 200:
                continue

            feed  = r2.json().get("feed", [])
            count = 0
            for post_obj in feed:
                post = post_obj.get("post", {})
                record = post.get("record", {})

                # Recency check
                created = record.get("createdAt", "")
                try:
                    pub = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if pub < cutoff:
                        continue
                except Exception:
                    pass

                text = record.get("text", "").strip()
                if not text or len(text) < 60:
                    continue
                # Skip replies
                if record.get("reply"):
                    continue

                uri   = post.get("uri", "")
                parts = uri.split("/")
                post_id = parts[-1] if parts else ""
                url = f"https://bsky.app/profile/{handle}/post/{post_id}" if post_id else ""

                items.append({
                    "source":   f"bsky:{handle}",
                    "weight":   BLUESKY_WEIGHT,
                    "type":     "BlueSky",
                    "title":    text[:280],
                    "summary":  "",
                    "platform": "bluesky",
                    "url":      url,
                    "handle":   handle,
                    "acct_type": "BlueSky",
                    "score":    tweet_newsworthiness(text, BLUESKY_WEIGHT),
                })
                count += 1
                if count >= 5:
                    break

            if count:
                print(f"  ✓ BlueSky @{handle}: {count} posts")

        except Exception as e:
            print(f"  ✗ BlueSky {handle}: {e}")

    # Filter by newsworthiness
    items = [i for i in items if i["score"] >= TWEET_MIN_SCORE]
    print(f"  ✓ BlueSky total: {len(items)} newsworthy posts")
    return items


# ══════════════════════════════════════════════════════════════════
#  INGESTION — TELEGRAM (public channels via t.me/s/)
# ══════════════════════════════════════════════════════════════════

def fetch_telegram():
    """Fetch recent posts from public Telegram channels via web preview."""
    items   = []
    cutoff  = datetime.now(timezone.utc) - timedelta(hours=24)

    for ch in TELEGRAM_CHANNELS:
        handle = ch["handle"].lstrip("@")
        name   = ch["name"]
        weight = ch["weight"]
        try:
            # Use t.me/s/ which returns HTML preview of public channels
            r = requests.get(
                f"https://t.me/s/{handle}",
                headers=RSS_HEADERS,
                timeout=10
            )
            if r.status_code != 200:
                continue

            # Extract message text from HTML using regex
            # Telegram preview wraps messages in <div class="tgme_widget_message_text">
            texts = re.findall(
                r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
                r.text, re.DOTALL
            )

            count = 0
            for raw_text in texts[:10]:
                # Strip HTML tags
                text = re.sub(r"<[^>]+>", " ", raw_text).strip()
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) < 40:
                    continue
                score = tweet_newsworthiness(text, weight)
                if score < TWEET_MIN_SCORE:
                    continue
                items.append({
                    "source":      f"TG:{name}",
                    "handle":      handle,
                    "weight":      weight,
                    "type":        "Telegram",
                    "source_type": "social",
                    "acct_type":   "Telegram",
                    "title":       text[:280],
                    "summary":     "",
                    "platform":    "telegram",
                    "score":       score,
                    "url":         f"https://t.me/{handle}",
                })
                count += 1
                if count >= 5:
                    break

            if count:
                print(f"  ✓ Telegram @{handle}: {count} posts")

        except Exception as e:
            print(f"  ✗ Telegram {handle}: {e}")

    items.sort(key=lambda x: x["score"], reverse=True)
    print(f"  ✓ Telegram total: {len(items)} newsworthy posts from {len(TELEGRAM_CHANNELS)} channels")
    return items


# ══════════════════════════════════════════════════════════════════
#  INGESTION — TWITTER/X (batched)
# ══════════════════════════════════════════════════════════════════

def tweet_newsworthiness(text, weight):
    score = weight * 0.38
    if re.search(r'\b(says|said|confirms|confirmed|announces|announced|reports|reported|breaking|BREAKING|warns|warned|strikes|struck|hits|hit|fires|fired|launches|launched)\b', text, re.I):
        score += 10
    if re.search(r'\b(billion|million|trillion|\$|€|£|₹|bps|%)\b', text, re.I):
        score += 8
    if re.search(r'\b(president|prime minister|minister|central bank|fed|rbi|ecb|boj|nato|un|opec|ceo|government|pentagon|kremlin|white house)\b', text, re.I):
        score += 6
    if re.search(r'\d+', text):
        score += 5
    if re.search(r'[A-Z]{3,}', text):
        score += 4
    if len(text) > 150:
        score += 3
    if re.search(r'^\s*if\b', text, re.I):          score -= 18
    if re.search(r'\b(1\)|2\)|3\)|\(1\)|\(2\))\b', text): score -= 12
    if re.search(r'\b(would|could|might|should|may|perhaps|maybe)\b', text, re.I): score -= 8
    if re.search(r'\b(think|believe|seems|appears|feel|suggest|argument|argue)\b', text, re.I): score -= 8
    if text.count('?') > 0:             score -= 10
    if text.count('#') > 2:             score -= 5
    if re.search(r'^\s*[a-z]', text):  score -= 5
    return min(65, max(0, round(score)))

TWEET_MIN_SCORE = 20


def fetch_twitter():
    items = []
    if not TWITTER_BEARER_TOKEN or TWITTER_BEARER_TOKEN == "your-bearer-token":
        print("  ⚠ Twitter: Bearer token not set, skipping")
        return []

    handles    = [a["handle"] for a in TWITTER_ACCOUNTS]
    handle_map = {a["handle"].lower(): a for a in TWITTER_ACCOUNTS}
    start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    suffix     = " -is:retweet -is:reply -is:quote lang:en"

    BATCH_SIZE = 13
    batches    = [handles[i:i+BATCH_SIZE] for i in range(0, len(handles), BATCH_SIZE)]
    all_tweets = []
    all_users  = {}

    for batch in batches:
        query = " OR ".join(f"from:{h}" for h in batch) + suffix
        try:
            r = requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers={"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"},
                params={
                    "query":        query,
                    "max_results":  MAX_TWEETS_PER_RUN,
                    "start_time":   start_time,
                    "tweet.fields": "created_at,text,author_id,id",
                    "expansions":   "author_id",
                    "user.fields":  "name,username",
                },
                timeout=15
            )
            if r.status_code != 200:
                print(f"  ✗ Twitter batch error {r.status_code}: {r.text[:150]}")
                continue
            data = r.json()
            all_tweets.extend(data.get("data", []))
            for u in data.get("includes", {}).get("users", []):
                all_users[u["id"]] = u
        except Exception as e:
            print(f"  ✗ Twitter batch failed: {e}")

    skipped = 0
    for tweet in all_tweets:
        user       = all_users.get(tweet.get("author_id", ""), {})
        username   = user.get("username", "unknown")
        meta       = handle_map.get(username.lower(), {"weight": 70, "type": "X"})
        text       = tweet.get("text", "").strip()
        tweet_id   = tweet.get("id", "")
        clean_text = re.sub(r"https?://\S+", "", text).strip()

        if clean_text.startswith("@"):  skipped += 1; continue
        if len(clean_text) < 80:        skipped += 1; continue

        score = tweet_newsworthiness(clean_text, meta["weight"])
        if score < TWEET_MIN_SCORE:     skipped += 1; continue

        tweet_url = f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else ""
        items.append({
            "source":      f"@{username}",
            "handle":      username,
            "weight":      meta["weight"],
            "type":        f"X/{meta['type']}",
            "source_type": "social",
            "acct_type":   meta["type"],
            "title":       clean_text[:280],
            "summary":     "",
            "score":       score,
            "url":         tweet_url,
            "platform":    "twitter",
        })

    # Deduplicate and sort
    seen, unique = set(), []
    for item in items:
        key = item["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    unique.sort(key=lambda x: x["score"], reverse=True)

    print(f"  ✓ Twitter/X: {len(unique)} newsworthy tweets ({skipped} skipped) from {len(batches)} batches")
    return unique


# ══════════════════════════════════════════════════════════════════
#  FETCH ALL
# ══════════════════════════════════════════════════════════════════

def fetch_all():
    print("\n[1/3] Fetching headlines...")
    newsapi_items   = fetch_newsapi()
    rss_items       = fetch_rss()
    twitter_items   = fetch_twitter()
    bluesky_items   = fetch_bluesky()
    telegram_items  = fetch_telegram()

    social_items    = twitter_items + bluesky_items + telegram_items
    all_items       = newsapi_items + rss_items + social_items

    seen, unique = set(), []
    for item in all_items:
        key = item["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"      {len(unique)} unique items after dedup")
    return unique[:MAX_TOTAL_ITEMS], social_items


# ══════════════════════════════════════════════════════════════════
#  CLAUDE ANALYSIS — topic-clustered
# ══════════════════════════════════════════════════════════════════

ANALYSIS_PROMPT = """You are STRATUM, an AI producing a verified signal digest for a sophisticated investor and geopolitical risk monitor.

You receive items from a curated source whitelist. Each has a credibility weight (0-100) and a URL.
- 90+: Wire services (Reuters, AP, Bloomberg)
- 80-89: Named journalists, top publications
- 70-79: Credible aggregators, regional press
- X/ or BlueSky prefix: Social posts — fast but unverified unless corroborated

SCORING RULES:
- Single social post only: 10-25
- Single named journalist (80+): 30-50
- Social post + 1 wire corroboration: 50-65
- 2+ independent strong sources (85+): 65-80
- Wire consensus (Reuters + AP + Bloomberg): 80-95
- Sources contradict: deduct 15-20 points

YOUR TASK:
1. Identify ALL DISTINCT story clusters — include EVERY story, even single-source ones
2. MINIMUM SCORE IS 20 — include all clusters with a verification score of 20 or higher
3. For each cluster assign a TOPIC LABEL (3-5 words, e.g. "US-Iran Military Conflict", "RBI Rate Policy", "OPEC Oil Cuts")
4. For each cluster list ALL social posts (X/BlueSky) that relate to it under social_signals — make sure ALL relevant social posts are matched to clusters, not dropped
5. Assign DOMAIN: markets / macro / geopolitics / commodities / corporate / india / japan / europe / middleeast
6. Compute VERIFICATION SCORE (0-100) per scoring rules above
7. Write a sharp 2-sentence VERIFIED SUMMARY
8. Write a 1-sentence SIGNAL for investor/risk manager
9. Set TREND: "rising" / "falling" / "stable"
10. Flag breaking_on_social: true if story appeared on social before wire services
11. Pick the BEST source URL for this story from the items provided — use the highest-credibility source that has a URL. Set as source_url.
12. STANDALONE SOCIAL STORIES: For any social post (X/BlueSky) with a news score ≥ 30 that has NO corroboration from wire/RSS sources, create a standalone story entry with:
    - standalone_social: true
    - score: the social post's news score (max 65)
    - context: a 1-sentence explanation of why this is worth watching even unverified
    - summary: the tweet/post content paraphrased
    - signal: what to watch for if this turns out to be true

Respond ONLY with valid JSON, no markdown:
{
  "stories": [
    {
      "rank": 1,
      "score": 94,
      "topic": "US-Iran Military Conflict",
      "domain": "geopolitics",
      "headline": "Max 12 words, sharp and specific",
      "summary": "Two-sentence synthesis.",
      "signal": "One-sentence implication.",
      "sources": ["Reuters", "@DeItaone"],
      "source_url": "https://reuters.com/...",
      "standalone_social": false,
      "context": "",
      "social_signals": [
        {"handle": "DeItaone", "platform": "twitter", "text": "Netanyahu confirms...", "score": 57, "url": "https://..."},
        {"handle": "bbc.com",  "platform": "bluesky", "text": "F-15 shot down...",    "score": 61, "url": "https://..."}
      ],
      "trend": "rising",
      "breaking_on_social": true
    },
    {
      "rank": 5,
      "score": 42,
      "topic": "Unverified Market Signal",
      "domain": "markets",
      "headline": "Max 12 words",
      "summary": "Paraphrased post content.",
      "signal": "What to watch for if this proves true.",
      "sources": ["@KobeissiLetter"],
      "source_url": "",
      "standalone_social": true,
      "context": "One sentence on why this is worth watching despite being unverified.",
      "social_signals": [
        {"handle": "KobeissiLetter", "platform": "twitter", "text": "...", "score": 42, "url": "https://..."}
      ],
      "trend": "stable",
      "breaking_on_social": true
    }
  ]
}

Sort by score descending. Include ALL clusters with score ≥ 20."""


def analyze_with_claude(items, social_items, client):
    print("\n[2/3] Analyzing with Claude...")

    # Build social lookup for Claude to reference
    social_block = "\n".join(
        f"  SOCIAL [{i['platform'].upper()}] @{i.get('handle','?')} (wt:{i['weight']}, score:{i.get('score',0)}) — {i['title'][:200]}"
        + (f" | URL: {i.get('url','')}" if i.get('url') else "")
        for i in social_items[:60]
    )

    headlines_block = "\n".join(
        f"[{i+1}] {item['source']} (wt:{item['weight']}, {item['type']}) — {item['title']}"
        + (f" | URL: {item['url']}" if item.get("url") else "")
        + (f"\n    {item['summary']}" if item.get("summary") else "")
        for i, item in enumerate(items)
    )

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": (
                ANALYSIS_PROMPT
                + "\n\nALL ITEMS (RSS + NewsAPI):\n" + headlines_block
                + "\n\nSOCIAL SIGNALS (X + BlueSky) — match these to story clusters:\n" + social_block
            )
        }]
    )

    raw = msg.content[0].text.strip().lstrip("```json").rstrip("```").strip()

    # Try direct parse first
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract partial valid JSON — find stories array even if truncated
        try:
            # Find the stories array start
            stories_start = raw.find('"stories"')
            if stories_start > 0:
                # Find last complete story object by looking for last complete },
                truncated = raw[:raw.rfind('},\n    {')]
                if truncated:
                    # Close the array and object
                    fixed = truncated + '}\n  ]\n}'
                    result = json.loads(fixed)
                else:
                    result = {"stories": []}
            else:
                result = {"stories": []}
        except Exception:
            result = {"stories": []}

    stories = result.get("stories", [])
    print(f"      {len(stories)} topic clusters · top score: {stories[0]['score'] if stories else 'n/a'}")
    return stories


# ══════════════════════════════════════════════════════════════════
#  EMAIL RENDERING — topic-clustered
# ══════════════════════════════════════════════════════════════════

DOMAIN_COLORS = {
    "markets":    "#0369a1",
    "macro":      "#7c3aed",
    "geopolitics":"#b45309",
    "commodities":"#065f46",
    "corporate":  "#c2410c",
    "india":      "#be185d",
    "japan":      "#dc2626",
    "europe":     "#1d4ed8",
    "middleeast": "#b45309",
}

def score_color(s):
    if s >= 80: return "#16a34a"
    if s >= 60: return "#0369a1"
    if s >= 35: return "#d97706"
    return "#dc2626"

def score_bg(s):
    if s >= 80: return "#f0fdf4"
    if s >= 60: return "#eff6ff"
    if s >= 35: return "#fffbeb"
    return "#fef2f2"

def score_label(s):
    if s >= 80: return "VERIFIED"
    if s >= 60: return "HIGH"
    if s >= 35: return "DEVELOPING"
    return "UNVERIFIED"


def render_social_signal(sig):
    """Render a single social signal (tweet/bsky) inside a topic cluster."""
    handle   = sig.get("handle", "?")
    platform = sig.get("platform", "twitter")
    score    = sig.get("score", 0)
    text     = sig.get("text", "")[:200]
    url      = sig.get("url", "")
    sc       = "#d97706" if score >= 55 else ("#b45309" if score >= 40 else "#dc2626")
    plat_tag = "X" if platform == "twitter" else "BSKY"
    plat_col = "#0d9488" if platform == "bluesky" else "#0d9488"
    link     = f'<a href="{url}" style="font-size:9px;color:#0369a1;text-decoration:none;font-weight:700;font-family:Courier New,monospace;">VIEW →</a>' if url else ""

    return f"""<div style="background:#f8fafc;border-radius:4px;padding:8px 10px;margin-bottom:5px;border-left:2px solid {sc};font-family:Arial,sans-serif;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <span style="font-family:'Courier New',Courier,monospace;font-size:9px;font-weight:700;color:{plat_col};">{plat_tag} · @{handle}</span>
    <div style="display:flex;gap:6px;align-items:center;">
      <span style="font-family:'Courier New',Courier,monospace;font-size:9px;color:{sc};font-weight:700;">[{score}]</span>
      <span style="font-family:'Courier New',Courier,monospace;font-size:8px;background:#fef2f2;color:#dc2626;padding:1px 5px;border-radius:2px;font-weight:700;">UNVERIFIED</span>
      {link}
    </div>
  </div>
  <div style="font-size:12px;color:#374151;line-height:1.55;">{text}</div>
</div>"""


def render_topic_cluster(story):
    """Render a full topic cluster — verified story + its social signals."""
    sc          = score_color(story["score"])
    sbg         = score_bg(story["score"])
    dc          = DOMAIN_COLORS.get(story.get("domain", "markets"), "#475569")
    trend       = story.get("trend", "stable")
    trend_sym   = "▲" if trend == "rising" else ("▼" if trend == "falling" else "─")
    trend_color = "#16a34a" if trend == "rising" else ("#dc2626" if trend == "falling" else "#94a3b8")
    sources_str = " · ".join(story.get("sources", []))
    label       = score_label(story["score"])
    topic       = story.get("topic", "")
    social_sigs = story.get("social_signals", [])

    social_html = "".join(render_social_signal(s) for s in social_sigs[:5])
    social_block = f"""<div style="margin-top:10px;padding-top:10px;border-top:1px solid #f1f5f9;">
      <div style="font-family:'Courier New',Courier,monospace;font-size:8px;color:#94a3b8;letter-spacing:0.5px;margin-bottom:6px;">⚡ SOCIAL SIGNALS — {len(social_sigs)} post{'s' if len(social_sigs)!=1 else ''}</div>
      {social_html}
    </div>""" if social_sigs else ""

    bsoc_badge = '<span style="font-size:9px;background:#e0f2fe;color:#0369a1;padding:1px 6px;border-radius:2px;margin-left:6px;font-weight:700;">BROKE ON SOCIAL</span>' if story.get("breaking_on_social") else ""

    return f"""
<div style="background:#ffffff;border-radius:6px;margin-bottom:12px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);font-family:Arial,sans-serif;">
  <div style="display:flex;">
    <!-- Score column -->
    <div style="width:72px;min-width:72px;background:{sbg};border-right:3px solid {sc};display:flex;flex-direction:column;align-items:center;justify-content:center;padding:18px 4px;text-align:center;">
      <div style="font-family:'Courier New',Courier,monospace;font-size:28px;font-weight:700;color:{sc};line-height:1;">{story['score']}</div>
      <div style="font-family:'Courier New',Courier,monospace;font-size:7px;color:{sc};letter-spacing:0.8px;margin-top:2px;opacity:0.8;">{label}</div>
      <div style="font-size:14px;color:{trend_color};margin-top:8px;font-weight:700;">{trend_sym}</div>
    </div>
    <!-- Content -->
    <div style="flex:1;padding:14px 16px;min-width:0;">
      <div style="margin-bottom:6px;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
        <span style="font-family:'Courier New',Courier,monospace;font-size:9px;font-weight:700;letter-spacing:1px;color:{dc};background:{dc}15;padding:2px 8px;border-radius:2px;">{story.get('domain','').upper()}</span>
        <span style="font-family:'Courier New',Courier,monospace;font-size:9px;font-weight:600;color:#64748b;background:#f1f5f9;padding:2px 8px;border-radius:2px;">{topic}</span>
        {bsoc_badge}
        <span style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#94a3b8;margin-left:4px;">{sources_str}</span>
      </div>
      <div style="font-family:Georgia,'Times New Roman',serif;font-size:16px;font-weight:700;color:#0f172a;line-height:1.4;margin-bottom:8px;">{story['headline']}</div>
      <div style="font-size:13px;color:#475569;line-height:1.7;margin-bottom:10px;">{story['summary']}</div>
      <div style="font-size:12px;color:#64748b;border-left:3px solid {sc};padding-left:10px;font-style:italic;">
        <span style="font-family:'Courier New',Courier,monospace;font-size:8px;color:{sc};font-style:normal;font-weight:700;letter-spacing:0.5px;">SIGNAL · </span>{story.get('signal','')}
      </div>
      {social_block}
    </div>
    <!-- Rank -->
    <div style="width:26px;min-width:26px;display:flex;align-items:flex-start;justify-content:center;padding-top:14px;">
      <span style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#cbd5e1;">#{story['rank']}</span>
    </div>
  </div>
</div>"""


def build_html_email(stories, social_items):
    ist_offset     = timedelta(hours=5, minutes=30)
    now_ist        = datetime.now(timezone.utc) + ist_offset
    now_str        = now_ist.strftime("%d %b %Y · %H:%M IST")
    verified_count = sum(1 for s in stories if s["score"] >= 80)
    avg_score      = round(sum(s["score"] for s in stories) / len(stories)) if stories else 0
    broke_on_s     = sum(1 for s in stories if s.get("breaking_on_social"))
    twitter_count  = sum(1 for i in social_items if i.get("platform") == "twitter")
    bsky_count     = sum(1 for i in social_items if i.get("platform") == "bluesky")

    stories_html = "".join(render_topic_cluster(s) for s in stories)
    bsoc_note    = f'<span style="color:#ea580c;font-weight:700;">{broke_on_s} broke on social · </span>' if broke_on_s else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<div style="max-width:1150px;margin:0 auto;padding:20px 16px;">

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:18px 24px;margin-bottom:16px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
    <tr>
      <td>
        <div style="font-family:'Courier New',Courier,monospace;font-size:22px;font-weight:700;letter-spacing:5px;color:#0f172a;">STRATUM</div>
        <div style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#94a3b8;letter-spacing:2px;margin-top:3px;">VERIFIED SIGNAL DIGEST v0.4</div>
      </td>
      <td style="text-align:right;vertical-align:top;">
        <div style="font-family:'Courier New',Courier,monospace;font-size:11px;color:#64748b;">{now_str}</div>
        <div style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#94a3b8;margin-top:4px;">
          {bsoc_note}{len(stories)} TOPICS · {verified_count} VERIFIED · AVG {avg_score} · X:{twitter_count} BSKY:{bsky_count}
        </div>
      </td>
    </tr>
  </table>

  <!-- Topic clusters — full width, social signals embedded -->
  <div style="font-family:'Courier New',Courier,monospace;font-size:10px;font-weight:700;color:#64748b;letter-spacing:2px;margin-bottom:10px;padding:0 4px;">
    ✓ VERIFIED DIGEST · TOPIC-CLUSTERED · SOCIAL SIGNALS EMBEDDED
  </div>
  {stories_html}

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;padding:14px 0;">
    <tr>
      <td style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#cbd5e1;">
        <span style="color:#16a34a;">■</span> ≥80 VERIFIED &nbsp;
        <span style="color:#0369a1;">■</span> 60–79 HIGH &nbsp;
        <span style="color:#d97706;">■</span> 35–59 DEVELOPING &nbsp;
        <span style="color:#dc2626;">■</span> &lt;35 LOW &nbsp;·&nbsp;
        RSS: 12h fast / 24h analysis &nbsp;·&nbsp; X + BlueSky: 24h
      </td>
      <td style="text-align:right;font-family:'Courier New',Courier,monospace;font-size:9px;color:#cbd5e1;">STRATUM v0.4</td>
    </tr>
  </table>

</div>
</body></html>"""


# ══════════════════════════════════════════════════════════════════
#  TELEGRAM — topic-clustered
# ══════════════════════════════════════════════════════════════════

def score_emoji(s):
    if s >= 80: return "🟢"
    if s >= 60: return "🔵"
    if s >= 35: return "🟡"
    return "🔴"


def build_telegram_message(stories):
    ist_offset = timedelta(hours=5, minutes=30)
    now_ist    = datetime.now(timezone.utc) + ist_offset
    now_str    = now_ist.strftime("%d %b · %H:%M IST")
    verified_count = sum(1 for s in stories if s["score"] >= 80)
    avg_score      = round(sum(s["score"] for s in stories) / len(stories)) if stories else 0

    lines = []
    lines.append(f"*STRATUM* | {now_str}")
    lines.append(f"_{len(stories)} topics · {verified_count} verified · Avg {avg_score}_")
    lines.append("")

    for s in stories:
        em     = score_emoji(s["score"])
        topic  = s.get("topic", s.get("domain", "").upper())[:40]
        score  = s["score"]
        hl     = s["headline"][:80]
        signal = s.get("signal", "")[:120]
        bsoc   = " _(social)_" if s.get("breaking_on_social") else ""
        lines.append(f"{em} *[{score}] {hl}*{bsoc}")
        lines.append(f"_{topic} · {signal}_")
        lines.append("")

    lines.append("─────────────────")
    lines.append(f"_Full digest at stratum.streamlit.app_")
    return "\n".join(lines)


def send_telegram(message):
    """Send Telegram message, splitting into chunks if over 4096 chars."""
    LIMIT = 4000
    chunks = []
    if len(message) <= LIMIT:
        chunks = [message]
    else:
        # Split at double newlines to keep story blocks intact
        parts = message.split("\n\n")
        current = ""
        for part in parts:
            if len(current) + len(part) + 2 <= LIMIT:
                current += part + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = part + "\n\n"
        if current:
            chunks.append(current.strip())

    for i, chunk in enumerate(chunks):
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id":    TELEGRAM_CHAT_ID,
                    "text":       chunk,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=10
            )
            if r.status_code == 200:
                print(f"      ✓ Telegram part {i+1}/{len(chunks)} sent")
            else:
                print(f"      ✗ Telegram error {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"      ✗ Telegram failed: {e}")


# ══════════════════════════════════════════════════════════════════
#  EMAIL DELIVERY
# ══════════════════════════════════════════════════════════════════

def send_email(html_body, stories):
    ist_offset = timedelta(hours=5, minutes=30)
    now_str    = (datetime.now(timezone.utc) + ist_offset).strftime("%d %b %H:%M IST")
    top     = stories[0] if stories else {}
    subject = f"STRATUM · {now_str} · [{top.get('score','?')}] {top.get('headline','Top stories')[:50]}"
    msg     = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_FROM
    msg["To"]      = GMAIL_TO
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_FROM, GMAIL_PASS)
        server.sendmail(GMAIL_FROM, GMAIL_TO, msg.as_string())
    print(f"      ✓ Email sent → {GMAIL_TO}")
    print(f"      Subject: {subject}")


# ══════════════════════════════════════════════════════════════════
#  DIGEST HISTORY — write to digests.json
# ══════════════════════════════════════════════════════════════════

DIGESTS_FILE  = "digests.json"
MAX_DIGESTS   = 35   # 7 days × 5 runs/day

def strip_html(text):
    """Remove any HTML tags from a string."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).strip()

def clean_story(story):
    """Ensure all text fields in a story are HTML-free before saving."""
    for field in ("headline", "summary", "signal", "topic"):
        if field in story:
            story[field] = strip_html(story[field])
    # Clean social signals too
    for sig in story.get("social_signals", []):
        if "text" in sig:
            sig["text"] = strip_html(sig["text"])
    return story

def save_digest(stories, social_items, all_items=None):
    """Append current digest to digests.json, keep last 35. Move older to archives."""
    try:
        with open(DIGESTS_FILE, "r") as f:
            existing = json.load(f)
        # Handle both old flat format and new format with archives
        if isinstance(existing, dict):
            history  = existing.get("digests", [])
            archives = existing.get("archives", [])
        else:
            history  = existing
            archives = []
    except Exception:
        history  = []
        archives = []

    # Clean all stories before saving
    clean_stories = [clean_story(s) for s in stories]

    # IST = UTC + 5:30
    ist_offset = timedelta(hours=5, minutes=30)
    now_ist    = datetime.now(timezone.utc) + ist_offset

    tg_count = sum(1 for i in social_items if i.get("platform") == "telegram")
    tw_count = sum(1 for i in social_items if i.get("platform") == "twitter")
    bk_count = sum(1 for i in social_items if i.get("platform") == "bluesky")

    LOCAL_KW = {
        "maharashtra","mumbai","thane","pune","nagpur","nashik",
        "navi mumbai","bmc","mmc","mhada","mmrda","konkan",
        "vidarbha","marathwada","aurangabad","shiv sena","ncp",
        "uddhav","fadnavis","devendra","eknath shinde",
    }

    # Raw local items — individual RSS/NewsAPI headlines mentioning Maharashtra/Mumbai/Thane
    raw_local = []
    for item in all_items:
        text = (item.get("title","") + " " + item.get("summary","")).lower()
        if any(kw in text for kw in LOCAL_KW):
            raw_local.append({
                "source":   item.get("source",""),
                "title":    item.get("title",""),
                "summary":  item.get("summary",""),
                "url":      item.get("url",""),
                "platform": item.get("platform",""),
                "weight":   item.get("weight",0),
            })

    digest = {
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "timestamp_ist": now_ist.strftime("%d %b %Y · %H:%M IST"),
        "story_count":   len(clean_stories),
        "avg_score":     round(sum(s["score"] for s in clean_stories) / len(clean_stories)) if clean_stories else 0,
        "stories":       clean_stories,
        "social_count":  len(social_items),
        "tg_count":      tg_count,
        "tw_count":      tw_count,
        "bk_count":      bk_count,
        "local_items":   raw_local,
    }

    history.insert(0, digest)

    # Move digests older than 7 days to archives
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent   = [d for d in history if d.get("timestamp", "") >= cutoff_ts]
    to_archive = [d for d in history if d.get("timestamp", "") < cutoff_ts]
    archives = to_archive + archives
    archives = archives[:200]  # Keep max 200 archived digests

    # Keep last 35 in main feed
    recent = recent[:MAX_DIGESTS]

    with open(DIGESTS_FILE, "w") as f:
        json.dump({"digests": recent, "archives": archives}, f, indent=2)

    print(f"      ✓ Saved digest ({len(recent)} recent, {len(archives)} archived)")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    sep = "─" * 52
    print(f"\n{sep}")
    print(f"  STRATUM v0.4  ·  {datetime.now().strftime('%d %b %Y  %H:%M')}")
    print(sep)

    all_items, social_items = fetch_all()
    if not all_items:
        print("  ✗ No items fetched. Check your API keys.")
        return

    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    stories = analyze_with_claude(all_items, social_items, client)
    if not stories:
        print("  ✗ Claude returned no stories.")
        return

    print("\n[3/3] Sending digest...")
    html = build_html_email(stories, social_items)
    send_email(html, stories)
    tg_msg = build_telegram_message(stories)
    send_telegram(tg_msg)

    # Save to digests.json (GitHub Actions will commit this)
    save_digest(stories, social_items, all_items)

    print(f"\n  Topics: {len(stories)} · Social signals: {len(social_items)}")
    for s in stories[:3]:
        bsoc = " [SOCIAL]" if s.get("breaking_on_social") else ""
        print(f"    [{s['score']}]{bsoc} {s['headline']}")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
