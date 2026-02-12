"""Runtime alert configuration and wiring."""
from __future__ import annotations

import config
from alerts.channels.email import EmailChannel
from alerts.channels.webhook import WebhookChannel, WebhookType
from alerts.manager import get_manager
from alerts.models import AlertRule, AlertSeverity, AlertTrigger, ChannelType

_DEFAULT_ANOMALY_RULE_ID = "default_anomaly_rule"
_DEFAULT_CUSTOM_RULE_ID = "default_custom_rule"
_DEFAULT_CIRCUIT_BREAKER_RULE_ID = "default_circuit_breaker_rule"
_DEFAULT_DAILY_LOSS_RULE_ID = "default_daily_loss_rule"
_DEFAULT_MAX_DRAWDOWN_RULE_ID = "default_max_drawdown_rule"
_DEFAULT_ORDER_FAILED_RULE_ID = "default_order_failed_rule"
_DEFAULT_SYSTEM_ERROR_RULE_ID = "default_system_error_rule"


def configure_alerts(runtime_config: dict) -> dict:
    """
    Configure alert channels and default anomaly rule based on runtime config.

    Returns a summary dict for debugging/UI.
    """
    manager = get_manager()
    alerts_enabled = bool(runtime_config.get("alerts_enabled", False))

    enabled_channels: list[ChannelType] = []

    # Email channel
    if alerts_enabled and runtime_config.get("alert_email_enabled", False):
        channel = _build_email_channel()
        if channel:
            manager.register_channel(ChannelType.EMAIL, channel)
            enabled_channels.append(ChannelType.EMAIL)
        else:
            manager.unregister_channel(ChannelType.EMAIL)
    else:
        manager.unregister_channel(ChannelType.EMAIL)

    # Webhook channel
    if alerts_enabled and runtime_config.get("alert_webhook_enabled", False):
        channel = _build_webhook_channel()
        if channel:
            manager.register_channel(ChannelType.WEBHOOK, channel)
            enabled_channels.append(ChannelType.WEBHOOK)
        else:
            manager.unregister_channel(ChannelType.WEBHOOK)
    else:
        manager.unregister_channel(ChannelType.WEBHOOK)

    def _apply_rule(rule: AlertRule) -> bool:
        if alerts_enabled and enabled_channels:
            manager.add_rule(rule)
            return True
        manager.remove_rule(rule.id)
        return False

    anomaly_rule_enabled = _apply_rule(AlertRule(
        id=_DEFAULT_ANOMALY_RULE_ID,
        name="Anomaly Detected",
        trigger=AlertTrigger.ANOMALY_DETECTED,
        severity=AlertSeverity.MEDIUM,
        channels=enabled_channels,
        enabled=True,
    ))

    custom_rule_enabled = _apply_rule(AlertRule(
        id=_DEFAULT_CUSTOM_RULE_ID,
        name="Custom Alert (Test)",
        trigger=AlertTrigger.CUSTOM,
        severity=AlertSeverity.LOW,
        channels=enabled_channels,
        enabled=True,
    ))

    circuit_rule_enabled = _apply_rule(AlertRule(
        id=_DEFAULT_CIRCUIT_BREAKER_RULE_ID,
        name="Circuit Breaker Activated",
        trigger=AlertTrigger.CIRCUIT_BREAKER,
        severity=AlertSeverity.HIGH,
        channels=enabled_channels,
        enabled=True,
    ))

    daily_loss_rule_enabled = _apply_rule(AlertRule(
        id=_DEFAULT_DAILY_LOSS_RULE_ID,
        name="Daily Loss Limit Hit",
        trigger=AlertTrigger.DAILY_LOSS_LIMIT,
        severity=AlertSeverity.CRITICAL,
        channels=enabled_channels,
        enabled=True,
    ))

    max_drawdown_rule_enabled = _apply_rule(AlertRule(
        id=_DEFAULT_MAX_DRAWDOWN_RULE_ID,
        name="Max Drawdown Limit Hit",
        trigger=AlertTrigger.MAX_DRAWDOWN,
        severity=AlertSeverity.CRITICAL,
        channels=enabled_channels,
        enabled=True,
    ))

    order_failed_rule_enabled = _apply_rule(AlertRule(
        id=_DEFAULT_ORDER_FAILED_RULE_ID,
        name="Order Failed",
        trigger=AlertTrigger.ORDER_FAILED,
        severity=AlertSeverity.HIGH,
        channels=enabled_channels,
        enabled=True,
    ))

    system_error_rule_enabled = _apply_rule(AlertRule(
        id=_DEFAULT_SYSTEM_ERROR_RULE_ID,
        name="System Error",
        trigger=AlertTrigger.SYSTEM_ERROR,
        severity=AlertSeverity.HIGH,
        channels=enabled_channels,
        enabled=True,
    ))

    return {
        "alerts_enabled": alerts_enabled,
        "channels": [ch.value for ch in enabled_channels],
        "anomaly_rule_enabled": anomaly_rule_enabled,
        "custom_rule_enabled": custom_rule_enabled,
        "circuit_breaker_rule_enabled": circuit_rule_enabled,
        "daily_loss_rule_enabled": daily_loss_rule_enabled,
        "max_drawdown_rule_enabled": max_drawdown_rule_enabled,
        "order_failed_rule_enabled": order_failed_rule_enabled,
        "system_error_rule_enabled": system_error_rule_enabled,
    }


def _build_email_channel() -> EmailChannel | None:
    to_addrs = _parse_email_list(config.ALERT_EMAIL_TO)
    if not config.ALERT_EMAIL_SMTP_HOST:
        print("Alert email disabled: ALERT_EMAIL_SMTP_HOST missing")
        return None
    if not config.ALERT_EMAIL_SMTP_USER or not config.ALERT_EMAIL_SMTP_PASSWORD:
        print("Alert email disabled: SMTP credentials missing")
        return None
    if not config.ALERT_EMAIL_FROM:
        print("Alert email disabled: ALERT_EMAIL_FROM missing")
        return None
    if not to_addrs:
        print("Alert email disabled: ALERT_EMAIL_TO missing")
        return None

    return EmailChannel(
        smtp_host=config.ALERT_EMAIL_SMTP_HOST,
        smtp_port=config.ALERT_EMAIL_SMTP_PORT,
        smtp_user=config.ALERT_EMAIL_SMTP_USER,
        smtp_password=config.ALERT_EMAIL_SMTP_PASSWORD,
        from_addr=config.ALERT_EMAIL_FROM,
        to_addrs=to_addrs,
        use_tls=config.ALERT_EMAIL_USE_TLS,
        retry_attempts=config.ALERT_EMAIL_RETRY_ATTEMPTS,
    )


def _build_webhook_channel() -> WebhookChannel | None:
    if not config.ALERT_WEBHOOK_URL:
        print("Alert webhook disabled: ALERT_WEBHOOK_URL missing")
        return None

    webhook_type = _parse_webhook_type(config.ALERT_WEBHOOK_TYPE)

    return WebhookChannel(
        webhook_url=config.ALERT_WEBHOOK_URL,
        webhook_type=webhook_type,
        retry_attempts=config.ALERT_WEBHOOK_RETRY_ATTEMPTS,
        timeout_seconds=config.ALERT_WEBHOOK_TIMEOUT_SECONDS,
    )


def _parse_email_list(value: str) -> list[str]:
    if not value:
        return []
    return [email.strip() for email in value.split(",") if email.strip()]


def _parse_webhook_type(value: str) -> WebhookType:
    try:
        return WebhookType(value)
    except Exception:
        print(f"Unknown webhook type '{value}', defaulting to generic")
        return WebhookType.GENERIC
