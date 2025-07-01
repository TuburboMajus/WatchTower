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


admin_bp = MultiLanguageBlueprint('admin_bp', __name__, load_in_g=True, default_config={
    "templates_folder": "{language}/admin",
    "service_types": ["web", "database", "queue", "cache", "monitoring"],
    "check_intervals": [30, 60, 300, 900],  # seconds
    "default_check_interval": 60,
    "max_services": 100
}, dictionnary_selector=lambda lg: lg['code'])


@admin_bp.route("/admin", methods=['GET', 'POST'])
@login_required
@admin_bp.with_dictionnary
def admin_panel():
    form = ServiceForm()
    
    # Handle CRUD operations
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == "create":
            if form.validate_on_submit():
                # Check for duplicate service names
                if Service.storage.exists(name=form.name.data):
                    flash("Service name already exists", "error")
                else:
                    service = Service(
                        id=Service.storage.generate_value('id'),
                        name=form.name.data,
                        type=form.type.data,
                        endpoint=form.endpoint.data,
                        check_interval=form.check_interval.data,
                        is_active=form.is_active.data,
                        created_by=current_user.id,
                        created_at=datetime.now()
                    )
                    Service.storage.create(service)
                    log_audit("create", f"Created service {service.name}")
                    flash("Service created successfully", "success")
        
        elif action == "update":
            service_id = request.form.get('service_id')
            service = Service.storage.get(id=service_id)
            if service and form.validate_on_submit():
                original_data = service.to_dict()
                service.update(
                    name=form.name.data,
                    type=form.type.data,
                    endpoint=form.endpoint.data,
                    check_interval=form.check_interval.data,
                    is_active=form.is_active.data,
                    updated_at=datetime.now()
                )
                Service.storage.update(service)
                log_audit("update", f"Updated service {service.name}", original_data)
                flash("Service updated successfully", "success")
        
        elif action == "delete":
            service_id = request.form.get('service_id')
            service = Service.storage.get(id=service_id)
            if service:
                Service.storage.delete(service)
                log_audit("delete", f"Deleted service {service.name}")
                flash("Service deleted successfully", "success")
        
        elif action == "test":
            service_id = request.form.get('service_id')
            service = Service.storage.get(id=service_id)
            if service:
                result = test_service_connection(service)
                flash(f"Connection test {'succeeded' if result else 'failed'}", "success" if result else "error")
    
    # Get all services
    services = list(Service.storage.list(limit=admin_bp.configuration["max_services"]))
    
    # Get recent audit logs
    audit_logs = list(AuditLog.storage.list(
        action={"$in": ["create", "update", "delete"]},
        limit=50,
        orderby="timestamp DESC"
    ))
    
    return NormalUserTemplate(
        Path(admin_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath("admin_panel.html"),
        services=services,
        service_types=admin_bp.configuration["service_types"],
        check_intervals=admin_bp.configuration["check_intervals"],
        audit_logs=audit_logs,
        form=form,
        segment='admin'
    ).handles_success_and_error().with_sidebar("admin").with_dictionnary().with_navbar().render()


@admin_bp.route("/admin/service/<int:service_id>", methods=['GET'])
@login_required
def get_service(service_id):
    service = Service.storage.get(id=service_id)
    if not service:
        return abort(404)
    return jsonify(service.to_dict())


@admin_bp.route("/admin/bulk-update", methods=['POST'])
@login_required
@body_content('json')
def bulk_update(data):
    try:
        updates = data.get('updates', [])
        results = []
        
        for update in updates:
            service = Service.storage.get(id=update['id'])
            if service:
                original_data = service.to_dict()
                service.update(**update['fields'])
                Service.storage.update(service)
                log_audit("bulk_update", f"Bulk updated service {service.name}", original_data)
                results.append({"id": service.id, "status": "success"})
            else:
                results.append({"id": update.get('id'), "status": "not_found"})
        
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


def test_service_connection(service):
    """Test connection to a service endpoint"""
    # Implementation depends on your service types
    try:
        if service.type == "web":
            response = requests.get(service.endpoint, timeout=5)
            return response.status_code < 400
        elif service.type == "database":
            # Implement database connection test
            return True
        # Add other service type checks
        return False
    except:
        return False

def log_audit(action, description, original_data=None):
    AuditLog.storage.create(AuditLog(
        id=AuditLog.storage.generate_value('id'),
        user_id=current_user.id,
        action=action,
        description=description,
        original_data=original_data,
        timestamp=datetime.now()
    ))