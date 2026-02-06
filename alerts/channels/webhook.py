"""Webhook alert delivery channel."""
import asyncio
import aiohttp
from typing import Dict, Any
from enum import Enum

from .base import AlertChannel
from ..models import Alert, AlertSeverity


class WebhookType(Enum):
    """Supported webhook types."""
    GENERIC = "generic"      # Generic JSON POST
    DISCORD = "discord"      # Discord webhook format
    SLACK = "slack"          # Slack incoming webhook format
    TELEGRAM = "telegram"    # Telegram bot API format


class WebhookChannel(AlertChannel):
    """
    Webhook delivery channel with support for multiple platforms.

    Sends alerts via HTTP POST to configured webhook URLs.
    Supports platform-specific payload formatting.
    """

    def __init__(
        self,
        webhook_url: str,
        webhook_type: WebhookType = WebhookType.GENERIC,
        retry_attempts: int = 3,
        timeout_seconds: int = 10,
    ):
        """
        Initialize webhook channel.

        Args:
            webhook_url: URL to POST alerts to
            webhook_type: Type of webhook (affects payload format)
            retry_attempts: Number of retry attempts on failure
            timeout_seconds: HTTP request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.webhook_type = webhook_type
        self.retry_attempts = retry_attempts
        self.timeout_seconds = timeout_seconds

    async def send(self, alert: Alert) -> bool:
        """
        Send alert via webhook.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully

        Raises:
            Exception: On delivery failure after all retries
        """
        payload = self._format_payload(alert)

        for attempt in range(self.retry_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
                    async with session.post(
                        self.webhook_url,
                        json=payload,
                        timeout=timeout
                    ) as response:
                        response.raise_for_status()
                        return True

            except Exception as exc:
                if attempt == self.retry_attempts - 1:
                    raise  # Re-raise on final attempt
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        return False

    def _format_payload(self, alert: Alert) -> Dict[str, Any]:
        """
        Format alert as webhook payload.

        Args:
            alert: Alert to format

        Returns:
            Payload dict for the webhook
        """
        if self.webhook_type == WebhookType.DISCORD:
            return self._format_discord(alert)
        elif self.webhook_type == WebhookType.SLACK:
            return self._format_slack(alert)
        elif self.webhook_type == WebhookType.TELEGRAM:
            return self._format_telegram(alert)
        else:
            return self._format_generic(alert)

    def _format_generic(self, alert: Alert) -> Dict[str, Any]:
        """
        Format as generic JSON payload.

        Args:
            alert: Alert to format

        Returns:
            Generic alert payload
        """
        return alert.to_dict()

    def _format_discord(self, alert: Alert) -> Dict[str, Any]:
        """
        Format as Discord webhook payload.

        Discord webhook format: https://discord.com/developers/docs/resources/webhook

        Args:
            alert: Alert to format

        Returns:
            Discord-formatted payload
        """
        # Color code by severity
        severity_colors = {
            AlertSeverity.LOW: 0x28a745,      # Green
            AlertSeverity.MEDIUM: 0xffc107,   # Yellow
            AlertSeverity.HIGH: 0xfd7e14,     # Orange
            AlertSeverity.CRITICAL: 0xdc3545, # Red
        }
        color = severity_colors.get(alert.severity, 0x6c757d)

        # Build embed fields
        fields = [
            {
                "name": "Trigger",
                "value": alert.trigger.value,
                "inline": True
            },
            {
                "name": "Time",
                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "inline": True
            },
        ]

        # Add context fields
        if alert.context:
            for key, value in alert.context.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": False
                })

        return {
            "embeds": [{
                "title": f"[{alert.severity.value.upper()}] {alert.title}",
                "description": alert.message,
                "color": color,
                "fields": fields,
                "footer": {
                    "text": "Market-Watch Trading Bot"
                }
            }]
        }

    def _format_slack(self, alert: Alert) -> Dict[str, Any]:
        """
        Format as Slack incoming webhook payload.

        Slack webhook format: https://api.slack.com/messaging/webhooks

        Args:
            alert: Alert to format

        Returns:
            Slack-formatted payload
        """
        # Color code by severity
        severity_colors = {
            AlertSeverity.LOW: "good",       # Green
            AlertSeverity.MEDIUM: "warning", # Yellow
            AlertSeverity.HIGH: "danger",    # Orange/Red
            AlertSeverity.CRITICAL: "danger", # Red
        }
        color = severity_colors.get(alert.severity, "#6c757d")

        # Build context fields
        fields = [
            {
                "title": "Trigger",
                "value": alert.trigger.value,
                "short": True
            },
            {
                "title": "Time",
                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "short": True
            },
        ]

        # Add context fields
        if alert.context:
            for key, value in alert.context.items():
                fields.append({
                    "title": key,
                    "value": str(value),
                    "short": False
                })

        return {
            "attachments": [{
                "color": color,
                "title": f"[{alert.severity.value.upper()}] {alert.title}",
                "text": alert.message,
                "fields": fields,
                "footer": "Market-Watch Trading Bot",
                "ts": int(alert.timestamp.timestamp())
            }]
        }

    def _format_telegram(self, alert: Alert) -> Dict[str, Any]:
        """
        Format as Telegram bot message.

        Telegram bot API: https://core.telegram.org/bots/api#sendmessage

        Args:
            alert: Alert to format

        Returns:
            Telegram-formatted payload
        """
        # Build message text with Markdown formatting
        lines = [
            f"*[{alert.severity.value.upper()}] {alert.title}*",
            "",
            alert.message,
            "",
            f"*Trigger:* {alert.trigger.value}",
            f"*Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        # Add context
        if alert.context:
            lines.append("")
            for key, value in alert.context.items():
                lines.append(f"*{key}:* {value}")

        lines.append("")
        lines.append("_Market-Watch Trading Bot_")

        return {
            "text": "\n".join(lines),
            "parse_mode": "Markdown"
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate webhook channel configuration.

        Args:
            config: Configuration dict with webhook settings

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        if "webhook_url" not in config:
            raise ValueError("Missing required field: webhook_url")

        if not isinstance(config["webhook_url"], str):
            raise ValueError("webhook_url must be a string")

        if not config["webhook_url"].startswith(("http://", "https://")):
            raise ValueError("webhook_url must start with http:// or https://")

        if "webhook_type" in config:
            if config["webhook_type"] not in [t.value for t in WebhookType]:
                raise ValueError(f"Invalid webhook_type: {config['webhook_type']}")

        return True

    def get_name(self) -> str:
        """Get channel name."""
        return f"Webhook ({self.webhook_type.value})"
