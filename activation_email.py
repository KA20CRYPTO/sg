import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_activation_email(to_email, username, activation_link):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "screenerpro.ai@gmail.com"
    SMTP_PASSWORD = "udwilifenbdvkgdt"  # Gmail App Password

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Activate Your ScreenerPro Account"
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>

<body style="margin:0; padding:0;
background:linear-gradient(180deg,#e6efff,#f7faff);
font-family:'Segoe UI', Arial, sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="padding:50px 0;">
<tr>
<td align="center">

<table width="650" cellpadding="0" cellspacing="0"
style="background:linear-gradient(135deg,#2563eb,#38bdf8,#6366f1);
border-radius:24px; padding:2px;">
<tr><td>

<table width="100%" cellpadding="0" cellspacing="0"
style="background:#ffffff; border-radius:22px; overflow:hidden;
box-shadow:0 25px 60px rgba(37,99,235,0.28);">

<tr>
<td style="padding:36px 44px;
background:linear-gradient(135deg,#2563eb,#38bdf8);">
<table width="100%">
<tr>
<td align="left">
<img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s320/logo.png"
width="92" alt="ScreenerPro Logo" style="display:block;">
</td>
<td align="right" style="color:#e0f2fe; font-size:14px;">
AI-Driven Talent Intelligence
</td>
</tr>
</table>
</td>
</tr>

<tr>
<td style="background:linear-gradient(90deg,#eff6ff,#f8fbff);
padding:22px 44px;">
<p style="margin:0; font-size:15px; color:#1e3a8a; font-weight:600;">
Smarter hiring starts here
</p>
</td>
</tr>

<tr>
<td style="padding:38px 46px 28px;">
<h2 style="margin:0; font-size:27px; color:#0f172a; font-weight:700;">
Welcome to ScreenerPro, {username}
</h2>

<p style="margin-top:16px; font-size:16px; color:#334155; line-height:1.75;">
Your account has been created successfully.
Activate your account to begin your
<strong>14-day free pilot</strong> and experience
intelligent, fast, and data-driven candidate screening.
</p>
</td>
</tr>

<tr>
<td align="center" style="padding:10px 46px 38px;">
<a href="{activation_link}"
style="display:inline-block;
padding:18px 50px;
background:linear-gradient(135deg,#2563eb,#6366f1);
color:#ffffff;
font-size:17px;
font-weight:700;
text-decoration:none;
border-radius:999px;
box-shadow:0 14px 34px rgba(37,99,235,0.55);">
Activate Your Account
</a>
</td>
</tr>

<tr>
<td style="padding:0 42px 38px;">
<table width="100%">
<tr>
<td width="33%" style="padding:14px;">
<div style="background:#f0f7ff; border-radius:16px; padding:20px;">
<p style="margin:0; font-size:14px; font-weight:700; color:#1e40af;">
AI Resume Scoring
</p>
<p style="margin-top:8px; font-size:13px; color:#475569;">
Accurate candidate evaluation
</p>
</div>
</td>

<td width="33%" style="padding:14px;">
<div style="background:#ecfeff; border-radius:16px; padding:20px;">
<p style="margin:0; font-size:14px; font-weight:700; color:#155e75;">
Advanced Analytics
</p>
<p style="margin-top:8px; font-size:13px; color:#475569;">
Deep hiring insights
</p>
</div>
</td>

<td width="33%" style="padding:14px;">
<div style="background:#eef2ff; border-radius:16px; padding:20px;">
<p style="margin:0; font-size:14px; font-weight:700; color:#3730a3;">
Instant Shortlisting
</p>
<p style="margin-top:8px; font-size:13px; color:#475569;">
Save hours of effort
</p>
</div>
</td>
</tr>
</table>
</td>
</tr>

<tr>
<td style="padding:0 46px 30px;">
<p style="font-size:14px; color:#475569;">
If the button does not work, copy and paste this link:
</p>
<p style="word-break:break-all; font-size:14px; color:#2563eb;">
{activation_link}
</p>
</td>
</tr>

<tr>
<td style="background:#eef3ff; padding:24px 44px; text-align:center;">
<p style="margin:0; font-size:13px; color:#475569;">
© 2026 ScreenerPro. All rights reserved.
</p>
<p style="margin-top:6px; font-size:13px; color:#475569;">
Support: <strong>screenerpro.ai@gmail.com</strong>
</p>
</td>
</tr>

</table>
</td></tr></table>

</td>
</tr>
</table>

</body>
</html>
"""

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print("❌ Email Send Error:", e)
        return False
