import streamlit as st
import requests
import json
from datetime import datetime
import litellm

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Player Progress Report",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}
.stTextInput > label, .stTextArea > label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7c7c8a;
}
.report-block {
    background: #0f0f14;
    border: 1px solid #2a2a3a;
    border-radius: 4px;
    padding: 2rem;
    margin-top: 1rem;
    color: #e0e0f0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    line-height: 1.7;
    white-space: pre-wrap;
}
.status-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 2px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
}
.badge-ok   { background:#1a3a2a; color:#4ade80; border:1px solid #4ade80; }
.badge-err  { background:#3a1a1a; color:#f87171; border:1px solid #f87171; }
.badge-info { background:#1a2a3a; color:#60a5fa; border:1px solid #60a5fa; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.divider()
    bearer_token = st.text_input(
        "Bearer Auth Token",
        type="password",
        placeholder="eyJ...",
        help="Used in Authorization header for all API calls",
    )
    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Used by LiteLLM to generate the progress report",
    )
    st.divider()
    st.caption("All credentials are used only within this session and never stored.")

# ── Helpers ───────────────────────────────────────────────────────────────────
BASE = "https://api.prod.uptimelabs.io"

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_sessions(email: str, token: str):
    url = f"{BASE}/admin/player/{email}/sessions"
    resp = requests.get(url, headers=auth_headers(token), timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_session_report(email: str, session_id: int, token: str):
    url = f"{BASE}/report/player/{email}/{session_id}"
    resp = requests.get(url, headers=auth_headers(token), timeout=30)
    resp.raise_for_status()
    return resp.json()


def llm_summarise(prompt: str, openai_key: str) -> str:
    litellm.api_key = openai_key
    response = litellm.completion(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        # api_base="http://localhost:11434",
    )
    return response.choices[0].message.content.strip()


def build_improve_prompt(items: list[str]) -> str:
    joined = "\n\n---\n\n".join(
        [f"Session {i+1}:\n{item}" for i, item in enumerate(items)]
    )
    return (
        "You are an expert learning & development coach analysing a player's incident management training.\n\n"
        "Below are 'areas to improve' notes collected across multiple training sessions:\n\n"
        f"{joined}\n\n"
        "Write a comprehensive, forward-looking improvement report (3-5 paragraphs) that:\n"
        "- Identifies recurring themes and patterns\n"
        "- Offers specific, actionable advice\n"
        "- Uses an encouraging but honest tone\n"
        "- Is formatted in clear Markdown with headers"
    )


def build_went_well_prompt(items: list[str]) -> str:
    joined = "\n\n---\n\n".join(
        [f"Session {i+1}:\n{item}" for i, item in enumerate(items)]
    )
    return (
        "You are an expert learning & development coach analysing a player's incident management training.\n\n"
        "Below are 'what went well' notes collected across multiple training sessions:\n\n"
        f"{joined}\n\n"
        "Write a comprehensive strengths report (3-5 paragraphs) that:\n"
        "- Highlights consistent strengths and positive patterns\n"
        "- Explains how these strengths benefit the team\n"
        "- Uses motivating language\n"
        "- Is formatted in clear Markdown with headers"
    )


def build_markdown_report(
    email: str,
    sessions: list,
    reports: list[dict],
    went_well_summary: str,
    improve_summary: str,
) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"### Player Progress Report",
        f"",
        f"> **Player:** `{email}`  ",
        f"> **Generated:** {now}  ",
        f"> **Sessions analysed:** {len(sessions)}",
        f"",
        f"---",
        f"",
        f"### Session Overview",
        f"",
        f"| Session ID | Drill | Date | Role | Duration | Status |",
        f"|-----------|-------|------|------|----------|--------|",
    ]

    for r in reports:
        sid = r.get("sessionId", "—")
        drill = r.get("drillName", "—")
        date = r.get("date", "—")
        role = r.get("role", r.get("drillType", "—"))
        duration = r.get("drillDuration", "—")
        status = r.get("completionStatus", "—")
        lines.append(f"| {sid} | {drill} | {date} | {role} | {duration} | {status} |")

    lines += [
        f"",
        f"---",
        f"",
        f"### What Went Well — Synthesised Analysis",
        f"",
        went_well_summary,
        f"",
        f"---",
        f"",
        f"### Areas for Improvement — Synthesised Analysis",
        f"",
        improve_summary,
        # f"",
        # f"---",
        # f"",
        # f"## 📊 Per-Session Detail",
        # f"",
    ]

    # for r in reports:
    #     sid = r.get("sessionId", "—")
    #     drill = r.get("drillName", "—")
    #     lines += [
    #         f"### Session {sid} — {drill}",
    #         f"",
    #     ]

    #     feedback_list = r.get("sessionFeedback", [])
    #     if feedback_list:
    #         fb = feedback_list[0]

    #         went_well = fb.get("what_went_well", [])
    #         if went_well:
    #             lines.append("**✅ What Went Well**")
    #             lines.append("")
    #             for item in went_well:
    #                 lines.append(f"{item}")
    #             lines.append("")

    #         to_improve = fb.get("where_to_improve", [])
    #         if to_improve:
    #             lines.append("**🔧 Where to Improve**")
    #             lines.append("")
    #             for item in to_improve:
    #                 lines.append(f"{item}")
    #             lines.append("")

    #     lines.append("---")
    #     lines.append("")

    return "\n".join(lines)


# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown("# Individual Player Progress Report")

st.caption("Enter a player email below and click **Generate Report** to fetch session data and produce an AI-powered analysis.")

email_input = st.text_input("Player Email Address", placeholder="john@email.io")

run_btn = st.button("Generate Report", type="primary", use_container_width=True)

if run_btn:
    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not email_input.strip():
        errors.append("Please enter a player email address.")
    if not bearer_token:
        errors.append("Please add your Bearer Auth Token in the sidebar.")
    if not openai_key:
        errors.append("Please add your OpenAI API Key in the sidebar.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    email = email_input.strip()

    # ── Step 1: Fetch sessions ────────────────────────────────────────────────
    with st.status("Fetching sessions…", expanded=True) as status:
        try:
            sessions = get_sessions(email, bearer_token)
            session_ids = [s["id"] for s in sessions]
            st.write(f"✅ Found **{len(session_ids)}** sessions: {session_ids}")
        except Exception as exc:
            status.update(label="Error fetching sessions", state="error")
            st.error(f"Failed to fetch sessions: {exc}")
            st.stop()

        # ── Step 2: Fetch per-session reports ─────────────────────────────────
        reports = []
        failed = []
        for sid in session_ids:
            try:
                report = get_session_report(email, sid, bearer_token)
                reports.append(report)
                st.write(f"✅ Retrieved report for session **{sid}**")
            except Exception as exc:
                failed.append(sid)
                st.write(f"⚠️ Session **{sid}** failed: {exc}")

        if failed:
            st.warning(f"Could not retrieve {len(failed)} session(s): {failed}")

        if not reports:
            status.update(label="No reports retrieved", state="error")
            st.error("No session reports could be fetched. Cannot generate analysis.")
            st.stop()

        # ── Step 3: LLM calls ─────────────────────────────────────────────────
        st.write("🤖 Generating AI analysis…")

        went_well_texts = []
        improve_texts = []
        for r in reports:
            for fb in r.get("sessionFeedback", []):
                went_well_texts.extend(fb.get("what_went_well", []))
                improve_texts.extend(fb.get("where_to_improve", []))

        try:
            went_well_summary = llm_summarise(build_went_well_prompt(went_well_texts), openai_key)
            st.write("✅ 'What went well' analysis complete")
        except Exception as exc:
            went_well_summary = f"*(LLM call failed: {exc})*"
            st.warning(f"'What went well' LLM call failed: {exc}")

        try:
            improve_summary = llm_summarise(build_improve_prompt(improve_texts), openai_key)
            st.write("✅ 'Areas to improve' analysis complete")
        except Exception as exc:
            improve_summary = f"*(LLM call failed: {exc})*"
            st.warning(f"'Areas to improve' LLM call failed: {exc}")

        status.update(label="All done!", state="complete", expanded=False)

    # ── Render report ─────────────────────────────────────────────────────────
    md_report = build_markdown_report(
        email, sessions, reports, went_well_summary, improve_summary
    )

    st.divider()
    st.markdown(md_report)

    st.divider()
    st.download_button(
        label="⬇️ Download Markdown Report",
        data=md_report,
        file_name=f"player_report_{email.replace('@','_at_')}.md",
        mime="text/markdown",
        use_container_width=True,
    )