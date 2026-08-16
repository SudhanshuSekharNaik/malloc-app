"""
Hugging Face Spaces Native Multi-Feature App for malloc()
ZeroGPU-accelerated Career Intelligence & Long-Term Memory OS.
"""
import os
import spaces
import gradio as gr

from app.llm import call_llm
from app.services.ats_checker import calculate_ats_audit
from app.services.job_matcher import analyze_resume_vs_job
from app.services.resume_editor import generate_resume_edits
from app.services.company_insights import get_company_insights
from app.services.email_outreach import parse_informal_jd_regex, draft_application_email

# --- ZeroGPU Handlers ---
@spaces.GPU
def chat_response(message, history):
    if not message.strip():
        return ""
    try:
        messages = []
        for user_msg, bot_msg in (history or []):
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if bot_msg:
                messages.append({"role": "assistant", "content": bot_msg})
        messages.append({"role": "user", "content": message})
        
        response = call_llm(
            messages,
            system="You are malloc(), an AI Career Intelligence Assistant with long-term memory. Provide sharp, concise, actionable advice."
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"

@spaces.GPU
def match_resume(resume_text, jd_text):
    if not resume_text or not jd_text:
        return "Please provide both Resume and Job Description text.", ""
    try:
        match_res = analyze_resume_vs_job(resume_text=resume_text, job_description=jd_text)
        edits_res = generate_resume_edits(resume_text=resume_text, job_description=jd_text)
        
        summary = f"### Overall Match Score: {match_res.match_score}%\n\n"
        summary += f"**Verdict**: {match_res.verdict}\n\n"
        summary += f"**Matched Skills**: {', '.join(match_res.matched_skills)}\n\n"
        summary += f"**Missing / Gaps**: {', '.join(match_res.missing_skills)}\n\n"
        summary += f"**Summary**: {match_res.summary}"
        
        edits = "### Actionable Suggested Edits:\n"
        for item in edits_res.suggestions:
            edits += f"- **Original**: {item.original_text}\n  - **Suggested Edit**: {item.suggested_rewrite}\n  - **Rationale**: {item.rationale}\n\n"
            
        return summary, edits
    except Exception as e:
        return f"Error analyzing: {str(e)}", ""

@spaces.GPU
def check_ats(resume_text):
    if not resume_text:
        return "Please paste resume text to audit."
    try:
        res = calculate_ats_audit(resume_text=resume_text, file_name="resume.txt")
        output = f"### ATS Parseability Score: {res.overall_score}/100\n\n"
        output += f"- **Formatting & Layout**: {res.breakdown.formatting_and_layout}/100\n"
        output += f"- **Section Completeness**: {res.breakdown.section_completeness}/100\n"
        output += f"- **Entity Richness**: {res.breakdown.entity_richness}/100\n"
        output += f"- **Contact Info**: {res.breakdown.contact_info}/100\n\n"
        output += f"**Audit Recommendations**:\n"
        for item in res.audit_items:
            icon = "✅" if item.status == "pass" else "⚠️" if item.status == "warning" else "❌"
            output += f"- {icon} **{item.category.upper()}**: {item.message}\n"
        return output
    except Exception as e:
        return f"Error: {str(e)}"

@spaces.GPU
def company_insights(company_name, website):
    if not company_name:
        return "Please enter a company name."
    try:
        res = get_company_insights(company_name=company_name, company_url=website)
        output = f"### Company Insights for {res.company_name.upper()}\n\n"
        output += f"- **Classification**: {res.classification.predicted_category} ({res.classification.confidence_score}% confidence)\n"
        output += f"- **Industry**: {res.industry.primary_industry}\n"
        output += f"- **Culture Sentiment**: {res.culture.sentiment_label} (Score: {res.culture.positive_sentiment_score}% Positive)\n\n"
        output += f"**Culture Summary**:\n{res.culture.summary}\n\n"
        output += f"**Interview Focus Areas**:\n"
        for topic in res.interview_prep.focus_areas:
            output += f"- **{topic.topic}**: {topic.description}\n"
        return output
    except Exception as e:
        return f"Error: {str(e)}"

@spaces.GPU
def email_outreach(jd_text, applicant_name, applicant_skills):
    if not jd_text:
        return "Please paste the job posting text.", ""
    try:
        parsed_jd = parse_informal_jd_regex(jd_text)
        selected_role = (parsed_jd.get("open_positions") or ["Candidate"])[0]
        draft_res = draft_application_email(
            resume_text=applicant_skills or "Software Engineering background",
            selected_role=selected_role,
            parsed_jd=parsed_jd,
            applicant_name=applicant_name or "Applicant"
        )
        summary = f"**Company**: {parsed_jd.get('company_name') or 'Hiring Team'}\n"
        summary += f"**Role**: {selected_role}\n"
        summary += f"**Recipient HR Email**: {parsed_jd.get('hr_email') or 'Not specified in text'}\n"
        summary += f"**Subject Line**: {draft_res.get('subject', '')}"
        return summary, draft_res.get("body", "")
    except Exception as e:
        return f"Error: {str(e)}", ""

# --- Custom Theme & Multi-Tab Layout ---
theme = gr.themes.Monochrome(
    primary_hue="fuchsia",
    secondary_hue="cyan",
    neutral_hue="slate"
)

with gr.Blocks(title="MALLOC() [CORE_OS]", theme=theme) as demo:
    gr.Markdown("# // MALLOC() [AI CAREER INTELLIGENCE OS]\n*ZeroGPU Accelerated • Memory Vault • Resume Matcher • ATS Auditor • Email Outreach*")
    
    with gr.Tabs():
        with gr.TabItem("💬 AI Assistant"):
            gr.ChatInterface(fn=chat_response, title="Terminal Session")
            
        with gr.TabItem("📄 Resume Matcher & Suggested Edits"):
            with gr.Row():
                r_text = gr.Textbox(label="Your Resume Content", lines=8, placeholder="Paste resume plain text...")
                j_text = gr.Textbox(label="Target Job Description", lines=8, placeholder="Paste JD plain text...")
            match_btn = gr.Button("⚡ Match & Generate Edits", variant="primary")
            with gr.Row():
                out_summary = gr.Markdown(label="Match Analysis")
                out_edits = gr.Markdown(label="Suggested Rewrites")
            match_btn.click(fn=match_resume, inputs=[r_text, j_text], outputs=[out_summary, out_edits])

        with gr.TabItem("🛡️ ATS Parseability Checker"):
            ats_input = gr.Textbox(label="Resume Text", lines=10, placeholder="Paste resume to audit...")
            ats_btn = gr.Button("🔍 Audit ATS Structure", variant="primary")
            ats_out = gr.Markdown()
            ats_btn.click(fn=check_ats, inputs=[ats_input], outputs=[ats_out])

        with gr.TabItem("🏢 Company Insights"):
            with gr.Row():
                comp_name = gr.Textbox(label="Company Name", placeholder="e.g. TCS, Stripe, Google")
                comp_web = gr.Textbox(label="Website (Optional)", placeholder="https://...")
            comp_btn = gr.Button("📊 Analyze Company & Culture", variant="primary")
            comp_out = gr.Markdown()
            comp_btn.click(fn=company_insights, inputs=[comp_name, comp_web], outputs=[comp_out])

        with gr.TabItem("📧 Apply via Email Outreach"):
            with gr.Row():
                raw_jd = gr.Textbox(label="Informal / WhatsApp / LinkedIn Job Post", lines=6, placeholder="🏢 Company: ...\n💼 Role: ...\n📧 Apply: ...")
                with gr.Column():
                    app_name = gr.Textbox(label="Your Name", placeholder="Your Full Name")
                    app_skills = gr.Textbox(label="Top Key Skills / Experience Snippet", placeholder="e.g. Python, FastAPI, React, 2 years experience")
            email_btn = gr.Button("✉️ Parse & Generate Personalized Outreach", variant="primary")
            with gr.Row():
                email_fields = gr.Markdown()
                email_draft = gr.Textbox(label="Generated Email Draft", lines=8)
            email_btn.click(fn=email_outreach, inputs=[raw_jd, app_name, app_skills], outputs=[email_fields, email_draft])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)











