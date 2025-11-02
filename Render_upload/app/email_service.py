"""
Email Service Module
Obsługa wysyłania emaili przez SMTP (Gmail)
"""
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from .config import settings


class EmailService:
    """Serwis do wysyłania emaili"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS
    
    def _create_smtp_connection(self):
        """Tworzy połączenie SMTP"""
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {e}")
            raise
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Wysyła email
        
        Args:
            to_email: Adres odbiorcy
            subject: Temat wiadomości
            html_content: Treść HTML
            text_content: Treść tekstowa (fallback)
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        try:
            # Tworzenie wiadomości
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email
            message['Subject'] = subject
            
            # Dodaj treść tekstową jeśli podana
            if text_content:
                part1 = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(part1)
            
            # Dodaj treść HTML
            part2 = MIMEText(html_content, 'html', 'utf-8')
            message.attach(part2)
            
            # Wysyłanie
            server = self._create_smtp_connection()
            server.sendmail(self.from_email, to_email, message.as_string())
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def generate_verification_code(self, length: int = 6) -> str:
        """
        Generuje losowy kod weryfikacyjny
        
        Args:
            length: Długość kodu (domyślnie 6)
        
        Returns:
            Kod weryfikacyjny (cyfry)
        """
        return ''.join(random.choices(string.digits, k=length))
    
    def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_code: str,
        language: str = 'pl'
    ) -> bool:
        """
        Wysyła email z kodem weryfikacyjnym
        
        Args:
            to_email: Adres email użytkownika
            user_name: Imię użytkownika
            verification_code: Kod weryfikacyjny
            language: Język (pl/en/de)
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        # Tłumaczenia
        translations = {
            'pl': {
                'subject': 'Kod weryfikacyjny - PRO-Ka-Po',
                'greeting': f'Cześć {user_name}!',
                'message': 'Twój kod weryfikacyjny to:',
                'expires': f'Kod wygasa za {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minut.',
                'ignore': 'Jeśli nie rejestrowałeś się w PRO-Ka-Po, zignoruj tę wiadomość.',
                'footer': 'Pozdrawiamy,<br>Zespół PRO-Ka-Po'
            },
            'en': {
                'subject': 'Verification Code - PRO-Ka-Po',
                'greeting': f'Hello {user_name}!',
                'message': 'Your verification code is:',
                'expires': f'This code expires in {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutes.',
                'ignore': 'If you didn\'t sign up for PRO-Ka-Po, please ignore this email.',
                'footer': 'Best regards,<br>PRO-Ka-Po Team'
            },
            'de': {
                'subject': 'Bestätigungscode - PRO-Ka-Po',
                'greeting': f'Hallo {user_name}!',
                'message': 'Ihr Bestätigungscode lautet:',
                'expires': f'Dieser Code läuft in {settings.VERIFICATION_CODE_EXPIRE_MINUTES} Minuten ab.',
                'ignore': 'Wenn Sie sich nicht bei PRO-Ka-Po angemeldet haben, ignorieren Sie diese E-Mail.',
                'footer': 'Mit freundlichen Grüßen,<br>PRO-Ka-Po Team'
            }
        }
        
        t = translations.get(language, translations['pl'])
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code-box {{ background: white; border: 2px dashed #667eea; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 5px; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PRO-Ka-Po Kaizen Freak</h1>
                </div>
                <div class="content">
                    <h2>{t['greeting']}</h2>
                    <p>{t['message']}</p>
                    <div class="code-box">
                        <div class="code">{verification_code}</div>
                    </div>
                    <div class="warning">
                        ⏱️ {t['expires']}
                    </div>
                    <p>{t['ignore']}</p>
                    <p>{t['footer']}</p>
                </div>
                <div class="footer">
                    <p>© 2025 PRO-Ka-Po Kaizen Freak. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {t['greeting']}
        
        {t['message']}
        
        {verification_code}
        
        {t['expires']}
        {t['ignore']}
        
        {t['footer']}
        """
        
        return self.send_email(to_email, t['subject'], html_content, text_content)
    
    def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_code: str,
        language: str = 'pl'
    ) -> bool:
        """
        Wysyła email z kodem resetu hasła
        
        Args:
            to_email: Adres email użytkownika
            user_name: Imię użytkownika
            reset_code: Kod resetu hasła
            language: Język (pl/en/de)
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        translations = {
            'pl': {
                'subject': 'Reset hasła - PRO-Ka-Po',
                'greeting': f'Cześć {user_name}!',
                'message': 'Otrzymaliśmy prośbę o reset hasła dla Twojego konta.',
                'code_label': 'Twój kod resetujący hasło to:',
                'expires': f'Kod wygasa za {settings.RESET_PASSWORD_CODE_EXPIRE_MINUTES} minut.',
                'ignore': 'Jeśli nie prosiłeś o reset hasła, zignoruj tę wiadomość.',
                'security': 'Ze względów bezpieczeństwa nigdy nie udostępniaj tego kodu nikomu.',
                'footer': 'Pozdrawiamy,<br>Zespół PRO-Ka-Po'
            },
            'en': {
                'subject': 'Password Reset - PRO-Ka-Po',
                'greeting': f'Hello {user_name}!',
                'message': 'We received a request to reset your password.',
                'code_label': 'Your password reset code is:',
                'expires': f'This code expires in {settings.RESET_PASSWORD_CODE_EXPIRE_MINUTES} minutes.',
                'ignore': 'If you didn\'t request a password reset, please ignore this email.',
                'security': 'For security reasons, never share this code with anyone.',
                'footer': 'Best regards,<br>PRO-Ka-Po Team'
            },
            'de': {
                'subject': 'Passwort zurücksetzen - PRO-Ka-Po',
                'greeting': f'Hallo {user_name}!',
                'message': 'Wir haben eine Anfrage zum Zurücksetzen Ihres Passworts erhalten.',
                'code_label': 'Ihr Passwort-Reset-Code lautet:',
                'expires': f'Dieser Code läuft in {settings.RESET_PASSWORD_CODE_EXPIRE_MINUTES} Minuten ab.',
                'ignore': 'Wenn Sie kein Zurücksetzen des Passworts angefordert haben, ignorieren Sie diese E-Mail.',
                'security': 'Aus Sicherheitsgründen teilen Sie diesen Code niemals mit jemandem.',
                'footer': 'Mit freundlichen Grüßen,<br>PRO-Ka-Po Team'
            }
        }
        
        t = translations.get(language, translations['pl'])
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code-box {{ background: white; border: 2px dashed #f5576c; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 36px; font-weight: bold; color: #f5576c; letter-spacing: 5px; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 15px 0; }}
                .security {{ background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 PRO-Ka-Po</h1>
                    <p>Reset hasła</p>
                </div>
                <div class="content">
                    <h2>{t['greeting']}</h2>
                    <p>{t['message']}</p>
                    <p>{t['code_label']}</p>
                    <div class="code-box">
                        <div class="code">{reset_code}</div>
                    </div>
                    <div class="warning">
                        ⏱️ {t['expires']}
                    </div>
                    <div class="security">
                        🔒 {t['security']}
                    </div>
                    <p>{t['ignore']}</p>
                    <p>{t['footer']}</p>
                </div>
                <div class="footer">
                    <p>© 2025 PRO-Ka-Po Kaizen Freak. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {t['greeting']}
        
        {t['message']}
        {t['code_label']}
        
        {reset_code}
        
        {t['expires']}
        {t['security']}
        {t['ignore']}
        
        {t['footer']}
        """
        
        return self.send_email(to_email, t['subject'], html_content, text_content)


# Singleton instance
_email_service = None

def get_email_service() -> EmailService:
    """Pobiera instancję EmailService (singleton)"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
