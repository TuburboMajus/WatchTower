from flask import Response, current_app, render_template, request, redirect, url_for, abort, session,g
from flask_login import LoginManager, login_required, current_user

from temod_flask.utils.content_readers import body_content
from temod_flask.utils.content_writers import dictifier

from temod_flask.blueprint import MultiLanguageBlueprint
from temod_flask.blueprint.utils import Paginator

from temod.base.condition import Not, In, Equals
from temod.base.attribute import *

from core.object.service import ServiceFile

from front.renderers.normal_user import NormalUserTemplate

from datetime import datetime, date, timedelta
from pathlib import Path

import traceback
import json



monitoring_bp = MultiLanguageBlueprint('monitoring_bp', __name__, load_in_g=True, default_config={
    "templates_folder": "{language}/monitoring",
    "refresh_interval": 30000,  # 30 seconds
    "check_history_limit": 100,
    "critical_threshold": 95  # % uptime considered critical
}, dictionnary_selector=lambda lg: lg['code'])



@monitoring_bp.split_route({
    "/api/v1.0/": lambda x,y:{"status":x,"data":dictifier(y)},
    "/": lambda x,y: Response(status=x, response=NormalUserTemplate(
        Path(monitoring_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath("list.html"),
        **y
    ).handles_success_and_error().with_sidebar("monitoring").with_dictionnary().with_navbar().render())
})
@login_required
@monitoring_bp.with_dictionnary
def monitoring_dashboard():
    # Get all services with latest health check
    services = list(ServiceFile.storage.list())
    
    # Calculate global stats
    uptime_stats = {
        "global": sum(s.uptime for s in services) / len(services) if services else 100,
        "critical_count": sum(1 for s in services if s.uptime < monitoring_bp.configuration["critical_threshold"])
    }
    
    # Check for critical alerts
    critical_alerts = []; """list(Alert.storage.list(
        status="active",
        severity="critical",
        limit=5,
        orderby="created_at DESC"
    ))"""

    return 200, {"services":services, "uptime_stats": uptime_stats, "critical_alerts": critical_alerts, "refresh_interval": monitoring_bp.configuration["refresh_interval"]}


@monitoring_bp.split_route({
    "/api/v1.0/monitor/<int:service_id>": lambda x,y:{"status":x,"data":dictifier(y)},
    "/monitor/<int:service_id>": lambda x,y: Response(status=x, response=NormalUserTemplate(
        Path(monitoring_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath("view.html"),service=y
    ).handles_success_and_error().with_sidebar("monitoring").with_dictionnary().with_navbar().render())
})
@login_required
@monitoring_bp.with_dictionnary
def service_details(service_id):
    service = ServiceFile.storage.get(service_id=service_id)
    if not service:
        return abort(404)

    return 200, service


@monitoring_bp.route("/service/<int:service_id>/force-check", methods=['POST'])
@login_required
#@roles_required('admin')
def force_service_check(service_id):
    service = Service.storage.get(id=service_id)
    if not service:
        return abort(404)
    
    # Trigger immediate check (implementation depends on your system)
    result = trigger_immediate_check(service)
    
    return {
        "status": "success" if result else "error",
        "check_id": result.check_id if result else None,
        "message": "Check initiated" if result else "Failed to trigger check"
    }


@monitoring_bp.route("/service/<int:service_id>/export/<string:format>")
@login_required
def export_service_data(service_id, format):
    if format not in ['csv', 'json']:
        return abort(400)
    
    checks = list(HealthCheck.storage.list(service_id=service_id))
    
    if format == 'csv':
        csv_data = generate_monitoring_csv(checks)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=service_{service_id}_checks.csv"}
        )
    else:
        return jsonify([check.to_dict() for check in checks])


def generate_monitoring_csv(checks):
    # Implement CSV generation based on your needs
    pass