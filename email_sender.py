# email_sender.py
import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from time import sleep
# email_sender.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_welcome_email(to_email, username, company_name):
    """
    Sends a beautiful welcome email to a newly registered user.
    Works reliably in Gmail, Outlook, and other major email clients.
    """
    # --- SMTP Configuration ---
    SMTP_SERVER = "smtp.gmail.com"  # or your SMTP server
    SMTP_PORT = 587
    SMTP_USER = "screenerpro.ai@gmail.com"  # your Gmail
    SMTP_PASSWORD = "udwilifenbdvkgdt"  # Gmail App Password

    # --- Create Message ---
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Welcome to ScreenerPro! 🚀"
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    # --- HTML Content (email-safe) ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
      <body style="margin:0; padding:0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:#f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f4f4f4">
          <tr>
            <td align="center">
              <table width="650" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="border-radius:15px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <tr>
                  <td align="center" bgcolor="#3b82f6" style="padding:40px;">
                    <img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s578/logo.png" alt="ScreenerPro Logo" width="100" style="border-radius:50%; border:3px solid rgba(255,255,255,0.5); margin-bottom:15px;">
                    <h1 style="color:#ffffff; font-size:28px; margin:0;">Welcome to ScreenerPro, {username}!</h1>
                  </td>
                </tr>

                <!-- Content -->
                <tr>
                  <td style="padding:30px; color:#333333;">
                    <h2 style="color:#3b82f6;">Hello {username},</h2>
                    <p>We’re excited to have you and your company <strong>{company_name}</strong> on board! 🎉</p>
                    <p>ScreenerPro helps you streamline hiring with:</p>

                    <!-- Features -->
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:20px;">
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>🤖 AI-Powered Resume Screening:</strong> Instantly score and analyze resumes against your job descriptions.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>⚙️ Customizable Screening Criteria:</strong> Adjust minimum score, experience, and CGPA requirements.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>📊 Comprehensive Candidate Analytics:</strong> Get AI match scores, skill matches, and AI-generated suggestions.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>🗂️ Interactive Results Table:</strong> Filter, sort, and manually shortlist candidates in a dynamic table.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>📈 Visual Candidate Comparison:</strong> See candidates rank with intuitive charts and score tags.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>📄 Detailed Resume Highlights:</strong> View education, top skills, latest job, and availability quickly.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>📬 Automated Email Templates:</strong> Generate templates for shortlisting, rejection, or interview invites.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>🏆 ScreenerPro Certificates:</strong> Award official AI-verified certificates to qualified candidates.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>💾 Downloadable Reports:</strong> Export applicant data to CSV or detailed PDFs.</td></tr>
                      <tr><td style="padding:10px; border-radius:10px; background-color:#f0f4ff; margin-bottom:10px;"><strong>🖥️ User-Friendly Interface:</strong> Clean dashboard, no technical training required.</td></tr>
                    </table>

                    <!-- Button -->
                    <p style="text-align:center; margin-top:30px;">
                      <a href="https://screeneerpro.streamlit.app/" style="display:inline-block; padding:15px 35px; background-color:#3b82f6; color:#ffffff; text-decoration:none; border-radius:50px; font-weight:bold;">Go to Dashboard 🚀</a>
                    </p>

                    <p style="margin-top:25px;">For questions or assistance, our support team is always here.</p>
                  </td>
                </tr>

                <!-- Footer -->
                <tr>
                  <td bgcolor="#f7f7f7" style="padding:30px; text-align:center; font-size:12px; color:#555555;">
                    <p>Cheers,<br>The ScreenerPro Team</p>
                    <p><a href="https://screeneerpro.streamlit.app/" style="color:#3b82f6;">Visit our website</a> | <a href="mailto:screenerpro.ai@gmail.com" style="color:#3b82f6;">Contact Support</a></p>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    # Attach HTML content
    msg.attach(MIMEText(html_content, "html"))

    # --- Send Email ---
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


    # Attach HTML content
    msg.attach(MIMEText(html_content, "html"))

    # --- Send Email ---
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"✅ Welcome email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
def send_email_to_candidate():
    st.markdown("## 📤 Email Candidates")
    st.info("Send emails only to candidates shortlisted in the screener (auto + manual).")

    # --- Check if shortlist exists ---
    if 'shortlisted_candidates' not in st.session_state or st.session_state['shortlisted_candidates'].empty:
        st.warning("⚠️ No shortlisted candidates found. Please run shortlisting in the Resume Screener first.")
        return

    shortlisted_candidates = st.session_state['shortlisted_candidates']
    st.success(f"✅ Found {len(shortlisted_candidates)} shortlisted candidate(s).")
    st.dataframe(
        shortlisted_candidates[['Candidate Name', 'Email', 'Score (%)', 'AI Suggestion']],
        use_container_width=True
    )

    # --- Company Name ---
    company_name = st.session_state.get('user_company', 'ABC Corp')
    st.markdown(f"**Company Name:** {company_name}")

    # --- Email Configuration Expander ---
    with st.expander("📧 Email Configuration", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            sender_email = st.text_input("Your Email (Sender)")
            sender_password = st.text_input("Your Email Password (App Password)", type="password")
            smtp_server = st.text_input("SMTP Server", "smtp.gmail.com")
            smtp_port = int(st.number_input("SMTP Port", 587))
        with col2:
            job_description = st.text_area(
                "Job Description / Title",
                placeholder="Enter the job description used for screening resumes",
                height=100
            )

    # --- Candidate Selection ---
    candidate_options = shortlisted_candidates['Candidate Name'].tolist()
    selected_candidates = st.multiselect(
        "Select candidates to send email",
        options=candidate_options,
        default=candidate_options
    )

    # --- Email Content Expander ---
    with st.expander("✍️ Email Content", expanded=True):
        email_subject = st.text_input(
            "Email Subject",
            f"Job Application Update - Your Application to {job_description or 'the position'}"
        )

        email_body_template = """
<p>Dear <strong>{candidate_name}</strong>,</p>

<p>Thank you for your application for the position of <strong>{job_description}</strong> at <strong>{company_name}</strong>.</p>

<p>Based on our initial assessment:</p>
<ul>
<li><strong>Score:</strong> <span style="color:{score_color}">{score_percent:.1f}%</span></li>
<li><strong>Years of Experience:</strong> {years_experience:.1f}</li>
<li><strong>AI Suggestion:</strong> {ai_suggestion}</li>
</ul>

<p>We will be in touch shortly regarding the next steps in our hiring process.</p>

<p>Best regards,<br>
The {company_name} Hiring Team</p>
"""

        email_body = st.text_area(
            "Email Body (HTML supported, use {candidate_name}, {score_percent}, {years_experience}, {ai_suggestion}, {job_description}, {company_name})",
            value=email_body_template,
            height=400
        )

    # --- Live Preview Expander ---
    with st.expander("👀 Live Email Preview", expanded=True):
        for _, row in shortlisted_candidates.iterrows():
            if row['Candidate Name'] not in selected_candidates:
                continue

            candidate_name = row['Candidate Name']
            score_percent = row['Score (%)']
            years_experience = row['Years Experience']
            ai_suggestion = row['AI Suggestion']

            # Color code score
            score_color = "green" if score_percent > 80 else "orange" if score_percent > 50 else "red"

            # Replace placeholders
            preview_html = email_body.format(
                candidate_name=candidate_name,
                score_percent=score_percent,
                years_experience=years_experience,
                ai_suggestion=ai_suggestion,
                job_description=job_description or "the position",
                company_name=company_name,
                score_color=score_color
            )

            # Wrap in scrollable div
            wrapped_html = f"""
<div style="border:1px solid #ccc; padding:10px; border-radius:5px; max-height:300px; overflow-y:auto; font-family:Arial, sans-serif; line-height:1.5; color:#333;">
{preview_html}
</div>
"""
            st.markdown(f"**Preview for {candidate_name}:**", unsafe_allow_html=True)
            st.markdown(wrapped_html, unsafe_allow_html=True)
            st.markdown("---")

    # --- Send Emails ---
    if st.button("🚀 Send Emails to Selected Candidates"):
        if not sender_email or not sender_password:
            st.error("⚠️ Please enter your sender email and password.")
            return

        if not selected_candidates:
            st.error("⚠️ Please select at least one candidate to send email.")
            return

        progress_bar = st.progress(0)
        sent_list = []

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)

                for i, (_, row) in enumerate(shortlisted_candidates.iterrows()):
                    if row['Candidate Name'] not in selected_candidates:
                        continue

                    candidate_name = row['Candidate Name']
                    candidate_email = row['Email']
                    score_percent = row['Score (%)']
                    years_experience = row['Years Experience']
                    ai_suggestion = row['AI Suggestion']

                    score_color = "green" if score_percent > 80 else "orange" if score_percent > 50 else "red"

                    formatted_body = email_body.format(
                        candidate_name=candidate_name,
                        score_percent=score_percent,
                        years_experience=years_experience,
                        ai_suggestion=ai_suggestion,
                        job_description=job_description or "the position",
                        company_name=company_name,
                        score_color=score_color
                    )

                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    msg['To'] = candidate_email
                    msg['Subject'] = email_subject
                    msg.attach(MIMEText(formatted_body, 'html'))

                    server.send_message(msg)
                    sent_list.append(f"{candidate_name} ({candidate_email})")

                    # Log in session_state
                    if 'sent_emails_log' not in st.session_state:
                        st.session_state['sent_emails_log'] = []
                    st.session_state['sent_emails_log'].append({
                        "timestamp": pd.Timestamp.now().isoformat(),
                        "candidate_name": candidate_name,
                        "candidate_email": candidate_email,
                        "subject": email_subject,
                        "body_snippet": formatted_body[:100] + "..."
                    })

                    # Update progress
                    progress_bar.progress((i + 1) / len(selected_candidates))
                    sleep(0.1)

            st.success(f"✅ Emails sent to: {', '.join(sent_list)}")
            progress_bar.empty()

        except smtplib.SMTPAuthenticationError:
            st.error("❌ Email sending failed: Invalid email or app password.")
        except smtplib.SMTPConnectError:
            st.error(f"❌ Could not connect to SMTP server {smtp_server}:{smtp_port}")
        except Exception as e:
            st.error(f"❌ Unexpected error during email sending: {e}")






