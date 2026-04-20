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
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  .stApp { background: #f1f5f9; }
  .stratum-header { background:#fff; border-radius:10px; padding:16px 24px; margin-bottom:16px; border:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; }
  .stratum-wordmark { font-size:22px; font-weight:600; letter-spacing:6px; color:#0f172a; }
  .stratum-sub { font-size:9px; color:#94a3b8; letter-spacing:2px; margin-top:3px; font-family:monospace; }
  .metric-row { display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
  .metric-tile { background:#fff; border-radius:8px; padding:12px 18px; border:1px solid #e2e8f0; min-width:90px; flex:1; text-align:center; }
  .metric-val { font-size:26px; font-weight:600; color:#0f172a; line-height:1; }
  .metric-lbl { font-size:9px; color:#94a3b8; letter-spacing:1px; margin-top:4px; font-family:monospace; }
  .breaking-header { background:#dc2626; border-radius:6px; padding:10px 16px; margin-bottom:10px; }
  .breaking-header-text { font-size:12px; font-weight:600; color:#fff; letter-spacing:2px; font-family:monospace; }
  .section-header { background:#0f172a; border-radius:6px; padding:10px 16px; margin:16px 0 10px; }
  .section-header-text { font-size:12px; font-weight:600; color:#fff; letter-spacing:2px; font-family:monospace; }
  .topic-card { background:#fff; border-radius:8px; margin-bottom:10px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.04); }
  .card-inner { display:flex; }
  .score-col { width:70px; min-width:70px; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:16px 4px; text-align:center; }
  .score-num { font-size:26px; font-weight:600; line-height:1; }
  .score-lbl { font-size:7px; letter-spacing:0.8px; margin-top:2px; opacity:0.8; font-family:monospace; }
  .card-body { flex:1; padding:14px 16px; }
  .domain-pill { font-size:9px; font-weight:600; letter-spacing:1px; padding:2px 8px; border-radius:3px; display:inline-block; margin-right:6px; font-family:monospace; }
  .topic-pill { font-size:9px; color:#64748b; background:#f1f5f9; padding:2px 8px; border-radius:3px; display:inline-block; margin-right:6px; font-family:monospace; }
  .headline { font-size:16px; font-weight:600; color:#0f172a; line-height:1.4; margin:8px 0; }
  .summary { font-size:13px; color:#475569; line-height:1.7; margin-bottom:10px; }
  .signal-box { font-size:12px; color:#64748b; font-style:italic; padding-left:10px; margin-bottom:8px; }
  .signal-label { font-family:monospace; font-size:8px; font-weight:600; font-style:normal; letter-spacing:0.5px; }
  .context-banner { background:#fef9c3; border-left:3px solid #eab308; border-radius:3px; padding:7px 10px; margin-bottom:8px; font-size:11px; color:#854d0e; }
  .social-section { border-top:1px solid #f1f5f9; padding-top:10px; margin-top:10px; }
  .social-header { font-size:8px; color:#94a3b8; letter-spacing:0.5px; margin-bottom:6px; font-family:monospace; }
  .social-item { background:#f8fafc; border-radius:4px; padding:7px 10px; margin-bottom:5px; border-left:2px solid #d97706; font-size:12px; color:#374151; line-height:1.5; }
  .social-handle { font-size:9px; font-weight:600; font-family:monospace; }
  .unverified-badge { font-size:8px; background:#fef2f2; color:#dc2626; padding:1px 5px; border-radius:2px; font-weight:600; margin-left:6px; font-family:monospace; }
</style>
""", unsafe_allow_html=True)

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
        return {} if filename == "digests.json" else []
    except Exception as e:
        st.error(f"Failed to fetch {filename}: {e}")
        return {} if filename == "digests.json" else []

def push_github_json(filename, data, message):
    import base64
    token = get_token()
    if not token:
        st.error("GH_TOKEN not set.")
        return False
    url     = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r       = requests.get(url, headers=headers, timeout=10)
    sha     = r.json().get("sha", "") if r.status_code == 200 else ""
    content = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    payload = {"message": message, "content": content, "branch": GITHUB_BRANCH}
    if sha:
        payload["sha"] = sha
    r2 = requests.put(url, headers=headers, json=payload, timeout=15)
    return r2.status_code in (200, 201)

def safe(text):
    if not text:
        return ""
    stripped = re.sub(r"<[^>]+>", "", str(text)).strip()
    return htmllib.escape(stripped, quote=True)

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
PLATFORM_META = {
    "twitter":  ("#0369a1","X"),
    "bluesky":  ("#0d9488","BSKY"),
    "telegram": ("#7c3aed","TG"),
}

def render_card(story, starred_ids, digest_ts=None, key_prefix="feed"):
    sc, sbg, label = score_color(story["score"])
    dc          = DOMAIN_COLORS.get(story.get("domain",""), "#475569")
    trend       = story.get("trend","stable")
    ts          = TREND_SYMBOLS.get(trend,"─")
    tc          = TREND_COLORS.get(trend,"#94a3b8")
    sigs        = story.get("social_signals",[])
    topic       = safe(story.get("topic",""))
    sources     = " · ".join(safe(s) for s in story.get("sources",[]))
    headline    = safe(story.get("headline",""))
    summary     = safe(story.get("summary",""))
    signal      = safe(story.get("signal",""))
    context     = safe(story.get("context",""))
    source_url  = story.get("source_url","")
    is_standalone = story.get("standalone_social", False)
    read_more   = f'<a href="{source_url}" target="_blank" style="font-size:9px;color:#0369a1;text-decoration:none;font-weight:600;font-family:monospace;">READ SOURCE →</a>' if source_url else ""
    ctx_banner  = f'<div class="context-banner">⚡ <b>UNVERIFIED SOCIAL SIGNAL</b> · {context}</div>' if is_standalone and context else ""
    bsoc_badge  = '<span style="font-size:9px;background:#e0f2fe;color:#0369a1;padding:1px 6px;border-radius:2px;font-weight:600;margin-left:6px;font-family:monospace;">BROKE ON SOCIAL</span>' if story.get("breaking_on_social") else ""
    sid         = f"{digest_ts}_{story.get('rank',0)}_{story.get('headline','')[:30]}"
    is_star     = sid in starred_ids

    sig_items = ""
    for sig in sigs[:3]:
        plat    = sig.get("platform","twitter")
        pc, pl  = PLATFORM_META.get(plat,("#94a3b8","SRC"))
        url     = sig.get("url","")
        lnk     = f' <a href="{url}" target="_blank" style="color:#0369a1;font-size:9px;text-decoration:none;font-weight:600;">VIEW →</a>' if url else ""
        sig_items += f"""<div class="social-item">
          <span class="social-handle" style="color:{pc};">{pl} · @{sig.get('handle','?')}</span>
          <span class="unverified-badge">UNVERIFIED</span>
          <span style="font-family:monospace;font-size:9px;color:#d97706;font-weight:600;margin-left:6px;">[{sig.get('score',0)}]</span>
          {lnk}
          <div style="margin-top:4px;">{safe(sig.get('text',''))[:180]}</div>
        </div>"""
    social_html = f'<div class="social-section"><div class="social-header">⚡ {len(sigs)} SOCIAL SIGNAL{"S" if len(sigs)!=1 else ""}</div>{sig_items}</div>' if sigs else ""

    star_border = 'border:2px solid #f59e0b;' if is_star else ''
    card_html = f"""
    <div class="topic-card" style="{star_border}">
      <div class="card-inner">
        <div class="score-col" style="background:{sbg};border-right:3px solid {sc};">
          <div class="score-num" style="color:{sc};">{story['score']}</div>
          <div class="score-lbl" style="color:{sc};">{label}</div>
          <div style="font-size:14px;color:{tc};margin-top:8px;font-weight:600;">{ts}</div>
        </div>
        <div class="card-body">
          <div style="margin-bottom:6px;">
            <span class="domain-pill" style="color:{dc};background:{dc}18;">{story.get('domain','').upper()}</span>
            <span class="topic-pill">{topic}</span>
            {bsoc_badge}
            <span style="font-size:9px;color:#94a3b8;font-family:monospace;">{sources}</span>
          </div>
          <div class="headline">{headline}</div>
          {ctx_banner}
          <div class="summary">{summary}</div>
          <div class="signal-box" style="border-left:3px solid {sc};">
            <span class="signal-label" style="color:{sc};">SIGNAL · </span>{signal}
          </div>
          {read_more}
          {social_html}
        </div>
        <div style="width:26px;min-width:26px;display:flex;align-items:flex-start;justify-content:center;padding-top:14px;">
          <span style="font-size:9px;color:#cbd5e1;font-family:monospace;">#{story.get('rank',0)}</span>
        </div>
      </div>
    </div>"""
    st.html(card_html)

    _, col2 = st.columns([6,1])
    with col2:
        lbl = "★ Unstar" if is_star else "☆ Star"
        if st.button(lbl, key=f"{key_prefix}_star_{sid}", use_container_width=True):
            if is_star:
                starred_ids.discard(sid)
                starred = fetch_github_json("starred.json")
                starred = [s for s in starred if s.get("id") != sid]
                ok = push_github_json("starred.json", starred, f"unstar: {story['headline'][:40]}")
                (st.success("Unstarred") if ok else st.error("Failed"))
            else:
                starred_ids.add(sid)
                starred = fetch_github_json("starred.json")
                starred.append({
                    "id": sid, "digest_ts": digest_ts,
                    "starred_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
                    "story": story,
                })
                ok = push_github_json("starred.json", starred, f"star: {story['headline'][:40]}")
                (st.success("⭐ Starred!") if ok else st.error("Failed"))
            st.rerun()

def main():
    st.html("""
    <div class="stratum-header">
      <div>
        <div class="stratum-wordmark">STRATUM</div>
        <div class="stratum-sub">VERIFIED SIGNAL DIGEST</div>
      </div>
    </div>""")

    with st.spinner("Loading..."):
        raw         = fetch_github_json("digests.json")
        starred_raw = fetch_github_json("starred.json")

    if isinstance(raw, dict):
        digests  = raw.get("digests", [])
        archives = raw.get("archives", [])
    elif isinstance(raw, list):
        digests  = raw
        archives = []
    else:
        digests  = []
        archives = []

    if not isinstance(starred_raw, list):
        starred_raw = []

    now_utc     = datetime.now(timezone.utc)
    starred_ids = set()
    for s in starred_raw:
        try:
            exp = datetime.fromisoformat(s.get("expires_at","").replace("Z","+00:00"))
            if exp > now_utc:
                starred_ids.add(s["id"])
        except Exception:
            starred_ids.add(s.get("id",""))

    tab_summary, tab_news, tab_social, tab_starred, tab_archive = st.tabs([
        "📊 Summary", "📰 News", "📱 Social", "★ Starred", "🗄 Archives"
    ])

    latest    = digests[0] if digests else {}
    stories   = latest.get("stories", [])
    breaking  = [s for s in stories if s.get("breaking_on_social")]
    digest_ts = latest.get("timestamp_ist","")

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
                    st.success("✓ Running — refresh in ~3 min") if r.status_code==204 else st.error(f"Failed: {r.status_code}")

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

        if breaking:
            st.html('<div class="breaking-header"><div class="breaking-header-text">🔴 BREAKING — SOCIAL FIRST</div></div>')
            for s in breaking[:5]:
                render_card(s, starred_ids, digest_ts=digest_ts, key_prefix="sum_brk")

        st.html('<div class="section-header"><div class="section-header-text">✓ TOP VERIFIED STORIES</div></div>')
        top = [s for s in stories if not s.get("breaking_on_social")][:8]
        for s in top:
            render_card(s, starred_ids, digest_ts=digest_ts, key_prefix="sum_top")

    # ── NEWS ─────────────────────────────────────────────────────
    with tab_news:
        if not digests:
            st.info("No digests yet."); return
        for dig in digests:
            ts       = dig.get("timestamp_ist", dig.get("timestamp",""))
            d_st     = dig.get("stories",[])
            news_only = [s for s in d_st if not s.get("standalone_social")]
            verified  = sum(1 for s in news_only if s.get("score",0)>=80)
            avg_d     = round(sum(s.get("score",0) for s in news_only)/len(news_only)) if news_only else 0
            with st.expander(f"📅 {ts}  ·  {len(news_only)} stories  ·  {verified} verified  ·  avg {avg_d}", expanded=(dig==digests[0])):
                for s in news_only:
                    render_card(s, starred_ids, digest_ts=ts, key_prefix=f"news_{ts[:10]}")

    # ── SOCIAL ───────────────────────────────────────────────────
    with tab_social:
        if not digests:
            st.info("No digests yet."); return
        for dig in digests:
            ts      = dig.get("timestamp_ist", dig.get("timestamp",""))
            d_st    = dig.get("stories",[])
            soc_st  = [s for s in d_st if s.get("standalone_social") or s.get("breaking_on_social")]
            if not soc_st:
                continue
            with st.expander(f"📱 {ts}  ·  {len(soc_st)} social stories", expanded=(dig==digests[0])):
                plat_filter = st.multiselect(
                    "Platform", ["X/Twitter","BlueSky","Telegram"],
                    default=["X/Twitter","BlueSky","Telegram"],
                    key=f"pf_{ts[:10]}")
                pmap = {"X/Twitter":"twitter","BlueSky":"bluesky","Telegram":"telegram"}
                sel  = {pmap[p] for p in plat_filter}
                for s in soc_st:
                    sigs = s.get("social_signals",[])
                    if any(sig.get("platform") in sel for sig in sigs) or (not sigs and s.get("standalone_social")):
                        render_card(s, starred_ids, digest_ts=ts, key_prefix=f"soc_{ts[:10]}")

    # ── STARRED ──────────────────────────────────────────────────
    with tab_starred:
        if not starred_raw:
            st.html('<div style="text-align:center;padding:60px 0;color:#94a3b8;font-family:monospace;"><div style="font-size:32px;margin-bottom:12px;">☆</div><div>NO STARRED TOPICS YET</div></div>')
            return
        active  = [s for s in starred_raw if s.get("id") in starred_ids]
        expired = [s for s in starred_raw if s.get("id") not in starred_ids]
        st.html(f"<div style='font-size:11px;color:#94a3b8;margin-bottom:16px;font-family:monospace;'>{len(active)} active · {len(expired)} expired</div>")
        for item in active:
            story    = item.get("story",{})
            dts_item = item.get("digest_ts","")
            try:
                star_str = datetime.fromisoformat(item.get("starred_at","").replace("Z","+00:00")).strftime("%d %b %Y · %H:%M")
            except Exception:
                star_str = ""
            st.html(f"<div style='font-size:9px;color:#f59e0b;margin-bottom:4px;font-family:monospace;'>★ STARRED {star_str}</div>")
            render_card(story, starred_ids, digest_ts=dts_item, key_prefix="starred")
        if expired:
            with st.expander(f"Expired ({len(expired)})"):
                for item in expired:
                    s = item.get("story",{})
                    st.html(f"<div style='font-size:9px;color:#94a3b8;font-family:monospace;'>★ expired · {safe(s.get('headline',''))}</div>")

    # ── ARCHIVES ─────────────────────────────────────────────────
    with tab_archive:
        if not archives:
            st.info("No archives yet. Digests move here after 7 days.")
            return
        st.html(f"<div style='font-size:11px;color:#94a3b8;margin-bottom:16px;font-family:monospace;'>{len(archives)} archived digests</div>")
        for dig in archives:
            ts    = dig.get("timestamp_ist", dig.get("timestamp",""))
            d_st  = dig.get("stories",[])
            avg_d = dig.get("avg_score",0)
            with st.expander(f"🗄 {ts}  ·  {len(d_st)} stories  ·  avg {avg_d}", expanded=False):
                for s in d_st:
                    render_card(s, starred_ids, digest_ts=ts, key_prefix=f"arch_{ts[:10]}")

if __name__ == "__main__":
    main()
