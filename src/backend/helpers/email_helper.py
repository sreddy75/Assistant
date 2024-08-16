

def get_email_html_template(header, message, button_text, button_url):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{header}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4CAF50;
                color: white;
                text-align: center;
                padding: 20px;
                font-size: 24px;
            }}
            .content {{
                background-color: #f9f9f9;
                border: 1px solid #dddddd;
                padding: 20px;
                margin-top: 20px;
            }}
            .button {{
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                font-size: 12px;
                color: #888888;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{header}</h1>
        </div>
        <div class="content">
            <p>{message}</p>
            <a href="{button_url}" class="button">{button_text}</a>
        </div>
        <div class="footer">
            <p>This is an automated message from Compare the Meerkat. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

def send_email(to_email: str, subject: str, html_content: str):
    try:
        # Initialize the SMTP object with user and password
        yag = yagmail.SMTP(user=GMAIL_USER, password=GMAIL_PASSWORD)
        yag.send(
            to=to_email,
            subject=subject,
            contents=[html_content]
        )
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise
    
def send_verification_email(email: str, token: str):
    subject = "Verify Your Email for Compare the Meerkat"
    verification_url = f"{FRONTEND_URL}?token={token}&verify=true"
    html_content = get_email_html_template(
        header="Email Verification",
        message="Thank you for registering with Compare the Meerkat! Please click the button below to verify your email address and activate your account.",
        button_text="Verify Email",
        button_url=verification_url
    )
    send_email(email, subject, html_content)
    
def send_password_reset_email(email: str, token: str):
    subject = "Reset Your Compare the Meerkat Password"
    reset_url = f"{FRONTEND_URL}?token={token}&reset=true"
    html_content = get_email_html_template(
        header="Password Reset",
        message="You have requested to reset your password for Compare the Meerkat. Click the button below to set a new password. If you didn't request this, please ignore this email.",
        button_text="Reset Password",
        button_url=reset_url
    )
    send_email(email, subject, html_content)
    