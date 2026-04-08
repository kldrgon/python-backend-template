# -*- coding: utf-8 -*-
"""
邮件发送服务
提供验证码邮件发送功能
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import structlog
import socket
from typing import Optional

from core.config import config

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class EmailSender:
    """邮件发送服务"""

    # SMTP 连接超时时间（秒）
    SMTP_TIMEOUT = 10

    @staticmethod
    async def send_captcha_email(to_email: str, captcha_code: str) -> bool:
        """
        发送验证码邮件

        Args:
            to_email: 收件人邮箱
            captcha_code: 验证码

        Returns:
            是否发送成功
        """
        try:
            if not hasattr(config, 'SMTP_HOST') or not config.SMTP_HOST:
                logger.warning("smtp_not_configured", captcha=captcha_code, to=to_email)
                print(f"\n{'='*50}\n发送验证码至 {to_email}\n验证码：{captcha_code}\n{'='*50}\n")
                return True

            logger.info("sending_captcha_email", to=to_email, smtp_host=config.SMTP_HOST)

            msg = MIMEMultipart()
            msg['From'] = config.SMTP_USERNAME
            msg['To'] = to_email
            msg['Subject'] = '验证码 - EduForge'

            body = f"""
            <html>
            <body>
                <h2>欢迎使用 EduForge</h2>
                <p>您的验证码：<strong style="font-size: 24px; color: #1890ff;">{captcha_code}</strong></p>
                <p>验证码有效期 5 分钟，请尽快使用。</p>
                <p>如非本人操作，请忽略此邮件。</p>
                <br/>
                <p>谢谢！</p>
                <p>EduForge 团队</p>
            </body>
            </html>
            """

            msg.attach(MIMEText(body, 'html', 'utf-8'))

            server = None
            try:
                if config.SMTP_PORT == 465:
                    logger.info("smtp_ssl_connect", host=config.SMTP_HOST, port=config.SMTP_PORT)
                    server = smtplib.SMTP_SSL(
                        config.SMTP_HOST,
                        config.SMTP_PORT,
                        timeout=EmailSender.SMTP_TIMEOUT,
                    )
                else:
                    logger.info("smtp_connect", host=config.SMTP_HOST, port=config.SMTP_PORT)
                    server = smtplib.SMTP(
                        config.SMTP_HOST,
                        config.SMTP_PORT,
                        timeout=EmailSender.SMTP_TIMEOUT,
                    )
                    if config.SMTP_USE_TLS:
                        logger.info("smtp_starttls")
                        server.starttls()

                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.send_message(msg)
                logger.info("captcha_email_sent", to=to_email)
                return True
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception as e:
                        logger.warning("smtp_quit_failed", error=str(e))
                        try:
                            server.close()
                        except Exception:
                            pass

        except socket.timeout as e:
            logger.error("smtp_timeout", to=to_email, error=str(e))
            return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error("smtp_auth_error", to=to_email, error=str(e))
            return False
        except smtplib.SMTPConnectError as e:
            logger.error("smtp_connect_error", to=to_email, error=str(e))
            return False
        except smtplib.SMTPException as e:
            logger.error("smtp_error", to=to_email, error=str(e))
            return False
        except Exception as e:
            logger.error("email_send_failed", to=to_email, exc_type=type(e).__name__, error=str(e), exc_info=True)
            return False
