"""
malloc() frontend: chat + job application tracker.

User -> Streamlit -> FastAPI -> LLM -> Response  (Chat tab)
User -> Streamlit -> FastAPI -> SQLite            (Job Tracker tab)

Run the FastAPI backend first (`uvicorn app.main:app --reload`), then:

    streamlit run streamlit_app.py
"""
import os
import uuid
from datetime import datetime

import requests
import streamlit as st

# Priority: Streamlit secrets -> Environment variable -> Default localhost
def get_api_url() -> str:
    if "api_url" in st.session_state and st.session_state.api_url:
        return st.session_state.api_url.rstrip("/")
    try:
        if hasattr(st, "secrets") and "API_URL" in st.secrets:
            return str(st.secrets["API_URL"]).rstrip("/")
    except Exception:
        pass
    return os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

API_URL = get_api_url()

st.set_page_config(page_title="malloc()", page_icon=":brain:", layout="wide")
st.title("malloc()")
st.caption("memory allocated for you")

if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-{uuid.uuid4().hex[:8]}"
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "user"|"assistant", "content": str}]

# Helper to check backend health
def check_backend_health(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

with st.sidebar:
    st.subheader("Session")
    st.text(f"user: {st.session_state.user_id}")
    st.text(f"conversation: {st.session_state.conversation_id or '(new)'}")
    if st.button("New conversation"):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.subheader("Backend Status")
    is_healthy = check_backend_health(API_URL)
    if is_healthy:
        st.success(f"Connected to API (`{API_URL}`)")
    else:
        st.error(f"Backend unreachable at `{API_URL}`")
        with st.expander("Configure API URL"):
            custom_url = st.text_input("Custom Backend URL", value=API_URL)
            if st.button("Apply URL"):
                st.session_state.api_url = custom_url
                st.rerun()

chat_tab, insights_tab, jobs_tab = st.tabs(["💬 Chat", "🏢 Company Insights", "📋 Job Tracker"])

# ---------------------------------------------------------------- Chat tab
with chat_tab:
    st.caption("Plain chat with memory extraction running in the background")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Say something to malloc()")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("Thinking...")
            try:
                resp = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "user_external_id": st.session_state.user_id,
                        "conversation_id": st.session_state.conversation_id,
                        "message": prompt,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                st.session_state.conversation_id = data["conversation_id"]
                reply = data["reply"]
            except requests.exceptions.ConnectionError:
                reply = "Can't reach the malloc() backend. Is `uvicorn app.main:app --reload` running?"
            except requests.exceptions.HTTPError as exc:
                reply = f"Backend error: {exc.response.status_code} — {exc.response.text}"

            placeholder.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

# ------------------------------------------------------------ Job Tracker tab
# ---------------------------------------------------------------- Company Insights tab
with insights_tab:
    st.subheader("🏢 Company Insights Engine")
    st.caption("Zero-Shot Size Classification (BART) + 62-Industry Tagging + Culture Sentiment Scoring (SST-2)")

    c1, c2 = st.columns(2)
    insight_comp = c1.text_input("Company Name", value="Stripe", key="st_insight_comp")
    insight_role = c2.text_input("Target Role (Optional)", value="Staff Backend Engineer", key="st_insight_role")
    insight_about = st.text_area("About / Company Description / Job Post Snippets", value="Stripe is a financial infrastructure platform for businesses. Founded in 2010 with over 7,000 employees globally.", rows=3, key="st_insight_about")

    if st.button("Generate Company Intelligence", key="st_btn_run_insights", type="primary"):
        with st.spinner("Synthesizing company intelligence via transformers pipelines..."):
            try:
                resp = requests.post(
                    f"{API_URL}/insights/analyze",
                    json={
                        "company": insight_comp,
                        "role_title": insight_role or None,
                        "about_text": insight_about or None,
                        "user_external_id": st.session_state.user_id
                    },
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"Generated intelligence profile for **{data['company']}**")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("### 🏷️ Classification & Size")
                        cls = data.get("classification", {})
                        st.metric("Company Size", cls.get("label", "N/A"), f"Confidence: {int((cls.get('confidence', 0))*100)}%")
                        if cls.get("industry"):
                            st.info(f"**Industry:** {cls.get('industry')} ({int((cls.get('industry_confidence', 0))*100)}% conf)")
                        if cls.get("disagreement_flag"):
                            st.warning("⚠️ **Signal Disagreement:** Classifier prediction conflicts with numeric facts.")

                        facts = cls.get("facts", {})
                        st.write(f"- **Estimated Employees:** {facts.get('employee_count_estimate', 'unknown')}")
                        st.write(f"- **Founded Year:** {facts.get('founded_year', 'unknown')}")

                    with col_b:
                        st.markdown("### 💬 Culture & Sentiment")
                        cult = data.get("culture_synthesis", {})
                        sent = cult.get("sentiment_breakdown", {})
                        st.metric("Sentiment Score", f"{sent.get('positive_count', 0)} Pos / {sent.get('negative_count', 0)} Neg", f"{int((sent.get('positive_count', 0) / (sent.get('total', 1) or 1))*100)}% Positive")

                        st.markdown("**Praised Aspects:**")
                        for p in cult.get("praised_aspects", []):
                            st.markdown(f"- {p}")
                        st.markdown("**Criticized Aspects:**")
                        for c in cult.get("criticized_aspects", []):
                            st.markdown(f"- {c}")

                    st.markdown("### 🎯 Interview Preparation Blueprint")
                    inter = data.get("interview_insights", {})
                    i1, i2 = st.columns(2)
                    with i1:
                        st.markdown("**Key Focus Areas:**")
                        for f in inter.get("focus_areas", []):
                            st.markdown(f"- `{f}`")
                    with i2:
                        st.markdown("**Preparation Tips:**")
                        for t in inter.get("prep_tips", []):
                            st.markdown(f"- {t}")
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"Failed to connect: {e}")

# ---------------------------------------------------------------- Job Tracker tab
with jobs_tab:
    user_id = st.session_state.user_id

    # Reminder banner - what's overdue for follow-up
    try:
        due_resp = requests.get(f"{API_URL}/jobs/{user_id}/due-followups", timeout=10)
        due_resp.raise_for_status()
        due = due_resp.json()
    except requests.exceptions.RequestException:
        due = []

    if due:
        st.warning(
            f"**{len(due)} application(s) due for follow-up:** "
            + ", ".join(f"{j['company']} ({j['role_title']})" for j in due)
        )

    st.subheader("Log a new application")
    with st.form("new_job_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        company = col1.text_input("Company")
        role_title = col2.text_input("Role")
        col3, col4 = st.columns(2)
        job_url = col3.text_input("Job posting URL (optional)")
        follow_up_days = col4.number_input("Follow up after (days)", min_value=1, max_value=90, value=7)
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Add application")

        if submitted:
            if not company or not role_title:
                st.error("Company and Role are required.")
            else:
                try:
                    resp = requests.post(
                        f"{API_URL}/jobs",
                        json={
                            "user_external_id": user_id,
                            "company": company,
                            "role_title": role_title,
                            "job_url": job_url or None,
                            "notes": notes or None,
                            "follow_up_days": int(follow_up_days),
                        },
                        timeout=10,
                    )
                    resp.raise_for_status()
                    st.success(f"Added {company} — {role_title}")
                    st.rerun()
                except requests.exceptions.RequestException as exc:
                    st.error(f"Failed to add application: {exc}")

    st.subheader("Your applications")
    try:
        list_resp = requests.get(f"{API_URL}/jobs/{user_id}", timeout=10)
        list_resp.raise_for_status()
        jobs = list_resp.json()
    except requests.exceptions.RequestException as exc:
        jobs = []
        st.error(f"Couldn't load applications: {exc}")

    if not jobs:
        st.caption("No applications logged yet.")

    STATUS_OPTIONS = ["applied", "interview", "offer", "rejected", "no_response"]

    for job in jobs:
        with st.expander(f"{job['company']} — {job['role_title']}  ·  {job['status']}"):
            c1, c2, c3 = st.columns([2, 2, 1])
            new_status = c1.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(job["status"]) if job["status"] in STATUS_OPTIONS else 0,
                key=f"status_{job['id']}",
            )
            c2.text(f"Applied: {job['applied_date'][:10]}")
            c2.text(f"Follow-up: {(job['follow_up_date'] or '')[:10]}")
            if job.get("job_url"):
                c1.markdown(f"[Job posting]({job['job_url']})")
            if job.get("notes"):
                st.caption(job["notes"])

            if c3.button("Update", key=f"update_{job['id']}"):
                try:
                    requests.patch(
                        f"{API_URL}/jobs/{job['id']}",
                        json={"status": new_status},
                        timeout=10,
                    ).raise_for_status()
                    st.rerun()
                except requests.exceptions.RequestException as exc:
                    st.error(f"Update failed: {exc}")

            if c3.button("Delete", key=f"delete_{job['id']}"):
                try:
                    requests.delete(f"{API_URL}/jobs/{job['id']}", timeout=10).raise_for_status()
                    st.rerun()
                except requests.exceptions.RequestException as exc:
                    st.error(f"Delete failed: {exc}")
