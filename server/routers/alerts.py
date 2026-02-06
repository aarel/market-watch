"""Alert management API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime

from alerts.manager import get_manager
from alerts.models import Alert, AlertTrigger, AlertSeverity, ChannelType
from ..dependencies import get_state

router = APIRouter()


@router.get("/alerts/history")
async def get_alert_history(limit: Optional[int] = 20, state=Depends(get_state)):
    """
    Get alert history.

    Args:
        limit: Maximum number of alerts to return (default 20)

    Returns:
        List of recent alerts with details
    """
    manager = get_manager()
    alerts = manager.get_history(limit=limit)

    return {
        "alerts": [alert.to_dict() for alert in alerts]
    }


class TestAlertRequest(BaseModel):
    """Request to send a test alert."""
    channel: str  # "email" or "webhook"


@router.post("/alerts/test")
async def test_alert(request: TestAlertRequest, state=Depends(get_state)):
    """
    Send a test alert through specified channel.

    Args:
        request: Test alert request with channel type

    Returns:
        Success status and any error messages
    """
    manager = get_manager()

    # Create test alert
    channel_type = ChannelType.EMAIL if request.channel == "email" else ChannelType.WEBHOOK

    try:
        alerts = await manager.trigger_alert(
            trigger_type=AlertTrigger.CUSTOM,
            severity=AlertSeverity.LOW,
            title="Test Alert",
            message=f"This is a test alert sent via {request.channel}. If you received this, your {request.channel} channel is configured correctly!",
            context={"test": True, "timestamp": datetime.now().isoformat()},
        )

        if alerts:
            alert = alerts[0]
            return {
                "success": alert.delivered is not None,
                "message": "Test alert sent successfully" if alert.delivered else "Test alert created but delivery failed",
                "errors": alert.delivery_errors,
            }
        else:
            return {
                "success": False,
                "message": f"No alert rules configured for {request.channel}",
                "errors": [],
            }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Failed to send test alert: {str(exc)}",
            "errors": [str(exc)],
        }
