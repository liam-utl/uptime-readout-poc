import streamlit as st
import requests
import json
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Uptime Labs Readout",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3 {
    font-family: 'Space Mono', monospace;
}
.stApp {
    background: #0d0f14;
    color: #e8eaf0;
}
.sidebar .sidebar-content {
    background: #13151c;
}
.metric-card {
    background: #1a1d26;
    border: 1px solid #2a2d3a;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.tag-complete   { background:#16a34a22; color:#4ade80; border:1px solid #16a34a; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-family:'Space Mono',monospace; }
.tag-partial    { background:#ca8a0422; color:#fbbf24; border:1px solid #ca8a04; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-family:'Space Mono',monospace; }
.tag-none       { background:#dc262622; color:#f87171; border:1px solid #dc2626; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-family:'Space Mono',monospace; }
.tag-practicing { background:#2563eb22; color:#60a5fa; border:1px solid #2563eb; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-family:'Space Mono',monospace; }
.tag-strengthening { background:#7c3aed22; color:#c4b5fd; border:1px solid #7c3aed; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-family:'Space Mono',monospace; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    bearer_token = st.text_input("Bearer Auth Token", type="password", placeholder="eyJ...")
    # openai_key   = st.text_input("OpenAI API Key",    type="password", placeholder="sk-...")
    st.divider()
    # st.caption("Tokens are used only for API calls in this session and are never stored.")

# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown("# Uptime Labs Readout")
st.markdown("Generate comparative reports across multiple players for a given level.")

col_email, col_level = st.columns([3, 1])
with col_email:
    emails_input = st.text_area(
        "Player Email Addresses",
        placeholder="alice@example.com, bob@example.com, carol@example.com",
        height=80,
    )
with col_level:
    level = st.selectbox("Level", list(range(1, 35)), index=0)

run = st.button("Generate Report", use_container_width=True, type="primary")

# ── Helper functions ──────────────────────────────────────────────────────────
BASE = "https://api.prod.uptimelabs.io"

def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def fetch_sessions(email: str, token: str) -> list:
    url = f"{BASE}/admin/player/{email}/sessions"
    try:
        r = requests.get(url, headers=get_headers(token), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Sessions fetch failed for {email}: {e}")
        return []

def fetch_report(email: str, session_id: int, token: str) -> dict | None:
    url = f"{BASE}/report/player/{email}/{session_id}"
    try:
        r = requests.get(url, headers=get_headers(token), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Report fetch failed for {email}/{session_id}: {e}")
        return None

def grade_badge(grade: str) -> str:
    g = (grade or "").strip().lower()
    if g == "Complete":
        return f'<span class="tag-complete">Complete</span>'
    elif g == "Partial":
        return f'<span class="tag-partial">Partial</span>'
    else:
        return f'<span class="tag-none">None</span>'

def competency_badge(comp: str) -> str:
    c = (comp or "").strip().lower()
    if "Strengthening" in c:
        return f'<span class="tag-strengthening">{comp}</span>'
    elif "Practicing" in c:
        return f'<span class="tag-practicing">{comp}</span>'
    else:
        return f'<span class="tag-none">{comp}</span>'

# ── Report generation ─────────────────────────────────────────────────────────
if run:
    if not bearer_token:
        st.error("Please enter a Bearer Auth Token in the sidebar.")
        st.stop()
    if not emails_input.strip():
        st.error("Please enter at least one email address.")
        st.stop()

    emails = [e.strip() for e in emails_input.split(",") if e.strip()]
    selected_level_id = level  # the dropdown integer value

    # ── Step 1: collect sessions filtered by level ────────────────────────────
    st.markdown("---")
    st.markdown(f"##### Fetching sessions for Level {level}")
    progress = st.progress(0)
    filtered: list[dict] = []  # {email, session_id, level}

    for i, email in enumerate(emails):
        with st.spinner(f"Fetching sessions for {email}…"):
            sessions = fetch_sessions(email, bearer_token)
        for s in sessions:
            lvl_id = s.get("level", {}).get("id")
            # Match by level id == selected level (1-10 maps to level ids)
            # The dropdown is 1-10; compare against level.id
            if lvl_id == selected_level_id:
                filtered.append({
                    "email":      email,
                    "session_id": s["id"],
                    "level":      lvl_id,
                })
        progress.progress((i + 1) / len(emails))

    if not filtered:
        st.warning(f"No sessions found at Level {level} for any of the provided emails.")
        st.stop()

    st.success(f"Found **{len(filtered)}** session(s) at Level {level}.")
    with st.expander("View session list"):
        st.json(filtered)

    # ── Step 2: fetch reports for each session ────────────────────────────────
    st.markdown("##### Fetching detailed reports")
    progress2 = st.progress(0)
    reports: list[dict] = []   # {email, session_id, data}

    for i, item in enumerate(filtered):
        with st.spinner(f"Fetching report for {item['email']} / session {item['session_id']}…"):
            data = fetch_report(item["email"], item["session_id"], bearer_token)
        if data:
            reports.append({"email": item["email"], "session_id": item["session_id"], "data": data})
        progress2.progress((i + 1) / len(filtered))

    if not reports:
        st.warning("No reports were returned.")
        st.stop()

    st.success(f"Retrieved **{len(reports)}** report(s).")

    # ── Step 3: build markdown report ────────────────────────────────────────
    md = ""
    st.markdown("---")
    md = md + "---\n"
    st.markdown("## Comparative Report")
    md = md + "## Comparative Report\n"

    # ── Table 1: Learning Outcomes ────────────────────────────────────────────
    st.markdown("### Learning Outcomes")
    md = md + "### Learning Outcomes\n"

    # Gather all unique learning outcome titles
    all_lo_titles: list[str] = []
    for rep in reports:
        for sf in rep["data"].get("sessionFeedback", []):
            for lo in sf.get("learning_outcomes", []):
                t = lo.get("title", "")
                if t and t not in all_lo_titles:
                    all_lo_titles.append(t)

    if all_lo_titles:
        # Build header
        header = "| Player |" + "".join(f" {t} |" for t in all_lo_titles)
        sep    = "|--------|" + "".join("--------|" for _ in all_lo_titles)
        rows   = [header, sep]
        for rep in reports:
            lo_map = {}
            for sf in rep["data"].get("sessionFeedback", []):
                for lo in sf.get("learning_outcomes", []):
                    lo_map[lo.get("title", "")] = lo.get("competency", "—")
            row = f"| {rep['email']} |"
            for t in all_lo_titles:
                row += f" {lo_map.get(t, '—')} |"
            rows.append(row)
        st.markdown("\n".join(rows))
        md = md + "\n".join(rows) + "\n"
    else:
        st.info("No learning_outcomes data found in the responses.")

    st.markdown("")
    md = md + "\n"

    # ── Table 2: Incident Checklist ───────────────────────────────────────────
    st.markdown("### Incident Checklist")
    md = md + "### Incident Checklist\n"

    all_ic_tasks: list[str] = []
    for rep in reports:
        for task in rep["data"].get("incidentChecklist", []):
            t = task.get("task", "")
            if t and t not in all_ic_tasks:
                all_ic_tasks.append(t)

    if all_ic_tasks:
        header = "| Player |" + "".join(f" {t} |" for t in all_ic_tasks)
        sep    = "|--------|" + "".join("--------|" for _ in all_ic_tasks)
        rows   = [header, sep]
        for rep in reports:
            ic_map = {item.get("task", ""): item.get("grade", "—") for item in rep["data"].get("incidentChecklist", [])}
            row = f"| {rep['email']} |"
            for t in all_ic_tasks:
                row += f" {ic_map.get(t, '—')} |"
            rows.append(row)
        st.markdown("\n".join(rows))
        md = md + "\n".join(rows) + "\n"
    else:
        st.info("No incidentChecklist data found.")

    st.markdown("")
    md = md + "\n"

    # ── Table 3: Drill Checklist ──────────────────────────────────────────────
    st.markdown("### Drill Checklist")
    md = md + "### Drill Checklist\n"

    all_dc_tasks: list[str] = []
    for rep in reports:
        for task in rep["data"].get("drillChecklist", []):
            t = task.get("task", "")
            if t and t not in all_dc_tasks:
                all_dc_tasks.append(t)

    if all_dc_tasks:
        header = "| Player |" + "".join(f" {t} |" for t in all_dc_tasks)
        sep    = "|--------|" + "".join("--------|" for _ in all_dc_tasks)
        rows   = [header, sep]
        for rep in reports:
            dc_map = {item.get("task", ""): item.get("grade", "—") for item in rep["data"].get("drillChecklist", [])}
            row = f"| {rep['email']} |"
            for t in all_dc_tasks:
                row += f" {dc_map.get(t, '—')} |"
            rows.append(row)
        st.markdown("\n".join(rows))
        md = md + "\n".join(rows) + "\n"
    else:
        st.info("No drillChecklist data found.")

    # ── Individual player cards ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Individual Player Reports")

    for rep in reports:
        d = rep["data"]
        with st.expander(f"📋 {rep['email']}  —  Session {rep['session_id']}  |  {d.get('drillName','')}", expanded=False):

            # Summary row
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Drill Type",    d.get("drillType", "—"))
            c2.metric("Duration",      d.get("drillDuration", "—"))
            c3.metric("Status",        d.get("completionStatus", "—"))
            c4.metric("# Drills",      d.get("numberOfDrills", "—"))

            # Stars & Hints
            stars_hints = d.get("starsAndHintsDetails", [])
            if stars_hints:
                st.markdown("#### ⭐ Stars & Hints")
                for item in stars_hints:
                    icon = "⭐" if item.get("type") == "star" else "💡"
                    st.markdown(
                        f"**{icon} {item.get('message','')}** "
                        f"*(x{item.get('occurrences',1)} · {', '.join(item.get('competency',[]))} · {item.get('timeAwarded','')})* \n\n"
                        f"{item.get('rationale','')}"
                    )

            # Session Feedback
            for sf in d.get("sessionFeedback", []):
                # Feedback tiles
                feedback_items = sf.get("feedback", [])
                if feedback_items:
                    st.markdown("#### Session Feedback")
                    fb_cols = st.columns(min(len(feedback_items), 2))
                    for idx, fb in enumerate(feedback_items):
                        with fb_cols[idx % 2]:
                            st.markdown(f"**{fb.get('title','')}**\n\n{fb.get('message','')}")

                # What went well / improve
                ww = sf.get("what_went_well", [])
                wi = sf.get("where_to_improve", [])
                if ww or wi:
                    ww_col, wi_col = st.columns(2)
                    with ww_col:
                        st.markdown("#### ✅ What Went Well")
                        for item in ww:
                            st.success(item)
                    with wi_col:
                        st.markdown("#### 🔺 Where to Improve")
                        for item in wi:
                            st.warning(item)

                # Learning outcomes detail
                los = sf.get("learning_outcomes", [])
                if los:
                    st.markdown("#### Learning Outcomes")
                    for lo in los:
                        st.markdown(
                            f"**{lo.get('title','')}** &nbsp; {competency_badge(lo.get('competency',''))}  \n"
                            f"{lo.get('message','')}",
                            unsafe_allow_html=True,
                        )

    # ── Raw JSON download ─────────────────────────────────────────────────────
    st.markdown("---")
    st.download_button(
        "⬇️  Download raw report data (JSON)",
        # data=json.dumps(reports, indent=2),
        data= md,
        file_name=f"player_reports_level{level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="application/markdown",
    )