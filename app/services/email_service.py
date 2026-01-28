"""
ENTERPRISE EMAIL SERVICE
Supports: Verification emails, OTP, Password reset, Welcome emails, Invoices
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from typing import Optional
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Enterprise email service"""
    
    @staticmethod
    def _send_email(
        to_email: str,
        subject: str,
        html_content: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Add attachment if provided
            if attachment_path and Path(attachment_path).exists():
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={Path(attachment_path).name}'
                    )
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_email(email: str, name: str, verification_url: str) -> bool:
        """Send email verification"""
        subject = "Verify Your RapidReportz Account"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 15px 30px; background: #667eea; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to RapidReportz!</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{name}</strong>,</p>
                    <p>Thank you for registering with RapidReportz! We're excited to have you on board.</p>
                    <p>To complete your registration and activate your account, please verify your email address by clicking the button below:</p>
                    <center>
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </center>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #667eea;">{verification_url}</p>
                    <p><strong>This link will expire in 24 hours.</strong></p>
                    <hr>
                    <p>If you didn't create this account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2026 RapidReportz by OS2 Studio. All rights reserved.</p>
                    <p>Dindigul, Tamil Nadu, India</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email(email, subject, html_content)
    
    @staticmethod
    def send_otp_email(email: str, name: str, otp_code: str) -> bool:
        """Send OTP via email"""
        subject = "Your RapidReportz Verification Code"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #667eea; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .otp-box {{ background: white; border: 2px dashed #667eea; padding: 20px; 
                           text-align: center; margin: 20px 0; border-radius: 10px; }}
                .otp-code {{ font-size: 36px; font-weight: bold; letter-spacing: 10px; 
                            color: #667eea; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🔐 Verification Code</h2>
                </div>
                <div class="content">
                    <p>Hi <strong>{name}</strong>,</p>
                    <p>Your verification code is:</p>
                    <div class="otp-box">
                        <div class="otp-code">{otp_code}</div>
                    </div>
                    <p><strong>This code will expire in 10 minutes.</strong></p>
                    <p>If you didn't request this code, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email(email, subject, html_content)
    
    @staticmethod
    def send_password_reset_email(email: str, name: str, reset_url: str) -> bool:
        """Send password reset email"""
        subject = "Reset Your RapidReportz Password"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ff6b6b; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ display: inline-block; padding: 15px 30px; background: #ff6b6b; 
                          color: white; text-decoration: none; border-radius: 5px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; 
                           margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🔒 Password Reset Request</h2>
                </div>
                <div class="content">
                    <p>Hi <strong>{name}</strong>,</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <center>
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </center>
                    <p>Or copy and paste this link:</p>
                    <p style="word-break: break-all; color: #ff6b6b;">{reset_url}</p>
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul>
                            <li>This link expires in 1 hour</li>
                            <li>If you didn't request this, ignore this email</li>
                            <li>Your password won't change until you create a new one</li>
                        </ul>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email(email, subject, html_content)
    
    @staticmethod
    def send_welcome_email(email: str, name: str, user_type: str, welcome_bonus: float) -> bool:
        """Send welcome email after email verification"""
        subject = "Welcome to RapidReportz - Let's Get Started! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 40px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .bonus-box {{ background: #d4edda; border: 2px solid #28a745; padding: 20px; 
                             text-align: center; margin: 20px 0; border-radius: 10px; }}
                .features {{ background: white; padding: 20px; margin: 20px 0; border-radius: 10px; }}
                .feature-item {{ margin: 15px 0; padding-left: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 You're All Set!</h1>
                    <p style="font-size: 18px; margin: 10px 0;">Welcome to RapidReportz</p>
                </div>
                <div class="content">
                    <p>Hi <strong>{name}</strong>,</p>
                    <p>Your account is now active and ready to use! As a welcome gift, we've added a bonus to your wallet:</p>
                    
                    <div class="bonus-box">
                        <h2 style="margin: 0; color: #28a745;">🎁 Welcome Bonus</h2>
                        <p style="font-size: 28px; font-weight: bold; margin: 10px 0; color: #28a745;">
                            RM {welcome_bonus}
                        </p>
                        <p style="margin: 0;">Start generating reports right away!</p>
                    </div>
                    
                    <div class="features">
                        <h3>What's Next?</h3>
                        <div class="feature-item">
                            <strong>📊 Generate Reports:</strong> Create professional reports instantly
                        </div>
                        <div class="feature-item">
                            <strong>📝 Build Templates:</strong> Save time with custom templates
                        </div>
                        <div class="feature-item">
                            <strong>💰 Top Up Wallet:</strong> Add funds anytime via Billplz
                        </div>
                        {'<div class="feature-item"><strong>👥 Add Team Members:</strong> Invite your team (Enterprise)</div>' if user_type == 'enterprise' else ''}
                    </div>
                    
                    <center>
                        <a href="{settings.FRONTEND_URL}/dashboard" 
                           style="display: inline-block; padding: 15px 30px; background: #667eea; 
                                  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0;">
                            Go to Dashboard
                        </a>
                    </center>
                    
                    <p>Need help? Check out our <a href="{settings.FRONTEND_URL}/docs">documentation</a> or contact support.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email(email, subject, html_content)
    
    @staticmethod
    def send_invoice_email(email: str, name: str, invoice_number: str, amount: float, pdf_path: Optional[str] = None) -> bool:
        """Send invoice email"""
        subject = f"Invoice #{invoice_number} from RapidReportz"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #667eea; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .invoice-box {{ background: white; border: 1px solid #ddd; padding: 20px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>📄 Invoice</h2>
                </div>
                <div class="content">
                    <p>Hi <strong>{name}</strong>,</p>
                    <p>Thank you for your payment! Here's your invoice:</p>
                    <div class="invoice-box">
                        <p><strong>Invoice Number:</strong> {invoice_number}</p>
                        <p><strong>Amount:</strong> RM {amount:.2f}</p>
                        <p><strong>Status:</strong> Paid ✅</p>
                    </div>
                    <p>Your invoice is attached to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email(email, subject, html_content, pdf_path)
    
    @staticmethod
    def send_subscription_expiry_reminder(email: str, name: str, days_remaining: int) -> bool:
        """Send subscription expiry reminder"""
        subject = f"⏰ Your Subscription Expires in {days_remaining} Days"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ffc107; color: #333; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; }}
                .button {{ display: inline-block; padding: 15px 30px; background: #28a745; 
                          color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>⏰ Subscription Expiring Soon</h2>
                </div>
                <div class="content">
                    <p>Hi <strong>{name}</strong>,</p>
                    <div class="warning">
                        <p><strong>Your subscription will expire in {days_remaining} days.</strong></p>
                    </div>
                    <p>Don't lose access to your account! Renew now to continue enjoying:</p>
                    <ul>
                        <li>✅ Unlimited report generation</li>
                        <li>✅ Custom templates</li>
                        <li>✅ Priority support</li>
                        <li>✅ Advanced features</li>
                    </ul>
                    <center>
                        <a href="{settings.FRONTEND_URL}/subscription" class="button">
                            Renew Subscription
                        </a>
                    </center>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email(email, subject, html_content)
