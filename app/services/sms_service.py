"""
SMS SERVICE for OTP Verification
Supports: Twilio, AWS SNS, or custom SMS gateway
"""
import logging
from typing import Optional
import requests

from core.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service for sending OTP and notifications"""
    
    @staticmethod
    def send_otp(phone_number: str, otp_code: str) -> bool:
        """
        Send OTP via SMS
        
        Supports multiple providers:
        - Twilio
        - AWS SNS
        - Custom SMS gateway
        """
        try:
            if settings.SMS_PROVIDER == "twilio":
                return SMSService._send_via_twilio(phone_number, otp_code)
            elif settings.SMS_PROVIDER == "aws_sns":
                return SMSService._send_via_aws_sns(phone_number, otp_code)
            else:
                return SMSService._send_via_custom(phone_number, otp_code)
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False
    
    @staticmethod
    def _send_via_twilio(phone_number: str, otp_code: str) -> bool:
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            message = client.messages.create(
                body=f"Your RapidReportz verification code is: {otp_code}. Valid for 10 minutes.",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            logger.info(f"SMS sent via Twilio to {phone_number}, SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Twilio SMS failed: {str(e)}")
            return False
    
    @staticmethod
    def _send_via_aws_sns(phone_number: str, otp_code: str) -> bool:
        """Send SMS via AWS SNS"""
        try:
            import boto3
            
            sns = boto3.client(
                'sns',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            
            response = sns.publish(
                PhoneNumber=phone_number,
                Message=f"Your RapidReportz verification code is: {otp_code}. Valid for 10 minutes.",
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            
            logger.info(f"SMS sent via AWS SNS to {phone_number}, MessageId: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"AWS SNS SMS failed: {str(e)}")
            return False
    
    @staticmethod
    def _send_via_custom(phone_number: str, otp_code: str) -> bool:
        """
        Send SMS via custom gateway
        Replace with your SMS provider's API
        """
        try:
            # Example for Malaysian SMS gateway
            api_url = settings.SMS_GATEWAY_URL
            api_key = settings.SMS_API_KEY
            
            payload = {
                "phone": phone_number,
                "message": f"Your RapidReportz OTP: {otp_code}. Valid for 10 minutes.",
                "sender_id": "RapidRpt"
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"SMS sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"SMS gateway returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Custom SMS gateway failed: {str(e)}")
            return False
    
    @staticmethod
    def send_notification(phone_number: str, message: str) -> bool:
        """Send general notification SMS"""
        try:
            if settings.SMS_PROVIDER == "twilio":
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=phone_number
                )
            
            logger.info(f"Notification SMS sent to {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification SMS: {str(e)}")
            return False
