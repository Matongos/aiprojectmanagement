import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import requests
from pathlib import Path
import jinja2
from config import settings
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import aiosmtplib

# Set up logging
logger = logging.getLogger(__name__)

# Template directories
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "emails"
# Create template directory if it doesn't exist
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# Set up jinja2 environment
template_loader = jinja2.FileSystemLoader(searchpath=str(TEMPLATE_DIR))
template_env = jinja2.Environment(loader=template_loader)

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS
)

# Initialize FastMail
fastmail = FastMail(conf)

class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.smtp_server = settings.MAIL_SERVER
        self.smtp_port = settings.MAIL_PORT
        self.smtp_username = settings.MAIL_USERNAME
        self.smtp_password = settings.MAIL_PASSWORD
        self.from_email = settings.MAIL_FROM

    @classmethod
    def send_email(
        cls,
        email_to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Send an email using the configured email service.
        
        Args:
            email_to: Email recipient(s), can be a string of comma-separated emails
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (fallback for HTML)
            cc: List of CC recipients
            attachments: List of attachment dictionaries with keys:
                        - content: The file content
                        - filename: The filename
                        - content_type: The content type (e.g., "application/pdf")
        
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        if not settings.EMAILS_ENABLED:
            logger.info("Email sending is disabled")
            return False
            
        # Choose email service based on configuration
        if settings.EMAIL_SERVICE.lower() == "resend":
            return cls._send_with_resend(email_to, subject, html_content, text_content, cc, attachments)
        else:
            return cls._send_with_smtp(email_to, subject, html_content, text_content, cc, attachments)
    
    @classmethod
    def _send_with_smtp(
        cls,
        email_to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send an email using SMTP."""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
            message["To"] = email_to
            
            if cc:
                message["Cc"] = ", ".join(cc)
                
            # Add plain text version
            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)
                
            # Add HTML version
            part2 = MIMEText(html_content, "html")
            message.attach(part2)
            
            # Connect to server and send
            with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                if settings.MAIL_STARTTLS:
                    server.starttls()
                if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                    server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                    
                recipients = [email_to]
                if cc:
                    recipients.extend(cc)
                
                server.sendmail(
                    settings.MAIL_FROM,
                    recipients,
                    message.as_string()
                )
                
            logger.info(f"Email sent successfully to {email_to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    @classmethod
    def _send_with_resend(
        cls,
        email_to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send an email using the Resend API."""
        if not settings.RESEND_API_KEY:
            logger.error("Resend API key not configured")
            return False
            
        try:
            headers = {
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
                "to": [email_to] if isinstance(email_to, str) else email_to,
                "subject": subject,
                "html": html_content,
            }
            
            if text_content:
                payload["text"] = text_content
                
            if cc:
                payload["cc"] = cc
                
            response = requests.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"Email sent successfully to {email_to} via Resend")
                return True
            else:
                logger.error(f"Failed to send email via Resend: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {str(e)}")
            return False
    
    @classmethod
    def send_template_email(
        cls,
        email_to: str,
        subject: str,
        template_name: str,
        template_vars: Dict[str, Any],
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Send an email using a template.
        
        Args:
            email_to: Email recipient(s)
            subject: Email subject
            template_name: Name of the template file (without extension)
            template_vars: Variables to pass to the template
            cc: List of CC recipients
            attachments: List of attachment dictionaries
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        try:
            # Load the template
            template = template_env.get_template(f"{template_name}.html")
            html_content = template.render(**template_vars)
            
            # Generate plain text version
            text_content = cls._html_to_text(html_content)
            
            # Send the email
            return cls.send_email(
                email_to=email_to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                cc=cc,
                attachments=attachments
            )
            
        except Exception as e:
            logger.error(f"Failed to send template email: {str(e)}")
            return False
    
    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML to plain text.
        This is a very simple implementation that just removes HTML tags.
        For a more sophisticated conversion, use a library like beautifulsoup4.
        """
        import re
        
        # Remove HTML tags
        text = re.sub(r'<.*?>', ' ', html)
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n+', '\n\n', text)
        
        return text.strip()

    def send_notification_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None
    ) -> bool:
        """Send a notification email to a user."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Plain text version
            text_part = MIMEText(content, 'plain')
            msg.attach(text_part)

            # HTML version (if provided)
            if html_content:
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)

            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Successfully sent notification email to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send notification email: {str(e)}")
            return False

async def send_email_notification(
    recipient_email: str,
    subject: str,
    content: str,
    cc: List[str] = None,
    attachments: List[str] = None
) -> bool:
    """Send an email notification."""
    try:
        # Create message schema
        message = MessageSchema(
            subject=subject,
            recipients=[recipient_email],
            body=content,
            cc=cc or [],
            subtype="plain"
        )

        # Send email
        await fastmail.send_message(message)
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False 