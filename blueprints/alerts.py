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


alerts_bp = MultiLanguageBlueprint('alerts_bp', __name__, default_config={
    "templates_folder": "{language}/alerts",
    "alerts_per_page": 25,
    "priority_levels": {
        "critical": 1,
        "warning": 2,
        "notice": 3
    },
    "default_filters": {
        "status": "unresolved",
        "timeframe": "24h"
    }
}, dictionnary_selector=lambda lg: lg['code'])

@alerts_bp.route("/alerts", methods=['GET', 'POST'])
@login_required
@alerts_bp.with_dictionnary
def alert_center():
    # Get user's notification preferences
    preferences = NotificationPreference.storage.get(user_id=current_user.id) or {}
    
    # Handle alert actions (acknowledge/mute)
    if request.method == 'POST':
        action = request.form.get('action')
        alert_id = request.form.get('alert_id')
        
        if action and alert_id:
            alert = Alert.storage.get(id=alert_id)
            if alert:
                if action == "acknowledge":
                    alert.status = "acknowledged"
                    alert.acknowledged_by = current_user.id
                    alert.acknowledged_at = datetime.now()
                elif action == "mute":
                    alert.status = "muted"
                    alert.muted_until = datetime.now() + timedelta(hours=8)
                
                Alert.storage.update(alert)
    
    # Parse filters
    filters = {
        "status": request.args.get('status', alerts_bp.configuration["default_filters"]["status"]),
        "timeframe": request.args.get('timeframe', alerts_bp.configuration["default_filters"]["timeframe"]),
        "service_type": request.args.get('service_type'),
        "priority": request.args.get('priority')
    }
    
    # Build query
    query = {}
    
    # Status filter
    if filters["status"] == "unresolved":
        query["status"] = {"$in": ["active", "new"]}
    elif filters["status"] != "all":
        query["status"] = filters["status"]
    
    # Timeframe filter
    if filters["timeframe"] == "24h":
        query["created_at"] = {">=": datetime.now() - timedelta(hours=24)}
    elif filters["timeframe"] == "7d":
        query["created_at"] = {">=": datetime.now() - timedelta(days=7)}
    
    # Service type filter
    if filters["service_type"]:
        services = list(Service.storage.list(type=filters["service_type"]))
        query["service_id"] = {"$in": [s.id for s in services]}
    
    # Priority filter
    if filters["priority"]:
        query["severity"] = filters["priority"]
    
    # Get alerts (sorted by priority then recency)
    alerts = list(Alert.storage.list(
        **query,
        orderby=["severity ASC", "created_at DESC"]
    ))
    
    # Get notification history
    notification_history = list(Notification.storage.list(
        alert_id={"$in": [a.id for a in alerts]},
        limit=50,
        orderby="sent_at DESC"
    )) if alerts else []
    
    # Get all services for filter dropdown
    services = list(Service.storage.list(is_active=True))
    
    return NormalUserTemplate(
        Path(alerts_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath("alerts.html"),
        alerts=alerts,
        services=services,
        notification_history=notification_history,
        filters=filters,
        priority_levels=alerts_bp.configuration["priority_levels"],
        user_preferences=preferences,
        segment='alerts'
    ).handles_success_and_error().with_sidebar("alerts").with_dictionnary().with_navbar().render()

@alerts_bp.route("/alerts/<int:alert_id>/notify", methods=['POST'])
@login_required
#@roles_required('admin')
def resend_notification(alert_id):
    alert = Alert.storage.get(id=alert_id)
    if not alert:
        return abort(404)
    
    # Trigger notification (implementation depends on your system)
    result = trigger_notification(alert, current_user)
    
    return {
        "status": "success" if result else "error",
        "notification_id": result.id if result else None
    }

@alerts_bp.route("/alerts/preferences", methods=['POST'])
@login_required
@body_content('json')
def update_preferences(data):
    pref = NotificationPreference.storage.get(user_id=current_user.id) or NotificationPreference(
        id=NotificationPreference.storage.generate_value('id'),
        user_id=current_user.id
    )
    
    pref.methods = data.get('methods', [])
    pref.working_hours = data.get('working_hours', {})
    pref.alert_types = data.get('alert_types', {})
    
    if pref.id:
        NotificationPreference.storage.update(pref)
    else:
        NotificationPreference.storage.create(pref)
    
    return {"status": "success"}

def trigger_notification(alert, user):
    """Send notification based on user preferences"""
    # Implementation depends on your notification system
    pass