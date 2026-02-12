"""Email alert delivery channel."""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from ..models import Alert, AlertSeverity
from .base import AlertChannel


class EmailChannel(AlertChannel):
    """
    Email delivery channel using SMTP.

    Supports both immediate delivery for critical alerts
    and batching for daily summaries.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_addr: str,
        to_addrs: list[str],
        use_tls: bool = True,
        retry_attempts: int = 3,
    ):
        """
        Initialize email channel.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (typically 587 for TLS, 465 for SSL)
            smtp_user: SMTP authentication username
            smtp_password: SMTP authentication password
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
            use_tls: Whether to use TLS (default True)
            retry_attempts: Number of retry attempts on failure
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls
        self.retry_attempts = retry_attempts

    async def send(self, alert: Alert) -> bool:
        """
        Send alert via email.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully

        Raises:
            Exception: On delivery failure after all retries
        """
        for attempt in range(self.retry_attempts):
            try:
                # Run SMTP operations in thread pool to avoid blocking
                await asyncio.to_thread(self._send_smtp, alert)
                return True

            except Exception:
                if attempt == self.retry_attempts - 1:
                    raise  # Re-raise on final attempt
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)

        return False

    def _send_smtp(self, alert: Alert):
        """
        Send email via SMTP (synchronous).

        Args:
            alert: Alert to send

        Raises:
            Exception: On SMTP failure
        """
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg["Date"] = alert.timestamp.strftime("%a, %d %b %Y %H:%M:%S %z")

        # Plain text version
        text_body = self._format_text(alert)
        msg.attach(MIMEText(text_body, "plain"))

        # HTML version
        html_body = self._format_html(alert)
        msg.attach(MIMEText(html_body, "html"))

        # Send via SMTP
        if self.use_tls:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

    def _format_text(self, alert: Alert) -> str:
        """
        Format alert as plain text email.

        Args:
            alert: Alert to format

        Returns:
            Plain text email body
        """
        lines = [
            f"Alert: {alert.title}",
            f"Severity: {alert.severity.value.upper()}",
            f"Trigger: {alert.trigger.value}",
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Message:",
            alert.message,
        ]

        if alert.context:
            lines.append("")
            lines.append("Additional Context:")
            for key, value in alert.context.items():
                lines.append(f"  {key}: {value}")

        lines.append("")
        lines.append("---")
        lines.append("This is an automated alert from Market-Watch Trading Bot")

        return "\n".join(lines)

    def _format_html(self, alert: Alert) -> str:
        """
        Format alert as HTML email.

        Args:
            alert: Alert to format

        Returns:
            HTML email body
        """
        # Color code by severity
        severity_colors = {
            AlertSeverity.LOW: "#28a745",      # Green
            AlertSeverity.MEDIUM: "#ffc107",   # Yellow
            AlertSeverity.HIGH: "#fd7e14",     # Orange
            AlertSeverity.CRITICAL: "#dc3545", # Red
        }
        color = severity_colors.get(alert.severity, "#6c757d")

        context_rows = ""
        if alert.context:
            context_items = "".join([
                f"<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>"
                for key, value in alert.context.items()
            ])
            context_rows = f"""
            <tr>
                <td colspan="2">
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">
                    <strong>Additional Context:</strong>
                    <table style="width: 100%; margin-top: 5px;">
                        {context_items}
                    </table>
                </td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px; }}
                .info-table {{ width: 100%; margin: 15px 0; }}
                .info-table td {{ padding: 5px; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">[{alert.severity.value.upper()}] {alert.title}</h2>
                </div>
                <div class="content">
                    <table class="info-table">
                        <tr>
                            <td><strong>Severity:</strong></td>
                            <td>{alert.severity.value.upper()}</td>
                        </tr>
                        <tr>
                            <td><strong>Trigger:</strong></td>
                            <td>{alert.trigger.value}</td>
                        </tr>
                        <tr>
                            <td><strong>Time:</strong></td>
                            <td>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                        </tr>
                        <tr>
                            <td colspan="2">
                                <hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">
                                <strong>Message:</strong>
                                <p style="margin: 10px 0;">{alert.message}</p>
                            </td>
                        </tr>
                        {context_rows}
                    </table>
                </div>
                <div class="footer">
                    This is an automated alert from Market-Watch Trading Bot
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate email channel configuration.

        Args:
            config: Configuration dict with SMTP settings

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        required = ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_addr", "to_addrs"]

        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(config["to_addrs"], list) or len(config["to_addrs"]) == 0:
            raise ValueError("to_addrs must be a non-empty list")

        if not isinstance(config["smtp_port"], int):
            raise ValueError("smtp_port must be an integer")

        return True

    def get_name(self) -> str:
        """Get channel name."""
        return "Email"
