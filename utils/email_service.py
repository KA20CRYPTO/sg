
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

def send_email(recipient_email, subject, body, html_body=None):
    """
    Sends an email using Gmail SMTP.
    Reads GMAIL_ADDRESS and GMAIL_APP_PASSWORD from environment/secrets.
    """
    # Try getting from env vars first, then Streamlit secrets
    gmail_address = os.environ.get("GMAIL_ADDRESS") or st.secrets.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD") or st.secrets.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_app_password:
        print("❌ Email configuration missing.")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = gmail_address
    msg['To'] = recipient_email
    
    # Add List-Unsubscribe header for better deliverability
    msg.add_header('List-Unsubscribe', f'<mailto:{gmail_address}?subject=unsubscribe>')

    # Attach plain text
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach HTML if provided
    if html_body:
        msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_address, gmail_app_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")
        return False

def generate_instant_match_email_html(candidate_name, job_title, company_name, location, score, job_id, base_url="https://candidate-screeneerpro.streamlit.app"):
    """
    Generates HTML content for an Instant Match notification.
    """
    job_link = f"{base_url}/public_job_board?job_id={job_id}"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
            .header h2 {{ margin: 0; }}
            .content {{ padding: 20px; background-color: #ffffff; }}
            .job-card {{ background-color: #f8f9fa; border-left: 5px solid #28a745; padding: 15px; margin: 20px 0; border-radius: 4px; }}
            .match-badge {{ background-color: #28a745; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold; font-size: 0.9em; }}
            .btn {{ display: inline-block; background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; margin-top: 10px; }}
            .footer {{ background-color: #f1f1f1; padding: 15px; text-align: center; font-size: 0.8em; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>New Job Match! 🎯</h2>
            </div>
            <div class="content">
                <p>Hi <strong>{candidate_name}</strong>,</p>
                <p>We found a new job that matches your profile perfectly!</p>
                
                <div class="job-card">
                    <h3 style="margin-top:0;">{job_title}</h3>
                    <p style="margin: 5px 0;"><strong>{company_name}</strong> • {location}</p>
                    <p style="margin-top: 10px;"><span class="match-badge">{score}% Match Score</span></p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{job_link}" class="btn">View Job & Apply Now</a>
                </p>
                
                <p>Good luck!</p>
                <p>The ScreenerPro Team</p>
            </div>
            <div class="footer">
                <p>You received this email because you opted into job alerts on ScreenerPro.</p>
                <p><a href="{base_url}" style="color: #666;">Manage Preferences</a></p>
            </div>
        </div>
    </body>
    </html>
    """

def generate_plain_text_match_email(candidate_name, job_title, company_name, score, job_id, base_url="https://candidate-screeneerpro.streamlit.app"):
    job_link = f"{base_url}/public_job_board?job_id={job_id}"
    return f"""
    Hi {candidate_name},

    We found a new job matching your profile!

    Job: {job_title}
    Company: {company_name}
    Match Score: {score}%

    Apply here: {job_link}

    Good luck,
    The ScreenerPro Team
    """
