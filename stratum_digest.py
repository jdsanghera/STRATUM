#!/usr/bin/env python3
"""
STRATUM v0.3 — GitHub Actions Version
Keys loaded from environment variables (GitHub Secrets).
Run via: GitHub Actions → Actions tab → STRATUM Digest → Run workflow
"""

import os

ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
NEWSAPI_KEY          = os.environ["NEWSAPI_KEY"]
TWITTER_BEARER_TOKEN = os.environ["TWITTER_BEARER_TOKEN"]
TELEGRAM_BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID     = os.environ["TELEGRAM_CHAT_ID"]
GMAIL_FROM           = os.environ["GMAIL_FROM"]
GMAIL_TO             = os.environ["GMAIL_TO"]
GMAIL_PASS           = os.environ["GMAIL_PASS"]

import json, smtplib, feedparser, requests, re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic

# ══════════════════════════════════════════════════════════════════
#  SOURCE CONFIGURATION
# ══════════════════════════════════════════════════════════════════

NEWSAPI_SOURCES = [
    {"id": "reuters",                 "name": "Reuters",         "weight": 95},
    {"id": "associated-press",        "name": "AP News",         "weight": 92},
    {"id": "bloomberg",               "name": "Bloomberg",       "weight": 93},
    {"id": "financial-times",         "name": "FT",              "weight": 90},
    {"id": "the-economist",           "name": "Economist",       "weight": 91},
    {"id": "the-wall-street-journal", "name": "WSJ",             "weight": 88},
    {"id": "cnbc",                    "name": "CNBC",            "weight": 86},
    {"id": "bbc-news",                "name": "BBC News",        "weight": 88},
    {"id": "the-guardian-uk",         "name": "The Guardian",    "weight": 82},
    {"id": "al-jazeera-english",      "name": "Al Jazeera",      "weight": 80},
]

RSS_SOURCES = [
    # ── INDIA — General ────────────────────────────────────────────
    {"name": "Times of India",        "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",            "weight": 80},
    {"name": "The Hindu",             "url": "https://www.thehindu.com/feeder/default.rss",                           "weight": 81},
    {"name": "Indian Express",        "url": "https://indianexpress.com/feed/",                                       "weight": 80},
    {"name": "NDTV News",             "url": "https://feeds.feedburner.com/ndtvnews-india-news",                      "weight": 79},
    # ── INDIA — Business ───────────────────────────────────────────
    {"name": "LiveMint Markets",      "url": "https://www.livemint.com/rss/markets",                                  "weight": 82},
    {"name": "LiveMint Companies",    "url": "https://www.livemint.com/rss/companies",                                "weight": 80},
    {"name": "Moneycontrol",          "url": "https://www.moneycontrol.com/rss/latestnews.xml",                       "weight": 78},
    {"name": "NDTV Profit",           "url": "https://feeds.feedburner.com/ndtvprofit-latest",                        "weight": 78},
    {"name": "Hindu Business",        "url": "https://www.thehindu.com/business/markets/feeder/default.rss",          "weight": 79},
    {"name": "CNBC TV18",             "url": "https://www.cnbctv18.com/commonfeeds/v1/eng/rss/business.xml",          "weight": 80},
    {"name": "ET Top Stories",        "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",           "weight": 81},
    # ── EUROPE ─────────────────────────────────────────────────────
    {"name": "DW Business",           "url": "https://rss.dw.com/rdf/rss-en-bus",                                     "weight": 82},
    {"name": "Euronews Business",     "url": "https://www.euronews.com/rss?level=theme&name=business",                "weight": 79},
    {"name": "Politico Europe",       "url": "https://www.politico.eu/feed/",                                         "weight": 81},
    # ── MIDDLE EAST ────────────────────────────────────────────────
    {"name": "The National (UAE)",    "url": "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml", "weight": 79},
    {"name": "Middle East Eye",       "url": "https://www.middleeasteye.net/rss",                                     "weight": 77},
    {"name": "Jerusalem Post",        "url": "https://www.jpost.com/rss/rssfeedsheadlines.aspx",                     "weight": 78},
    {"name": "Asharq Al-Awsat",       "url": "https://english.aawsat.com/rss",                                       "weight": 78},
    # ── JAPAN ──────────────────────────────────────────────────────
    {"name": "Nikkei Asia",           "url": "https://asia.nikkei.com/rss/feed/nar",                                  "weight": 85},
    {"name": "Japan Times",           "url": "https://www.japantimes.co.jp/feed/",                                    "weight": 80},
    # ── ASIA-PACIFIC ───────────────────────────────────────────────
    {"name": "S. China Morning Post", "url": "https://www.scmp.com/rss/91/feed",                                      "weight": 82},
    {"name": "Channel News Asia",     "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml",  "weight": 79},
]

TWITTER_ACCOUNTS = [
    # Fast aggregators
    {"handle": "MarioNawfal",     "weight": 72, "type": "Aggregator"},
    {"handle": "KobeissiLetter",  "weight": 78, "type": "Aggregator"},
    {"handle": "tier10k",         "weight": 74, "type": "Aggregator"},
    {"handle": "zerohedge",       "weight": 65, "type": "Aggregator"},
    {"handle": "spectatorindex",  "weight": 74, "type": "Aggregator"},
    # Global wire — real-time
    {"handle": "DeItaone",        "weight": 88, "type": "Wire"},
    {"handle": "FirstSquawk",     "weight": 85, "type": "Wire"},
    {"handle": "Newsquawk",       "weight": 83, "type": "Wire"},
    {"handle": "ReutersWorld",    "weight": 92, "type": "Wire"},
    {"handle": "AFP",             "weight": 90, "type": "Wire"},
    {"handle": "BBCBreaking",     "weight": 88, "type": "Wire"},
    {"handle": "SkyNewsBreak",    "weight": 82, "type": "Wire"},
    {"handle": "cnnbrk",          "weight": 84, "type": "Wire"},
    {"handle": "BNONews",         "weight": 80, "type": "Wire"},
    {"handle": "AJEnglish",       "weight": 82, "type": "Wire"},
    # India wire & markets
    {"handle": "PTI_News",        "weight": 82, "type": "Wire"},
    {"handle": "CNBCTV18Live",    "weight": 80, "type": "Wire"},
    {"handle": "ETNOWlive",       "weight": 79, "type": "Wire"},
    # Analysts & journalists
    {"handle": "AndyMukherjee72", "weight": 83, "type": "Analyst"},
    {"handle": "NikkeiAsia",      "weight": 85, "type": "Publication"},
    {"handle": "EliotHiggins",    "weight": 84, "type": "Journalist"},
    {"handle": "CarlBildt",       "weight": 85, "type": "Analyst"},
    {"handle": "NatashaBertrand", "weight": 83, "type": "Journalist"},
    {"handle": "Osinttechnical",  "weight": 78, "type": "OSINT"},
    {"handle": "JavierBlas",      "weight": 88, "type": "Journalist"},
    # Prediction markets
    {"handle": "Polymarket",      "weight": 68, "type": "Sentiment"},
]

MAX_PER_SOURCE     = 8
MAX_TOTAL_ITEMS    = 120
MAX_TWEETS_PER_RUN = 50
MAX_BREAKING_SHOWN = 40   # Max tweets shown in breaking section

# Browser-like headers to fix RSS blocking
RSS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

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
                    "source":  src_name,
                    "weight":  meta["weight"],
                    "type":    "WIRE/PUB",
                    "title":   title,
                    "summary": (article.get("description") or "")[:300],
                })
        print(f"  ✓ NewsAPI: {len(items)} articles")
    except Exception as e:
        print(f"  ✗ NewsAPI failed: {e}")
    return items


# ══════════════════════════════════════════════════════════════════
#  INGESTION — RSS  (FIX: use requests with browser headers)
# ══════════════════════════════════════════════════════════════════

def fetch_rss():
    items = []
    for src in RSS_SOURCES:
        count = 0
        try:
            # Step 1: fetch raw content with browser headers (bypasses most blocking)
            r    = requests.get(src["url"], headers=RSS_HEADERS, timeout=12)
            feed = feedparser.parse(r.content)

            # Step 2: if still empty, try direct feedparser as fallback
            if not feed.entries:
                feed = feedparser.parse(src["url"])

            for entry in feed.entries[:MAX_PER_SOURCE]:
                title = (entry.get("title") or "").strip()
                if title:
                    summary = entry.get("summary") or entry.get("description") or ""
                    summary = re.sub(r"<[^>]+>", " ", summary)[:300].strip()
                    items.append({
                        "source":  src["name"],
                        "weight":  src["weight"],
                        "type":    "RSS",
                        "title":   title,
                        "summary": summary,
                    })
                    count += 1
            print(f"  ✓ {src['name']}: {count} items")
        except Exception as e:
            print(f"  ✗ {src['name']}: {e}")
    return items


# ══════════════════════════════════════════════════════════════════
#  INGESTION — TWITTER/X
# ══════════════════════════════════════════════════════════════════

def tweet_newsworthiness(text, weight):
    """
    Score a tweet's newsworthiness 0-65.
    Uses intelligence, not just keyword matching — opinion and analysis are penalised hard.
    """
    score = weight * 0.38  # Base from account credibility (max ~33)

    # ── POSITIVE: hard news signals ────────────────────────────────
    if re.search(r'\b(says|said|confirms|confirmed|announces|announced|reports|reported|breaking|BREAKING|warns|warned|strikes|struck|hits|hit|fires|fired|launches|launched)\b', text, re.I):
        score += 10
    if re.search(r'\b(billion|million|trillion|\$|€|£|₹|bps|%)\b', text, re.I):
        score += 8
    if re.search(r'\b(president|prime minister|minister|central bank|fed|rbi|ecb|boj|nato|un|opec|ceo|government|pentagon|kremlin|white house)\b', text, re.I):
        score += 6
    if re.search(r'\d+', text):
        score += 5
    if re.search(r'[A-Z]{3,}', text):   # ALL CAPS headline style
        score += 4
    if len(text) > 150:
        score += 3

    # ── NEGATIVE: opinion, analysis, hypothesis ─────────────────────
    if re.search(r'^\s*if\b', text, re.I):          score -= 18  # Starts with "if" = pure hypothesis
    if re.search(r'\b(1\)|2\)|3\)|\(1\)|\(2\))\b', text): score -= 12  # Numbered points = analysis thread
    if re.search(r'\b(would|could|might|should|may|perhaps|maybe)\b', text, re.I): score -= 8
    if re.search(r'\b(think|believe|seems|appears|feel|suggest|argument|argue)\b', text, re.I): score -= 8
    if text.count('?') > 0:             score -= 10  # Questions = commentary not news
    if text.count('#') > 2:             score -= 5   # Hashtag spam
    if re.search(r'^\s*[a-z]', text):  score -= 5   # Starts lowercase = conversational

    return min(65, max(0, round(score)))


TWEET_MIN_SCORE = 40   # Raised from 32 — only genuinely newsworthy tweets pass


def fetch_twitter():
    from datetime import timezone, timedelta

    items = []
    if not TWITTER_BEARER_TOKEN or TWITTER_BEARER_TOKEN == "your-bearer-token":
        print("  ⚠ Twitter: Bearer token not set, skipping")
        return []

    handles    = [a["handle"] for a in TWITTER_ACCOUNTS]
    handle_map = {a["handle"].lower(): a for a in TWITTER_ACCOUNTS}
    query      = " OR ".join(f"from:{h}" for h in handles)
    query     += " -is:retweet -is:reply -is:quote lang:en"

    start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

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
            print(f"  ✗ Twitter API error {r.status_code}: {r.text[:200]}")
            return []

        data      = r.json()
        tweets    = data.get("data", [])
        users     = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        skipped   = 0

        for tweet in tweets:
            user       = users.get(tweet.get("author_id", ""), {})
            username   = user.get("username", "unknown")
            meta       = handle_map.get(username.lower(), {"weight": 70, "type": "X"})
            text       = tweet.get("text", "").strip()
            tweet_id   = tweet.get("id", "")
            clean_text = re.sub(r"https?://\S+", "", text).strip()

            # Skip replies/mentions
            if clean_text.startswith("@"):
                skipped += 1
                continue

            # Skip if too short
            if len(clean_text) < 80:
                skipped += 1
                continue

            # Score for newsworthiness — skip if below threshold
            score = tweet_newsworthiness(clean_text, meta["weight"])
            if score < TWEET_MIN_SCORE:
                skipped += 1
                continue

            # Build tweet link
            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else ""

            items.append({
                "source":    f"@{username}",
                "handle":    username,
                "weight":    meta["weight"],
                "type":      f"X/{meta['type']}",
                "acct_type": meta["type"],
                "title":     clean_text[:280],
                "summary":   "",
                "score":     score,
                "url":       tweet_url,
            })

        # Sort by score descending
        items.sort(key=lambda x: x["score"], reverse=True)

        print(f"  ✓ Twitter/X: {len(items)} newsworthy tweets ({skipped} skipped as low-context)")
    except Exception as e:
        print(f"  ✗ Twitter failed: {e}")

    return items


# ══════════════════════════════════════════════════════════════════
#  FETCH ALL
# ══════════════════════════════════════════════════════════════════

def fetch_all():
    print("\n[1/3] Fetching headlines...")
    newsapi_items  = fetch_newsapi()
    rss_items      = fetch_rss()
    twitter_items  = fetch_twitter()

    # All items for Claude (RSS + NewsAPI + Twitter)
    all_items = newsapi_items + rss_items + twitter_items

    # Deduplicate by first 60 chars of title
    seen, unique = set(), []
    for item in all_items:
        key = item["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"      {len(unique)} unique items after dedup")

    # Return all items AND twitter items separately (for breaking section)
    return unique[:MAX_TOTAL_ITEMS], twitter_items


# ══════════════════════════════════════════════════════════════════
#  CLAUDE ANALYSIS  (FIX: ask for 12-15 clusters)
# ══════════════════════════════════════════════════════════════════

ANALYSIS_PROMPT = """You are STRATUM, an AI producing a verified signal digest for a sophisticated investor and geopolitical risk monitor.

You receive items from a curated source whitelist. Each has a credibility weight (0-100):
- 90+: Wire services (Reuters, AP, Bloomberg)
- 80-89: Named journalists, top publications
- 70-79: Credible aggregators, regional press
- X/ prefix: Twitter/X posts — fast but unverified unless corroborated

SCORING RULES:
- Single X post only: 10-25
- Single named journalist (80+): 30-50
- X post + 1 wire corroboration: 50-65
- 2+ independent strong sources (85+): 65-80
- Wire consensus (Reuters + AP + Bloomberg): 80-95
- Sources contradict each other: deduct 15-20 points

YOUR TASK:
1. Identify 12-15 DISTINCT story clusters — be generous, surface more stories not fewer
2. Include clusters even if only 1-2 sources cover them — score them low but include them
3. Assign DOMAIN: markets / macro / geopolitics / commodities / corporate / india / japan / europe / middleeast
4. Write a sharp 2-sentence VERIFIED SUMMARY synthesising across sources
5. Write a 1-sentence SIGNAL: what does this mean for an investor or risk manager?
6. Set TREND: "rising" / "falling" / "stable"
7. Flag breaking_on_x: true if story appeared on X before wire services picked it up

Respond ONLY with valid JSON, no markdown:
{
  "stories": [
    {
      "rank": 1,
      "score": 94,
      "domain": "macro",
      "headline": "Max 12 words, sharp and specific",
      "summary": "Two-sentence synthesis.",
      "signal": "One-sentence implication for investor or risk manager.",
      "sources": ["Reuters", "@DeItaone"],
      "trend": "stable",
      "breaking_on_x": false
    }
  ]
}

Sort by score descending. AIM FOR 12-15 STORIES MINIMUM."""


def analyze_with_claude(items, client):
    print("\n[2/3] Analyzing with Claude...")
    headlines_block = "\n".join(
        f"[{i+1}] {item['source']} (wt:{item['weight']}, {item['type']}) — {item['title']}"
        + (f"\n    {item['summary']}" if item.get("summary") else "")
        for i, item in enumerate(items)
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": ANALYSIS_PROMPT + "\n\nITEMS:\n" + headlines_block}]
    )
    raw = msg.content[0].text.strip().lstrip("```json").rstrip("```").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match  = re.search(r'\{.*\}', raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"stories": []}
    stories = result.get("stories", [])
    print(f"      {len(stories)} clusters · top score: {stories[0]['score'] if stories else 'n/a'}")
    return stories


# ══════════════════════════════════════════════════════════════════
#  EMAIL RENDERING
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


def render_tweet(tweet):
    """Render tweet card matching the verified story card structure."""
    handle     = tweet.get("handle", "?")
    acct_type  = tweet.get("acct_type", "X")
    weight     = tweet.get("weight", 70)
    score      = tweet.get("score", 0)
    text       = tweet.get("title", "")
    url        = tweet.get("url", "")

    # Score colours (tweets cap at 65)
    if score >= 55:
        sc, sbg, label = "#d97706", "#fffbeb", "HIGH SIGNAL"
    elif score >= 40:
        sc, sbg, label = "#b45309", "#fefce8", "MODERATE"
    else:
        sc, sbg, label = "#dc2626", "#fef2f2", "LOW SIGNAL"

    link_html = f'<a href="{url}" style="font-family:Courier New,monospace;font-size:9px;color:#0d9488;text-decoration:none;font-weight:700;letter-spacing:0.5px;">VIEW TWEET →</a>' if url else ""

    return f"""
<div style="background:#ffffff;border-radius:6px;margin-bottom:10px;display:flex;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);font-family:Arial,sans-serif;">
  <!-- Score column -->
  <div style="width:66px;min-width:66px;background:{sbg};border-right:3px solid {sc};display:flex;flex-direction:column;align-items:center;justify-content:center;padding:16px 4px;text-align:center;">
    <div style="font-family:'Courier New',Courier,monospace;font-size:24px;font-weight:700;color:{sc};line-height:1;">{score}</div>
    <div style="font-family:'Courier New',Courier,monospace;font-size:6px;color:{sc};letter-spacing:0.5px;margin-top:2px;opacity:0.85;">{label}</div>
    <div style="font-family:'Courier New',Courier,monospace;font-size:8px;color:#94a3b8;margin-top:6px;">WT {weight}</div>
  </div>
  <!-- Content -->
  <div style="flex:1;padding:12px 14px;min-width:0;">
    <div style="margin-bottom:7px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
      <span style="font-family:'Courier New',Courier,monospace;font-size:9px;font-weight:700;letter-spacing:1px;color:#0d9488;background:#f0fdfa;padding:2px 8px;border-radius:2px;border:1px solid #99f6e4;">X · {acct_type.upper()}</span>
      <span style="font-family:'Courier New',Courier,monospace;font-size:10px;font-weight:700;color:#0d9488;">@{handle}</span>
      <span style="font-family:'Courier New',Courier,monospace;font-size:8px;background:#fef2f2;color:#dc2626;padding:1px 6px;border-radius:2px;font-weight:700;letter-spacing:0.5px;">UNVERIFIED</span>
    </div>
    <div style="font-family:Arial,sans-serif;font-size:13px;font-weight:400;color:#1c1917;line-height:1.65;margin-bottom:9px;">{text}</div>
    <div>{link_html}</div>
  </div>
</div>"""


def render_story(story):
    """Render a verified story card."""
    sc          = score_color(story["score"])
    sbg         = score_bg(story["score"])
    dc          = DOMAIN_COLORS.get(story.get("domain", "markets"), "#475569")
    trend       = story.get("trend", "stable")
    trend_sym   = "▲" if trend == "rising" else ("▼" if trend == "falling" else "─")
    trend_color = "#16a34a" if trend == "rising" else ("#dc2626" if trend == "falling" else "#94a3b8")
    sources_str = " · ".join(story.get("sources", []))
    label       = score_label(story["score"])
    x_badge     = '<span style="font-size:9px;background:#e0f2fe;color:#0369a1;padding:1px 6px;border-radius:2px;margin-left:6px;font-weight:700;">BROKE ON X</span>' if story.get("breaking_on_x") else ""

    return f"""
<div style="background:#ffffff;border-radius:6px;margin-bottom:10px;display:flex;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);font-family:Arial,sans-serif;">
  <div style="width:72px;min-width:72px;background:{sbg};border-right:3px solid {sc};display:flex;flex-direction:column;align-items:center;justify-content:center;padding:18px 4px;text-align:center;">
    <div style="font-family:'Courier New',Courier,monospace;font-size:28px;font-weight:700;color:{sc};line-height:1;">{story['score']}</div>
    <div style="font-family:'Courier New',Courier,monospace;font-size:7px;color:{sc};letter-spacing:0.8px;margin-top:2px;opacity:0.8;">{label}</div>
    <div style="font-size:14px;color:{trend_color};margin-top:8px;font-weight:700;">{trend_sym}</div>
  </div>
  <div style="flex:1;padding:14px 16px;min-width:0;">
    <div style="margin-bottom:8px;">
      <span style="font-family:'Courier New',Courier,monospace;font-size:9px;font-weight:700;letter-spacing:1px;color:{dc};background:{dc}15;padding:2px 8px;border-radius:2px;">{story.get('domain','').upper()}</span>
      {x_badge}
      <span style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#94a3b8;margin-left:6px;">{sources_str}</span>
    </div>
    <div style="font-family:Georgia,'Times New Roman',serif;font-size:16px;font-weight:700;color:#0f172a;line-height:1.4;margin-bottom:8px;">{story['headline']}</div>
    <div style="font-size:13px;color:#475569;line-height:1.7;margin-bottom:10px;">{story['summary']}</div>
    <div style="font-size:12px;color:#64748b;border-left:3px solid {sc};padding-left:10px;font-style:italic;">
      <span style="font-family:'Courier New',Courier,monospace;font-size:8px;color:{sc};font-style:normal;font-weight:700;letter-spacing:0.5px;">SIGNAL · </span>{story.get('signal','')}
    </div>
  </div>
  <div style="width:26px;min-width:26px;display:flex;align-items:flex-start;justify-content:center;padding-top:14px;">
    <span style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#cbd5e1;">#{story['rank']}</span>
  </div>
</div>"""


def section_header(title, subtitle, color):
    return f"""
<div style="margin:20px 0 12px;padding:10px 16px;background:{color};border-radius:5px;font-family:'Courier New',Courier,monospace;">
  <div style="font-size:13px;font-weight:700;color:#ffffff;letter-spacing:2px;">{title}</div>
  <div style="font-size:9px;color:rgba(255,255,255,0.7);margin-top:2px;letter-spacing:1px;">{subtitle}</div>
</div>"""


def build_html_email(stories, twitter_items):
    now_str        = datetime.now().strftime("%d %b %Y · %H:%M IST")
    verified_count = sum(1 for s in stories if s["score"] >= 80)
    avg_score      = round(sum(s["score"] for s in stories) / len(stories)) if stories else 0
    broke_on_x     = sum(1 for s in stories if s.get("breaking_on_x"))

    top_tweets  = sorted(twitter_items, key=lambda t: t["weight"], reverse=True)[:MAX_BREAKING_SHOWN]
    tweets_html = "".join(render_tweet(t) for t in top_tweets)
    stories_html= "".join(render_story(s) for s in stories)

    x_note = f'<span style="color:#ea580c;font-weight:700;">{broke_on_x} broke on X · </span>' if broke_on_x else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<div style="max-width:1150px;margin:0 auto;padding:20px 16px;">

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:18px 24px;margin-bottom:16px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
    <tr>
      <td>
        <div style="font-family:'Courier New',Courier,monospace;font-size:22px;font-weight:700;letter-spacing:5px;color:#0f172a;">STRATUM</div>
        <div style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#94a3b8;letter-spacing:2px;margin-top:3px;">VERIFIED SIGNAL DIGEST</div>
      </td>
      <td style="text-align:right;vertical-align:top;">
        <div style="font-family:'Courier New',Courier,monospace;font-size:11px;color:#64748b;">{now_str}</div>
        <div style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#94a3b8;margin-top:4px;">
          {x_note}{len(stories)} STORIES · {verified_count} VERIFIED · AVG {avg_score}
        </div>
      </td>
    </tr>
  </table>

  <!-- Two-column layout -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr valign="top">

      <!-- LEFT: Breaking Feed -->
      <td width="48%" style="padding-right:10px;">
        <!-- Section header -->
        <div style="margin-bottom:10px;padding:10px 14px;background:#0d9488;border-radius:5px;font-family:'Courier New',Courier,monospace;">
          <div style="font-size:12px;font-weight:700;color:#ffffff;letter-spacing:2px;">⚡ BREAKING FEED</div>
          <div style="font-size:8px;color:rgba(255,255,255,0.75);margin-top:2px;letter-spacing:1px;">LIVE FROM X · {len(top_tweets)} POSTS · UNVERIFIED</div>
        </div>
        {tweets_html}
      </td>

      <!-- SPACER -->
      <td width="4%"></td>

      <!-- RIGHT: Verified Digest -->
      <td width="48%" style="padding-left:10px;">
        <!-- Section header -->
        <div style="margin-bottom:10px;padding:10px 14px;background:#0f172a;border-radius:5px;font-family:'Courier New',Courier,monospace;">
          <div style="font-size:12px;font-weight:700;color:#ffffff;letter-spacing:2px;">✓ VERIFIED DIGEST</div>
          <div style="font-size:8px;color:rgba(255,255,255,0.6);margin-top:2px;letter-spacing:1px;">{len(stories)} STORIES · CROSS-REFERENCED & SCORED</div>
        </div>
        {stories_html}
      </td>

    </tr>
  </table>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;padding:14px 0;">
    <tr>
      <td style="font-family:'Courier New',Courier,monospace;font-size:9px;color:#cbd5e1;">
        <span style="color:#16a34a;">■</span> ≥80 VERIFIED &nbsp;
        <span style="color:#0369a1;">■</span> 60–79 HIGH &nbsp;
        <span style="color:#d97706;">■</span> 35–59 DEVELOPING &nbsp;
        <span style="color:#dc2626;">■</span> &lt;35 LOW
      </td>
      <td style="text-align:right;font-family:'Courier New',Courier,monospace;font-size:9px;color:#cbd5e1;">STRATUM v0.3</td>
    </tr>
  </table>

</div>
</body></html>"""


# ══════════════════════════════════════════════════════════════════
#  EMAIL DELIVERY
# ══════════════════════════════════════════════════════════════════

def send_email(html_body, stories):
    now_str = datetime.now().strftime("%d %b %H:%M")
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
#  TELEGRAM DELIVERY
# ══════════════════════════════════════════════════════════════════

SCORE_EMOJI = {
    "high":       "🟢",
    "mid_high":   "🔵",
    "developing": "🟡",
    "low":        "🔴",
}

def score_emoji(s):
    if s >= 80: return "🟢"
    if s >= 60: return "🔵"
    if s >= 35: return "🟡"
    return "🔴"

def build_telegram_message(stories, twitter_items):
    """Build Option C — headline-only digest for Telegram."""
    now_str        = datetime.now().strftime("%d %b · %H:%M IST")
    verified_count = sum(1 for s in stories if s["score"] >= 80)
    avg_score      = round(sum(s["score"] for s in stories) / len(stories)) if stories else 0

    lines = []

    # Header
    lines.append(f"*STRATUM* | {now_str}")
    lines.append(f"_{len(stories)} stories · {verified_count} verified · Avg {avg_score}_")
    lines.append("")

    # Breaking from X — top 3 tweets only
    top_tweets = sorted(twitter_items, key=lambda t: t["score"], reverse=True)[:3]
    if top_tweets:
        lines.append("⚡ *Breaking from X*")
        for t in top_tweets:
            emoji  = "🔴" if t["score"] >= 55 else "🟡"
            handle = t.get("handle", "?")
            text   = t.get("title", "")[:120]
            lines.append(f"{emoji} *@{handle}* [{t['score']}]")
            lines.append(f"{text}")
            url = t.get("url", "")
            if url:
                lines.append(f"[View tweet]({url})")
            lines.append("")

    # Verified digest — all stories, headlines only
    lines.append("✅ *Verified Digest*")
    for s in stories:
        em     = score_emoji(s["score"])
        domain = s.get("domain", "").upper()
        score  = s["score"]
        rank   = s["rank"]
        hl     = s["headline"]
        signal = s.get("signal", "")
        x_tag  = " _(broke on X)_" if s.get("breaking_on_x") else ""
        lines.append(f"{em} *[{score}] {hl}*{x_tag}")
        lines.append(f"_{domain} · {signal}_")
        lines.append("")

    lines.append("─────────────────")
    lines.append(f"_Full analysis in email · Next digest in 4h_")

    return "\n".join(lines)


def send_telegram(message):
    """Send message via Telegram Bot API."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10
        )
        if r.status_code == 200:
            print(f"      ✓ Telegram sent → chat {TELEGRAM_CHAT_ID}")
        else:
            print(f"      ✗ Telegram error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"      ✗ Telegram failed: {e}")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    sep = "─" * 52
    print(f"\n{sep}")
    print(f"  STRATUM v0.3  ·  {datetime.now().strftime('%d %b %Y  %H:%M')}")
    print(sep)

    all_items, twitter_items = fetch_all()
    if not all_items:
        print("  ✗ No items fetched. Check your API keys.")
        return

    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    stories = analyze_with_claude(all_items, client)
    if not stories:
        print("  ✗ Claude returned no stories.")
        return

    print("\n[3/3] Sending digest...")
    html = build_html_email(stories, twitter_items)
    send_email(html, stories)
    tg_msg = build_telegram_message(stories, twitter_items)
    send_telegram(tg_msg)

    print(f"\n  Breaking feed: {min(len(twitter_items), MAX_BREAKING_SHOWN)} tweets")
    print(f"  Verified digest: {len(stories)} stories")
    for s in stories[:3]:
        x_tag = " [X]" if s.get("breaking_on_x") else ""
        print(f"    [{s['score']}]{x_tag} {s['headline']}")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
