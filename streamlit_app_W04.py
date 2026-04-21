import streamlit as st
import requests
import json
import re
import html as htmllib
from datetime import datetime, timezone, timedelta

GITHUB_USER   = "jdsanghera"
GITHUB_REPO   = "STRATUM"
GITHUB_BRANCH = "main"
GITHUB_TOKEN  = ""

st.set_page_config(page_title="STRATUM", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; font-size: 15px; }
  .stApp { background: #f1f5f9; }
  .stTabs [data-baseweb="tab-list"] { gap: 12px; }
  .stTabs [data-baseweb="tab"] { padding: 10px 20px; font-size: 14px; font-weight: 500; }

  /* Header */
  .stratum-header { background:#fff; border-radius:10px; padding:18px 26px; margin-bottom:16px; border:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; }
  .stratum-wordmark { font-size:24px; font-weight:600; letter-spacing:6px; color:#0f172a; }
  .stratum-sub { font-size:10px; color:#94a3b8; letter-spacing:2px; margin-top:3px; font-family:monospace; }

  /* Metric tiles */
  .metric-row { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
  .metric-tile { background:#fff; border-radius:8px; padding:14px 20px; border:1px solid #e2e8f0; min-width:100px; flex:1; text-align:center; }
  .metric-val { font-size:28px; font-weight:600; color:#0f172a; line-height:1; }
  .metric-lbl { font-size:10px; color:#94a3b8; letter-spacing:1px; margin-top:4px; font-family:monospace; }

  /* Section headers */
  .breaking-header { background:#dc2626; border-radius:6px; padding:10px 16px; margin-bottom:10px; }
  .breaking-header-text { font-size:12px; font-weight:600; color:#fff; letter-spacing:2px; font-family:monospace; }
  .section-header { background:#0f172a; border-radius:6px; padding:10px 16px; margin:16px 0 10px; }
  .section-header-text { font-size:12px; font-weight:600; color:#fff; letter-spacing:2px; font-family:monospace; }

  /* Playing card */
  .play-card {
    background: #fff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    padding: 18px 16px 14px;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 10px;
    transition: box-shadow 0.15s;
    font-family: 'DM Sans', sans-serif;
  }
  .play-card-score {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .play-card-score-num {
    font-size: 32px;
    font-weight: 700;
    line-height: 1;
  }
  .play-card-score-meta {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .play-card-label {
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: monospace;
    opacity: 0.85;
  }
  .play-card-trend {
    font-size: 13px;
    font-weight: 600;
  }
  .play-card-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
  }
  .play-card-domain {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: monospace;
  }
  .play-card-bsoc {
    font-size: 8px;
    font-weight: 700;
    background: #e0f2fe;
    color: #0369a1;
    padding: 2px 6px;
    border-radius: 2px;
    font-family: monospace;
  }
  .play-card-headline {
    font-size: 15px;
    font-weight: 600;
    color: #0f172a;
    line-height: 1.4;
    flex: 1;
  }
  .play-card-signal {
    font-size: 12px;
    color: #64748b;
    font-style: italic;
    border-left: 3px solid #e2e8f0;
    padding-left: 8px;
    line-height: 1.5;
  }
  .play-card-signal-label {
    font-family: monospace;
    font-size: 8px;
    font-weight: 700;
    font-style: normal;
    letter-spacing: 0.5px;
  }
  .play-card-sources {
    font-size: 10px;
    color: #94a3b8;
    font-family: monospace;
  }

  /* Detail panel */
  .detail-panel {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.10);
    padding: 24px 28px;
    margin-bottom: 20px;
    font-family: 'DM Sans', sans-serif;
  }
  .detail-headline { font-size: 20px; font-weight: 700; color: #0f172a; line-height: 1.4; margin: 12px 0 10px; }
  .detail-summary { font-size: 14px; color: #475569; line-height: 1.75; margin-bottom: 12px; }
  .detail-signal { font-size: 13px; color: #64748b; font-style: italic; padding-left: 12px; margin-bottom: 14px; }
  .detail-signal-label { font-family: monospace; font-size: 9px; font-weight: 700; font-style: normal; letter-spacing: 0.5px; }
  .detail-social-item { background:#f8fafc; border-radius:4px; padding:8px 12px; margin-bottom:6px; border-left:2px solid #d97706; font-size:13px; color:#374151; line-height:1.6; }
  .detail-social-handle { font-size:10px; font-weight:600; font-family:monospace; }
  .unverified-badge { font-size:8px; background:#fef2f2; color:#dc2626; padding:1px 5px; border-radius:2px; font-weight:700; margin-left:6px; font-family:monospace; }
  .context-banner { background:#fef9c3; border-left:3px solid #eab308; border-radius:3px; padding:8px 12px; margin-bottom:10px; font-size:12px; color:#854d0e; }
</style>
""", unsafe_allow_html=True)

# ── Config & helpers ──────────────────────────────────────────────

def get_token():
    try:
        if "GH_TOKEN" in st.secrets:
            return st.secrets["GH_TOKEN"]
    except Exception:
        pass
    return GITHUB_TOKEN

def fetch_github_json(filename):
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filename}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return json.loads(r.text)
        return {}
    except Exception as e:
        st.error(f"Failed to fetch {filename}: {e}")
        return {}

def safe(text):
    if not text:
        return ""
    return htmllib.escape(re.sub(r"<[^>]+>", "", str(text)).strip(), quote=True)

def score_color(s):
    if s >= 80: return "#16a34a", "#f0fdf4", "VERIFIED"
    if s >= 60: return "#0369a1", "#eff6ff", "HIGH"
    if s >= 35: return "#d97706", "#fffbeb", "DEVELOPING"
    return "#dc2626", "#fef2f2", "LOW"

DOMAIN_COLORS = {
    "markets":"#0369a1","macro":"#7c3aed","geopolitics":"#b45309",
    "commodities":"#065f46","corporate":"#c2410c","india":"#be185d",
    "japan":"#dc2626","europe":"#1d4ed8","middleeast":"#b45309",
}
TREND_SYMBOLS = {"rising":"▲","falling":"▼","stable":"─"}
TREND_COLORS  = {"rising":"#16a34a","falling":"#dc2626","stable":"#94a3b8"}
PLATFORM_META = {"twitter":("#0369a1","X"),"bluesky":("#0d9488","BSKY"),"telegram":("#7c3aed","TG")}

# ── Playing card (compact) ────────────────────────────────────────

def render_play_card(story, card_key):
    sc, sbg, label = score_color(story["score"])
    dc      = DOMAIN_COLORS.get(story.get("domain",""), "#475569")
    trend   = story.get("trend","stable")
    ts      = TREND_SYMBOLS.get(trend,"─")
    tc      = TREND_COLORS.get(trend,"#94a3b8")
    headline = safe(story.get("headline",""))
    signal   = safe(story.get("signal",""))
    sources  = " · ".join(safe(s) for s in story.get("sources",[]))
    pub_at   = safe(story.get("published_at",""))
    bsoc     = '<span class="play-card-bsoc">BREAKING</span>' if story.get("breaking_on_social") else ""
    time_html = f'<div style="font-size:9px;color:#94a3b8;font-family:monospace;">{pub_at}</div>' if pub_at else ""

    st.html(f"""
    <div class="play-card" style="border-top: 4px solid {sc};">
      <div class="play-card-score">
        <div class="play-card-score-num" style="color:{sc};">{story['score']}</div>
        <div class="play-card-score-meta">
          <span class="play-card-label" style="color:{sc};">{label}</span>
          <span class="play-card-trend" style="color:{tc};">{ts}</span>
        </div>
      </div>
      <div class="play-card-pills">
        <span class="play-card-domain" style="color:{dc};background:{dc}18;">{story.get('domain','').upper()}</span>
        {bsoc}
      </div>
      <div class="play-card-headline">{headline}</div>
      <div class="play-card-signal" style="border-left-color:{sc};">
        <span class="play-card-signal-label" style="color:{sc};">SIGNAL · </span>{signal}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div class="play-card-sources">{sources}</div>
        {time_html}
      </div>
    </div>
    """)
    if st.button("View detail →", key=card_key, use_container_width=True):
        st.session_state["selected_story"] = story


# ── Detail panel ─────────────────────────────────────────────────

def render_detail_panel(story):
    sc, sbg, label = score_color(story["score"])
    dc       = DOMAIN_COLORS.get(story.get("domain",""), "#475569")
    trend    = story.get("trend","stable")
    ts       = TREND_SYMBOLS.get(trend,"─")
    tc       = TREND_COLORS.get(trend,"#94a3b8")
    headline = safe(story.get("headline",""))
    summary  = safe(story.get("summary",""))
    signal   = safe(story.get("signal",""))
    context  = safe(story.get("context",""))
    source_url = story.get("source_url","")
    sigs     = story.get("social_signals",[])
    sources  = " · ".join(safe(s) for s in story.get("sources",[]))

    ctx_html = f'<div class="context-banner">⚡ <b>UNVERIFIED SOCIAL SIGNAL</b> · {context}</div>' if story.get("standalone_social") and context else ""
    read_more = f'<a href="{source_url}" target="_blank" style="font-size:12px;color:#0369a1;text-decoration:none;font-weight:600;font-family:monospace;">READ SOURCE →</a>' if source_url else ""
    bsoc = '<span style="font-size:9px;background:#e0f2fe;color:#0369a1;padding:1px 7px;border-radius:2px;font-weight:700;margin-left:8px;font-family:monospace;">BROKE ON SOCIAL</span>' if story.get("breaking_on_social") else ""

    sig_items = ""
    for sig in sigs[:5]:
        plat = sig.get("platform","twitter")
        pc, pl = PLATFORM_META.get(plat,("#94a3b8","SRC"))
        url  = sig.get("url","")
        lnk  = f'<a href="{url}" target="_blank" style="color:#0369a1;font-size:10px;text-decoration:none;font-weight:600;">VIEW →</a>' if url else ""
        sig_items += f"""<div class="detail-social-item">
          <span class="detail-social-handle" style="color:{pc};">{pl} · @{sig.get('handle','?')}</span>
          <span class="unverified-badge">UNVERIFIED</span>
          <span style="font-family:monospace;font-size:9px;color:#d97706;font-weight:700;margin-left:6px;">[{sig.get('score',0)}]</span>
          {lnk}
          <div style="margin-top:5px;">{safe(sig.get('text',''))[:220]}</div>
        </div>"""
    social_block = f'<div style="margin-top:14px;border-top:1px solid #f1f5f9;padding-top:12px;"><div style="font-size:9px;color:#94a3b8;letter-spacing:0.5px;margin-bottom:8px;font-family:monospace;">⚡ {len(sigs)} SOCIAL SIGNAL{"S" if len(sigs)!=1 else ""}</div>{sig_items}</div>' if sigs else ""

    st.html(f"""
    <div class="detail-panel" style="border-left: 5px solid {sc};">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
        <div>
          <span class="play-card-domain" style="color:{dc};background:{dc}18;font-size:10px;font-weight:700;letter-spacing:1px;padding:2px 9px;border-radius:3px;font-family:monospace;">{story.get('domain','').upper()}</span>
          <span style="font-size:10px;color:#64748b;background:#f1f5f9;padding:2px 9px;border-radius:3px;margin-left:6px;font-family:monospace;">{safe(story.get('topic',''))}</span>
          {bsoc}
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <div style="text-align:right;">
            <div style="font-size:32px;font-weight:700;color:{sc};line-height:1;">{story['score']}</div>
            <div style="font-size:8px;color:{sc};font-family:monospace;letter-spacing:1px;">{label}</div>
          </div>
          <div style="font-size:18px;color:{tc};font-weight:700;">{ts}</div>
        </div>
      </div>
      {ctx_html}
      <div class="detail-headline">{headline}</div>
      <div class="detail-summary">{summary}</div>
      <div class="detail-signal" style="border-left:4px solid {sc};">
        <span class="detail-signal-label" style="color:{sc};">SIGNAL · </span>{signal}
      </div>
      <div style="display:flex;align-items:center;gap:16px;margin-bottom:4px;">
        {read_more}
        <span style="font-size:10px;color:#94a3b8;font-family:monospace;">{sources}</span>
      </div>
      {social_block}
    </div>
    """)

    if st.button("✕ Close", key="close_detail"):
        del st.session_state["selected_story"]
        st.rerun()


# ── Card grid renderer ────────────────────────────────────────────

def render_card_grid(stories, key_prefix):
    if not stories:
        st.info("No stories to display.")
        return

    cols = st.columns(3)
    for i, story in enumerate(stories):
        with cols[i % 3]:
            render_play_card(story, card_key=f"{key_prefix}_{i}")


# ── Main ─────────────────────────────────────────────────────────

def main():
    st.html("""
    <div class="stratum-header">
      <div><div class="stratum-wordmark">STRATUM</div><div class="stratum-sub">VERIFIED SIGNAL DIGEST</div></div>
    </div>""")

    with st.spinner("Loading..."):
        raw = fetch_github_json("digests.json")

    if isinstance(raw, dict):
        digests  = raw.get("digests", [])
        archives = raw.get("archives", [])
    elif isinstance(raw, list):
        digests  = raw
        archives = []
    else:
        digests  = []
        archives = []

    tab_summary, tab_news, tab_social, tab_chatter, tab_local, tab_archive = st.tabs([
        "📊 Summary", "📰 News", "📱 Social", "💬 Chatter", "🏙 Local", "🗄 Archives"
    ])

    latest    = digests[0] if digests else {}
    stories   = latest.get("stories", [])
    breaking  = [s for s in stories if s.get("breaking_on_social")]
    digest_ts = latest.get("timestamp_ist","")

    # Detail panel — shown at top of active tab when a story is selected
    def maybe_show_detail():
        sel = st.session_state.get("selected_story")
        if sel:
            render_detail_panel(sel)

    # ── SUMMARY ──────────────────────────────────────────────────
    with tab_summary:
        c1, c2, c3 = st.columns([1,1,3])
        with c1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear(); st.rerun()
        with c2:
            if st.button("▶ Run Now", use_container_width=True):
                token = get_token()
                if not token:
                    st.error("GH_TOKEN not set")
                else:
                    r = requests.post(
                        f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/actions/workflows/stratum.yml/dispatches",
                        headers={"Authorization":f"token {token}","Accept":"application/vnd.github.v3+json"},
                        json={"ref":GITHUB_BRANCH}, timeout=10)
                    if r.status_code == 204:
                        st.success("✓ Running — refresh in ~3 min")
                    else:
                        st.error(f"Failed: {r.status_code}")

        if not digests:
            st.info("No digests yet. Click ▶ Run Now.")
            return

        v_count = sum(1 for s in stories if s.get("score",0)>=80)
        avg     = round(sum(s.get("score",0) for s in stories)/len(stories)) if stories else 0
        tg = latest.get("tg_count",0); tw = latest.get("tw_count",0); bk = latest.get("bk_count",0)

        st.html(f"""<div class="metric-row">
          <div class="metric-tile"><div class="metric-val">{len(stories)}</div><div class="metric-lbl">STORIES</div></div>
          <div class="metric-tile"><div class="metric-val" style="color:#16a34a">{v_count}</div><div class="metric-lbl">VERIFIED</div></div>
          <div class="metric-tile"><div class="metric-val">{avg}</div><div class="metric-lbl">AVG SCORE</div></div>
          <div class="metric-tile"><div class="metric-val" style="color:#dc2626">{len(breaking)}</div><div class="metric-lbl">BREAKING</div></div>
          <div class="metric-tile"><div class="metric-val" style="color:#0369a1">{tw}</div><div class="metric-lbl">X SIGNALS</div></div>
          <div class="metric-tile"><div class="metric-val" style="color:#0d9488">{bk}</div><div class="metric-lbl">BSKY</div></div>
          <div class="metric-tile"><div class="metric-val" style="color:#7c3aed">{tg}</div><div class="metric-lbl">TELEGRAM</div></div>
        </div>""")

        maybe_show_detail()

        if breaking:
            st.html('<div class="breaking-header"><div class="breaking-header-text">🔴 BREAKING — SOCIAL FIRST</div></div>')
            render_card_grid(breaking[:6], "sum_brk")

        st.html('<div class="section-header"><div class="section-header-text">✓ TOP STORIES</div></div>')
        top = [s for s in stories if not s.get("breaking_on_social") and not s.get("standalone_social")][:12]
        render_card_grid(top, "sum_top")

    MIN_SCORE = 25

    def is_wire_source(src):
        return not src.startswith("@") and not src.startswith("TG:") and not src.startswith("bsky:")

    def is_news_story(s):
        """Has at least one wire/publication source."""
        sources = s.get("sources", [])
        return any(is_wire_source(src) for src in sources) or (not sources and not s.get("standalone_social"))

    def is_social_story(s):
        """Primarily social — standalone or all sources are social handles."""
        if s.get("standalone_social"):
            return True
        sources = s.get("sources", [])
        if not sources:
            return False
        return all(not is_wire_source(src) for src in sources)

    # ── NEWS ─────────────────────────────────────────────────────
    with tab_news:
        maybe_show_detail()
        if not digests:
            st.info("No digests yet."); return
        for idx, dig in enumerate(digests):
            ts        = dig.get("timestamp_ist", dig.get("timestamp",""))
            d_st      = dig.get("stories",[])
            news_only = sorted(
                [s for s in d_st if is_news_story(s) and not s.get("standalone_social") and s.get("score",0) >= MIN_SCORE],
                key=lambda x: x.get("score",0), reverse=True
            )
            verified = sum(1 for s in news_only if s.get("score",0)>=80)
            avg_d    = round(sum(s.get("score",0) for s in news_only)/len(news_only)) if news_only else 0
            with st.expander(f"📅 {ts}  ·  {len(news_only)} stories  ·  {verified} verified  ·  avg {avg_d}", expanded=(idx==0)):
                render_card_grid(news_only, f"news_{idx}")

    # ── SOCIAL ───────────────────────────────────────────────────
    with tab_social:
        maybe_show_detail()
        if not digests:
            st.info("No digests yet."); return

        def is_recent_6h(story):
            """True if story's published_at is within 6 hours of now."""
            pub = story.get("published_at","")
            if not pub:
                return True
            try:
                clean  = pub.replace(" IST","").replace(" · "," ")
                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                dt     = datetime.strptime(f"{clean} {now_ist.year}", "%d %b %H:%M %Y")
                dt_utc = dt.replace(tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
                return (datetime.now(timezone.utc) - dt_utc).total_seconds() <= 6 * 3600
            except Exception:
                return True

        for idx, dig in enumerate(digests):
            ts    = dig.get("timestamp_ist", dig.get("timestamp",""))
            d_st  = dig.get("stories",[])
            apply_recency = (idx == 0)

            # Social-driven: must have social signals or be standalone
            # Wire can corroborate — fine. Recency applied to latest digest only.
            soc_st = sorted(
                [s for s in d_st if
                 (s.get("social_signals") or s.get("standalone_social")) and
                 s.get("score",0) >= MIN_SCORE and
                 (not apply_recency or is_recent_6h(s))],
                key=lambda x: x.get("score",0), reverse=True
            )

            if not soc_st:
                if idx == 0:
                    st.info("No social-driven stories in the past 6 hours. Older digests shown below.")
                continue

            label = f"📱 {ts}  ·  {len(soc_st)} social stories" + (" · last 6h" if apply_recency else "")
            with st.expander(label, expanded=(idx==0)):
                plat_filter = st.multiselect(
                    "Platform", ["X/Twitter","BlueSky","Telegram"],
                    default=["X/Twitter","BlueSky","Telegram"],
                    key=f"pf_{idx}")
                pmap = {"X/Twitter":"twitter","BlueSky":"bluesky","Telegram":"telegram"}
                sel  = {pmap[p] for p in plat_filter}
                filtered = [s for s in soc_st if
                            any(sig.get("platform") in sel for sig in s.get("social_signals",[]))
                            or (not s.get("social_signals") and s.get("standalone_social"))]
                render_card_grid(filtered, f"soc_{idx}")

    # ── CHATTER ──────────────────────────────────────────────────
    with tab_chatter:
        maybe_show_detail()
        if not digests:
            st.info("No digests yet."); return
        st.html("""<div style="background:#fef9c3;border-left:4px solid #eab308;border-radius:6px;padding:10px 16px;margin-bottom:16px;font-size:12px;color:#854d0e;">
          ⚡ <b>LOW CONFIDENCE SIGNALS</b> — Unverified, emerging, or single-source stories. Worth watching but not yet corroborated.
        </div>""")
        for idx, dig in enumerate(digests):
            ts    = dig.get("timestamp_ist", dig.get("timestamp",""))
            d_st  = dig.get("stories",[])
            # Chatter = score 20-49, any source type
            chatter = sorted(
                [s for s in d_st if 20 <= s.get("score",0) < 50],
                key=lambda x: x.get("score",0), reverse=True
            )
            if not chatter:
                continue
            with st.expander(f"💬 {ts}  ·  {len(chatter)} low-confidence signals", expanded=(idx==0)):
                render_card_grid(chatter, f"chat_{idx}")

    # ── LOCAL ────────────────────────────────────────────────────
    LOCAL_KEYWORDS = {
        "maharashtra","mumbai","thane","pune","nagpur","nashik",
        "navi mumbai","bmc","mmc","mhada","mmrda","konkan",
        "vidarbha","marathwada","aurangabad","shiv sena","ncp",
        "uddhav","fadnavis","devendra","eknath shinde",
    }

    with tab_local:
        maybe_show_detail()
        if not digests:
            st.info("No digests yet."); return
        for idx, dig in enumerate(digests):
            ts          = dig.get("timestamp_ist", dig.get("timestamp",""))
            local_items = dig.get("local_items", [])
            d_st        = dig.get("stories",[])

            # Clustered stories mentioning local keywords
            local_stories = sorted(
                [s for s in d_st if any(kw in (s.get("headline","")+" "+s.get("summary","")+" "+s.get("topic","")).lower() for kw in LOCAL_KEYWORDS) and s.get("score",0) >= MIN_SCORE],
                key=lambda x: x.get("score",0), reverse=True
            )

            if not local_items and not local_stories:
                continue

            with st.expander(f"🏙 {ts}  ·  {len(local_stories)} clustered  ·  {len(local_items)} raw headlines", expanded=(idx==0)):
                if local_stories:
                    st.html('<div style="font-size:10px;color:#94a3b8;font-family:monospace;margin-bottom:10px;">CLUSTERED STORIES</div>')
                    render_card_grid(local_stories, f"local_{idx}")

                if local_items:
                    st.html('<div style="font-size:10px;color:#94a3b8;font-family:monospace;margin:16px 0 10px;">RAW HEADLINES</div>')
                    # Convert raw items to play-card format using weight as score
                    cols = st.columns(3)
                    for i, item in enumerate(local_items[:30]):
                        w      = item.get("weight", 70)
                        sc, sbg, lbl = score_color(w)
                        src    = safe(item.get("source",""))
                        title  = safe(item.get("title",""))
                        summ   = safe(item.get("summary",""))[:120]
                        url    = item.get("url","")
                        pub    = safe(item.get("published_at",""))
                        link   = f'<a href="{url}" target="_blank" style="font-size:10px;color:#0369a1;text-decoration:none;font-weight:600;font-family:monospace;">READ →</a>' if url else ""
                        with cols[i % 3]:
                            st.html(f"""
                            <div class="play-card" style="border-top:4px solid {sc};">
                              <div class="play-card-score">
                                <div class="play-card-score-num" style="color:{sc};">{w}</div>
                                <div class="play-card-score-meta"><span class="play-card-label" style="color:{sc};">{lbl}</span></div>
                              </div>
                              <div class="play-card-pills">
                                <span class="play-card-domain" style="color:#be185d;background:#be185d18;">LOCAL</span>
                              </div>
                              <div class="play-card-headline">{title}</div>
                              <div style="font-size:12px;color:#64748b;line-height:1.5;flex:1;">{summ}</div>
                              <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
                                <div class="play-card-sources">{src}</div>
                                <div style="font-size:9px;color:#94a3b8;font-family:monospace;">{pub}</div>
                              </div>
                              {link}
                            </div>""")

    # ── ARCHIVES ─────────────────────────────────────────────────
    with tab_archive:
        maybe_show_detail()
        if not archives:
            st.info("No archives yet. Digests move here after 7 days.")
            return
        st.html(f"<div style='font-size:11px;color:#94a3b8;margin-bottom:16px;font-family:monospace;'>{len(archives)} archived digests</div>")
        for idx, dig in enumerate(archives):
            ts    = dig.get("timestamp_ist", dig.get("timestamp",""))
            d_st  = dig.get("stories",[])
            avg_d = dig.get("avg_score",0)
            with st.expander(f"🗄 {ts}  ·  {len(d_st)} stories  ·  avg {avg_d}", expanded=False):
                render_card_grid(d_st, f"arch_{idx}")

if __name__ == "__main__":
    main()
