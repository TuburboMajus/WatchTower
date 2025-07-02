from flask import Response, current_app, render_template, request, redirect, url_for, abort, g
from flask_login import login_required, current_user

from temod_flask.utils.content_readers import body_content
from temod_flask.utils.content_writers import dictifier

from temod_flask.blueprint import MultiLanguageBlueprint
from temod_flask.blueprint.utils import Paginator

from temod.base.condition import Equals, Superior
from temod.base.attribute import *

from front.renderers.normal_user import NormalUserTemplate
from core.object.service import ServiceFile

from datetime import datetime
from pathlib import Path
import json


services_bp = MultiLanguageBlueprint('services', __name__, load_in_g=True, default_config={
    "templates_folder": "{language}/services",
    "services_per_page": 10,
}, dictionnary_selector=lambda lg: lg['code'])

UPDATABLE_FIELDS = ["name", "details", "check_interval", "is_active"]
DEFAULTS = {
    "webserver":{"method":"get","scheme":"http","path":"/","headers":"{}", "check_interval":60}
}

def select_services(dct):
    if 'type' in dct:
        return Equals(StringAttribute('type'), value=dct['type'])
    return None

def order_services(dct):
    if 'order_by' in dct:
        return dct['order_by']
    return "created_at"

@services_bp.split_route({
    "/api/v1.0/services": lambda x,y:y.to_dict(translator={"current":"data"}),
    "/services": lambda x,y: Response(status=x, response=NormalUserTemplate(
        Path(services_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath("list.html"),
        pagination=y
    ).handles_success_and_error().with_sidebar("services").with_dictionnary().with_navbar().render())
})
@login_required
@services_bp.with_dictionnary
@Paginator(services_bp, page_size_config="services_per_page").for_entity(ServiceFile).with_filter(
    lambda x: select_services(x)
).orderby(
    lambda x: order_services(x)
).paginate
def listServices(pagination):
    return 200, pagination


@services_bp.route('/service')
@login_required
@services_bp.with_dictionnary
def newService():
    return NormalUserTemplate(
        Path(services_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath("new.html")
    ).handles_success_and_error().with_sidebar("services").with_dictionnary().with_navbar().render()

@services_bp.route('/service_type/<string:service_type>')
@login_required
@services_bp.with_dictionnary
def getServiceTypeForm(service_type):
    return NormalUserTemplate(
        Path(services_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath(f"types/{service_type}.html"),
        details=DEFAULTS.get(service_type,{})
    ).with_dictionnary().render()

@services_bp.split_route({
    "/api/v1.0/service": lambda x,y:{"status":x[0],"data":x[1].to_dict(translate={"current":"data"})},
    "/service": lambda x,y: redirect("/services")
},methods=['POST'])
@login_required
@body_content('json')
def createService(form):
    service = ServiceFile(Service(
        service_id=-1,
        name=form['name'],
        type=form['type'],
        details=json.dumps(form.get('details',{})),
        check_interval=int(form['check_interval']),
        is_active=form.get('is_active')
    ),None)
    ServiceFile.storage.create(service)
    return 200, service.to_dict()

@services_bp.split_route({
    "/api/v1.0/service/<int:service_id>": lambda status,data:{"status":status,"data":data.to_dict()},
    "/service/<int:service_id>": lambda status,data: Response(status=status, response=NormalUserTemplate(
        Path(services_bp.configuration["templates_folder"].format(language=g.language['code'])).joinpath("view.html"),
        service=data
    ).handles_success_and_error().with_sidebar("services").with_dictionnary().with_navbar().render())
})
@login_required
@services_bp.with_dictionnary
def viewService(service_id):
    service = ServiceFile.storage.get(service_id=service_id)
    if service is None:
        return abort(404)

    return 200, service

@services_bp.route('/service/<int:service_id>', methods=["PUT", "PATCH"])
@login_required
@body_content('json')
def updateService(form, service_id):
    file = ServiceFile.storage.get(service_id=service_id)
    if file is None:
        return abort(404)

    file.service.takeSnapshot().setAttributes(
        **{field: (json.dumps(form.get(field, json.loads(file.service[field]))) if field == "details" else form.get(field, file.service[field])) for field in UPDATABLE_FIELDS}
    )
    Service.storage.updateOnSnapshot(file.service)
    return {"status":"updated", "data":file.to_dict()}

@services_bp.route('/service/<int:service_id>', methods=["DELETE"])
@login_required
def deleteService(service_id):
    file = ServiceFile.storage.get(service_id=service_id)
    if file is None:
        return abort(404)

    ServiceFile.storage.delete(file)
    return {"status":"deleted", "data":file.to_dict()}