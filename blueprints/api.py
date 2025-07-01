from flask import current_app, render_template, request, redirect, url_for, abort, session,g
from flask_login import LoginManager, login_required, current_user

from temod_flask.utils.content_readers import body_content
from temod_flask.blueprint import MultiLanguageBlueprint
from temod_flask.blueprint.utils import Paginator

from temod.base.condition import Not, In, Equals
from temod.base.attribute import *

from front.renderers.normal_user import NormalUserTemplate

from datetime import datetime, date
from pathlib import Path

import traceback
import json


api_bp = MultiLanguageBlueprint('api_bp', __name__, default_config={
    "rate_limit": "100 per hour",
    "required_checks": ["cpu", "memory", "disk"],
    "alert_thresholds": {
        "cpu": 90,
        "memory": 85,
        "disk": 80
    }
})

@api_bp.route("/api/v1/healthcheck", methods=['POST'])
@body_content('json')
#@limiter.limit(api_bp.configuration["rate_limit"])
def health_check(data):
    # Verify API key
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return {"status": "error", "message": "API key required"}, 401
    
    service = Service.storage.get(api_key=api_key, is_active=True)
    if not service:
        return {"status": "error", "message": "Invalid API key"}, 403
    
    # Validate payload structure
    if not all(k in data for k in api_bp.configuration["required_checks"]):
        return {
            "status": "error",
            "message": f"Missing required metrics: {api_bp.configuration['required_checks']}",
            "received": list(data.keys())
        }, 400
    
    # Check for alert conditions
    alerts = []
    for metric, threshold in api_bp.configuration["alert_thresholds"].items():
        if data[metric] > threshold:
            alerts.append({
                "metric": metric,
                "value": data[metric],
                "threshold": threshold
            })
    
    # Create health check record
    check = HealthCheck(
        id=HealthCheck.storage.generate_value('id'),
        service_id=service.id,
        timestamp=datetime.now(),
        metrics=data,
        has_alerts=len(alerts) > 0
    )
    HealthCheck.storage.create(check)
    
    # Trigger alerts if needed
    if alerts:
        trigger_alerts(service, alerts)
    
    return {
        "status": "success",
        "service": service.name,
        "received_at": datetime.now().isoformat(),
        "check_id": check.id,
        "alerts_triggered": len(alerts),
        "next_check_in": "Within 5 minutes"
    }

def trigger_alerts(service, alerts):
    """Send notifications for alert conditions"""
    # Implementation depends on your alerting system
    # Could email, SMS, Slack notification, etc.
    pass