import streamlit as st
import requests
import json
import re
import html as htmllib
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════════
#  CONFIG — update these to your GitHub repo details
# ══════════════════════════════════════════════════════════════════

GITHUB_USER    = "jdsanghera"
GITHUB_REPO    = "STRATUM"
GITHUB_BRANCH  = "main"
GITHUB_TOKEN   = ""  # Set via Streamlit Secrets — see setup instructions

# ══════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title  = "STRATUM",
    page_icon   = "📡",
    layout      = "wide",
    initial_sidebar_state = "collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────
st.html("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500;600&family=Libre+Baskerville:wght@400;700&display=swap');

  html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

  .stApp { background: #f1f5f9; }

  .stratum-header {
    background: #ffffff;
    border-radius: 10px;
    padding: 18px 24px;
    margin-bottom: 20px;
    border: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .stratum-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 6px;
    color: #0f172a;
  }
  .stratum-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    color: #94a3b8;
    letter-spacing: 2px;
    margin-top: 3px;
  }
  .digest-header {
    background: #0f172a;
    border-radius: 8px;
    padding: 12px 18px;
    margin: 16px 0 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .digest-ts {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
  }
  .digest-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #64748b;
  }
  .topic-card {
    background: #ffffff;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid #e2e8f0;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .topic-card.starred {
    border: 2px solid #f59e0b;
    box-shadow: 0 2px 8px rgba(245,158,11,0.15);
  }
  .card-inner {
    display: flex;
  }
  .score-col {
    width: 70px;
    min-width: 70px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 16px 4px;
    text-align: center;
  }
  .score-num {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 26px;
    font-weight: 700;
    line-height: 1;
  }
  .score-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 7px;
    letter-spacing: 0.8px;
    margin-top: 2px;
    opacity: 0.8;
  }
  .card-body {
    flex: 1;
    padding: 14px 16px;
  }
  .domain-pill {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 8px;
    border-radius: 3px;
    display: inline-block;
    margin-right: 6px;
  }
  .topic-pill {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    color: #64748b;
    background: #f1f5f9;
    padding: 2px 8px;
    border-radius: 3px;
    display: inline-block;
    margin-right: 6px;
  }
  .headline {
    font-family: 'Libre Baskerville', serif;
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.4;
    margin: 8px 0;
  }
  .summary {
    font-size: 13px;
    color: #475569;
    line-height: 1.7;
    margin-bottom: 10px;
  }
  .signal-box {
    font-size: 12px;
    color: #64748b;
    font-style: italic;
    padding-left: 10px;
    margin-bottom: 10px;
  }
  .signal-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 8px;
    font-weight: 700;
    font-style: normal;
    letter-spacing: 0.5px;
  }
  .social-section {
    border-top: 1px solid #f1f5f9;
    padding-top: 10px;
    margin-top: 10px;
  }
  .social-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 8px;
    color: #94a3b8;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }
  .social-item {
    background: #f8fafc;
    border-radius: 4px;
    padding: 7px 10px;
    margin-bottom: 5px;
    border-left: 2px solid #d97706;
    font-size: 12px;
    color: #374151;
    line-height: 1.5;
  }
  .social-handle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    color: #0d9488;
  }
  .unverified-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 8px;
    background: #fef2f2;
    color: #dc2626;
    padding: 1px 5px;
    border-radius: 2px;
    font-weight: 700;
    margin-left: 6px;
  }
  .star-expired {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    color: #94a3b8;
    margin-top: 4px;
  }
  div[data-testid="stExpander"] {
    border: none !important;
    background: transparent !important;
  }
</style>
""")


# ══════════════════════════════════════════════════════════════════
#  GITHUB DATA FETCHING
# ══════════════════════════════════════════════════════════════════

def get_token():
    try:
        if "GH_TOKEN" in st.secrets:
            return st.secrets["GH_TOKEN"]
    except Exception:
        pass
    return GITHUB_TOKEN


def fetch_github_json(filename):
    """Fetch a JSON file from the public GitHub repo via raw URL."""
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filename}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return json.loads(r.text)
        elif r.status_code == 404:
            return []
        else:
            st.error(f"GitHub fetch error {r.status_code}")
            return []
    except Exception as e:
        st.error(f"Failed to fetch {filename}: {e}")
        return []


def push_github_json(filename, data, message):
    """Push updated JSON file to GitHub repo."""
    token = get_token()
    if not token:
        st.error("GitHub token not set. Stars won't sync across devices.")
        return False

    # Get current file SHA (needed for update)
    url     = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r       = requests.get(url, headers=headers, timeout=10)
    sha     = r.json().get("sha", "") if r.status_code == 200 else ""

    import base64
    content = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    payload = {"message": message, "content": content, "branch": GITHUB_BRANCH}
    if sha:
        payload["sha"] = sha

    r2 = requests.put(url, headers=headers, json=payload, timeout=15)
    return r2.status_code in (200, 201)


# ══════════════════════════════════════════════════════════════════
#  SCORE COLOURS
# ══════════════════════════════════════════════════════════════════

def score_color(s):
    if s >= 80: return "#16a34a", "#f0fdf4", "VERIFIED"
    if s >= 60: return "#0369a1", "#eff6ff", "HIGH"
    if s >= 35: return "#d97706", "#fffbeb", "DEVELOPING"
    return "#dc2626", "#fef2f2", "LOW"

DOMAIN_COLORS = {
    "markets": "#0369a1", "macro": "#7c3aed", "geopolitics": "#b45309",
    "commodities": "#065f46", "corporate": "#c2410c", "india": "#be185d",
    "japan": "#dc2626", "europe": "#1d4ed8", "middleeast": "#b45309",
}

TREND_SYMBOLS = {"rising": "▲", "falling": "▼", "stable": "─"}
TREND_COLORS  = {"rising": "#16a34a", "falling": "#dc2626", "stable": "#94a3b8"}


# ══════════════════════════════════════════════════════════════════
#  TOPIC CARD RENDERER
# ══════════════════════════════════════════════════════════════════

def safe(text):
    """Make text completely safe for HTML insertion - escapes ALL special chars."""
    if not text:
        return ""
    stripped = re.sub(r"<[^>]+>", "", str(text)).strip()
    return htmllib.escape(stripped, quote=True)

def clean(text):
    """Alias for safe() - kept for compatibility."""
    return safe(text)

def render_card(story, starred_ids, digest_ts=None, key_prefix="feed"):
    sc, sbg, label = score_color(story["score"])
    dc      = DOMAIN_COLORS.get(story.get("domain", ""), "#475569")
    trend   = story.get("trend", "stable")
    ts      = TREND_SYMBOLS.get(trend, "─")
    tc      = TREND_COLORS.get(trend, "#94a3b8")
    sigs    = story.get("social_signals", [])
    topic    = safe(story.get("topic", ""))
    sources  = " · ".join(safe(s) for s in story.get("sources", []))
    headline = safe(story.get("headline", ""))
    summary  = safe(story.get("summary", ""))
    signal   = safe(story.get("signal", ""))
    context  = safe(story.get("context", ""))
    source_url = story.get("source_url", "")
    is_standalone = story.get("standalone_social", False)
    read_more = f'<a href="{source_url}" target="_blank" style="font-family:IBM Plex Mono,monospace;font-size:9px;color:#0369a1;text-decoration:none;font-weight:700;margin-left:8px;">READ SOURCE →</a>' if source_url else ""
    context_banner = f'<div style="background:#fef9c3;border-left:3px solid #eab308;border-radius:3px;padding:7px 10px;margin-bottom:8px;font-size:11px;color:#854d0e;font-family:Arial,sans-serif;">⚡ <b>UNVERIFIED SOCIAL SIGNAL</b> · {context}</div>' if is_standalone and context else ""
    sid     = f"{digest_ts}_{story.get('rank',0)}_{story.get('headline','')[:30]}"
    is_star = sid in starred_ids

    social_html = ""
    if sigs:
        sig_items = ""
        for sig in sigs[:3]:
            plat = "X" if sig.get("platform") == "twitter" else "BSKY"
            url  = sig.get("url", "")
            link = f' <a href="{url}" target="_blank" style="color:#0369a1;font-size:9px;text-decoration:none;font-weight:700;">VIEW →</a>' if url else ""
            sig_items += f"""<div class="social-item">
              <span class="social-handle">{plat} · @{sig.get('handle','?')}</span>
              <span class="unverified-badge">UNVERIFIED</span>
              <span style="font-family:IBM Plex Mono,monospace;font-size:9px;color:#d97706;font-weight:700;margin-left:6px;">[{sig.get('score',0)}]</span>
              {link}
              <div style="margin-top:4px;">{safe(sig.get('text',''))[:180]}</div>
            </div>"""
        social_html = f"""<div class="social-section">
          <div class="social-header">⚡ {len(sigs)} SOCIAL SIGNAL{'S' if len(sigs)!=1 else ''}</div>
          {sig_items}
        </div>"""

    bsoc = '<span style="font-family:IBM Plex Mono,monospace;font-size:9px;background:#e0f2fe;color:#0369a1;padding:1px 6px;border-radius:2px;font-weight:700;margin-left:6px;">BROKE ON SOCIAL</span>' if story.get("breaking_on_social") else ""
    star_cls = "starred" if is_star else ""

    card_html = f"""
    <div class="topic-card {star_cls}">
      <div class="card-inner">
        <div class="score-col" style="background:{sbg};border-right:3px solid {sc};">
          <div class="score-num" style="color:{sc};">{story['score']}</div>
          <div class="score-lbl" style="color:{sc};">{label}</div>
          <div style="font-size:14px;color:{tc};margin-top:8px;font-weight:700;">{ts}</div>
        </div>
        <div class="card-body">
          <div style="margin-bottom:6px;">
            <span class="domain-pill" style="color:{dc};background:{dc}18;">{story.get('domain','').upper()}</span>
            <span class="topic-pill">{topic}</span>
            {bsoc}
            <span style="font-family:IBM Plex Mono,monospace;font-size:9px;color:#94a3b8;">{sources}</span>
          </div>
          <div class="headline">{headline}</div>
          {context_banner}
          <div class="summary">{summary}</div>
          <div class="signal-box" style="border-left:3px solid {sc};">
            <span class="signal-label" style="color:{sc};">SIGNAL · </span>{signal}
          </div>
          {read_more}
          {social_html}
        </div>
        <div style="width:26px;min-width:26px;display:flex;align-items:flex-start;justify-content:center;padding-top:14px;">
          <span style="font-family:IBM Plex Mono,monospace;font-size:9px;color:#cbd5e1;">#{story.get('rank',0)}</span>
        </div>
      </div>
    </div>
    """
    st.html(card_html)

    # Star button
    col1, col2 = st.columns([6, 1])
    with col2:
        star_label = "★ Unstar" if is_star else "☆ Star"
        if st.button(star_label, key=f"{key_prefix}_star_{sid}", use_container_width=True):
            if is_star:
                starred_ids.discard(sid)
                starred = fetch_github_json("starred.json")
                starred = [s for s in starred if s.get("id") != sid]
                ok = push_github_json("starred.json", starred, f"unstar: {story['headline'][:40]}")
                if ok:
                    st.success("Unstarred")
                else:
                    st.error("Failed to unstar — check GH_TOKEN secret")
            else:
                starred_ids.add(sid)
                starred = fetch_github_json("starred.json")
                from datetime import timedelta as td
                starred.append({
                    "id":         sid,
                    "digest_ts":  digest_ts,
                    "starred_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + td(days=90)).isoformat(),
                    "story":      story,
                })
                ok = push_github_json("starred.json", starred, f"star: {story['headline'][:40]}")
                if ok:
                    st.success("⭐ Starred! View in Starred tab.")
                else:
                    st.error("Failed to star — check GH_TOKEN secret")
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════

def main():
    # Header
    st.html("""
    <div class="stratum-header">
      <div>
        <div class="stratum-title">STRATUM</div>
        <div class="stratum-sub">VERIFIED SIGNAL DIGEST</div>
      </div>
    </div>
    """)

    # Tabs
    tab_feed, tab_starred = st.tabs(["📡 Feed", "★ Starred"])

    # Load data
    with st.spinner("Loading digest..."):
        digests = fetch_github_json("digests.json")
        starred_raw = fetch_github_json("starred.json")

    # Build starred ID set
    now_utc = datetime.now(timezone.utc)
    starred_ids = set()
    for s in starred_raw:
        try:
            exp = datetime.fromisoformat(s.get("expires_at", "").replace("Z", "+00:00"))
            if exp > now_utc:
                starred_ids.add(s["id"])
        except Exception:
            starred_ids.add(s.get("id", ""))

    # ── FEED TAB ──────────────────────────────────────────────────
    with tab_feed:
        if not digests:
            st.info("No digests yet. Run the GitHub Action to generate the first digest.")

        col_refresh, col_run, col_count = st.columns([1, 1, 3])
        with col_refresh:
            if st.button("🔄 Refresh Feed", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col_run:
            if st.button("▶ Run Digest Now", use_container_width=True):
                token = get_token()
                if not token:
                    st.error("GH_TOKEN secret not set — cannot trigger workflow.")
                else:
                    r = requests.post(
                        f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/actions/workflows/stratum.yml/dispatches",
                        headers={
                            "Authorization": f"token {token}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                        json={"ref": GITHUB_BRANCH},
                        timeout=10,
                    )
                    if r.status_code == 204:
                        st.success("✓ Digest running — refresh in ~3 minutes")
                    else:
                        st.error(f"Failed to trigger: {r.status_code} {r.text[:100]}")
        with col_count:
            st.html(f"<div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#94a3b8;padding-top:8px;'>{len(digests)} digests · {sum(d.get('story_count',0) for d in digests)} total stories</div>")

        if not digests:
            return

        for digest in digests:
            ts       = digest.get("timestamp_ist", digest.get("timestamp", ""))
            stories  = digest.get("stories", [])
            avg      = digest.get("avg_score", 0)
            verified = sum(1 for s in stories if s.get("score", 0) >= 80)

            # Digest header — collapsible
            with st.expander(f"📅 {ts}  ·  {len(stories)} topics  ·  {verified} verified  ·  avg {avg}", expanded=(digests.index(digest) == 0)):
                for story in stories:
                    render_card(story, starred_ids, digest_ts=ts)

    # ── STARRED TAB ───────────────────────────────────────────────
    with tab_starred:
        if not starred_raw:
            st.html("""
            <div style="text-align:center;padding:60px 0;color:#94a3b8;font-family:IBM Plex Mono,monospace;">
              <div style="font-size:32px;margin-bottom:12px;">☆</div>
              <div style="font-size:13px;letter-spacing:1px;">NO STARRED TOPICS YET</div>
              <div style="font-size:11px;margin-top:6px;color:#cbd5e1;">Hit ☆ Star on any topic in the Feed tab</div>
            </div>
            """)
            return

        active   = [s for s in starred_raw if s.get("id") in starred_ids]
        expired  = [s for s in starred_raw if s.get("id") not in starred_ids]

        st.html(f"<div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#94a3b8;margin-bottom:16px;'>{len(active)} active · {len(expired)} expired (90-day limit)</div>")

        for item in active:
            story    = item.get("story", {})
            star_ts  = item.get("starred_at", "")
            digest_ts = item.get("digest_ts", "")
            try:
                star_dt = datetime.fromisoformat(star_ts.replace("Z", "+00:00"))
                star_str = star_dt.strftime("%d %b %Y · %H:%M")
            except Exception:
                star_str = ""

            st.html(f"<div style='font-family:IBM Plex Mono,monospace;font-size:9px;color:#f59e0b;margin-bottom:4px;'>★ STARRED {star_str} · from digest {digest_ts}</div>")
            render_card(story, starred_ids, digest_ts=digest_ts, key_prefix="starred")

        if expired:
            with st.expander(f"Expired stars ({len(expired)})"):
                for item in expired:
                    story = item.get("story", {})
                    st.html(f"<div class='star-expired'>★ expired · {story.get('headline','')}</div>")


if __name__ == "__main__":
    main()
