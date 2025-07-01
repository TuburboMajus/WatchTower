from flask import Blueprint, Flask, Response, request, render_template, redirect, session, url_for
from flask_login import login_required,login_user,logout_user,current_user

from temod_flask.security.authentification import Authenticator, TemodUserHandler
from temod.ext.holders import init_holders

from subprocess import Popen, PIPE, STDOUT

from context import *

import importlib
import traceback
import mimetypes
import logging
import random
import yaml
import toml
import json
import time
import sys
import os

LANGUAGES = [{"code":"en","name":"English"},{"code":"fr","name":"Français"},{"code":"ar","name":"العربية"}]


# ** Section ** MimetypesDefinition
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/css', '.min.css')
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/javascript', '.min.js')
# ** EndSection ** MimetypesDefinition


# ** Section ** LoadConfiguration
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.toml")) as config_file:
    config = toml.load(config_file)

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"dictionnary.yml")) as dictionnary_file:
    dictionnary = yaml.safe_load(dictionnary_file.read())
# ** EndSection ** LoadConfiguration


# ** Section ** ContextCreation
init_holders(
    entities_dir=os.path.join(config['temod']['core_directory'],r"entity"),
    joins_dir=os.path.join(config['temod']['core_directory'],r"join"),
    databases=config['temod']['bound_database'],
    db_credentials=config['storage']['credentials'],
)
init_context(config)
# ** EndSection ** ContextCreation

# ** Section ** AppCreation
def update_configuration(original_config, new_config):
    new_keys = set(new_config).difference(set(original_config))
    common_keys = set(new_config).intersection(set(original_config))
    for k in common_keys:
        if type(original_config[k]) is dict and type(new_config[k]) is not dict:
            raise Exception("Unmatched config type")
        if type(original_config[k]) is dict:
            update_configuration(original_config[k],new_config[k])
        else:
            original_config[k] = new_config[k]
    for k in new_keys:
        original_config[k] = new_config[k]


def register_plugins_blueprints(app, **config):
    blueprints_file = os.path.join("blueprints","__init__.py")
    if not os.path.isfile(blueprints_file):
        print(f"Cannot load blueprints from plugin {plugin}: No __init__.py file located in the blueprints directory at {blueprints_directory}")
        return

    spec = importlib.util.spec_from_file_location(f"blueprints", blueprints_file)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        for content in dir(module):
            if content.startswith('auth'):
                continue
            try:
                e = getattr(module,content)
                if issubclass(type(e),Blueprint):
                    app.register_blueprint(e.setup(config.get(module,{})))
                    print(f"Blueprint {e} has been registered successfully")
            except:
                print(f"Error while registering module {content} from {blueprints_file}")
    except:
        print(f"Error while registering blueprint from {blueprints_file}")
        traceback.print_exc()


def register_jinja_filters(app):
    def format_datetime(value, format='medium'):
        """Format a datetime object to a human-readable string"""
        if value is None:
            return ""
        
        if isinstance(value, str):
            # If it's a string, try to parse it to datetime
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return value
        
        if format == 'full':
            format = "%Y-%m-%d %H:%M:%S"
        elif format == 'medium':
            format = "%b %d, %Y %H:%M"
        else:
            format = "%Y-%m-%d"
        
        return value.strftime(format)

    def format_duration(seconds):
        """Convert seconds to a human-readable duration string"""
        if seconds is None:
            return "N/A"
        
        seconds = int(seconds)
        periods = [
            ('year', 60*60*24*365),
            ('month', 60*60*24*30),
            ('day', 60*60*24),
            ('hour', 60*60),
            ('minute', 60),
            ('second', 1)
        ]
        
        parts = []
        for period_name, period_seconds in periods:
            if seconds >= period_seconds:
                period_value, seconds = divmod(seconds, period_seconds)
                plural = 's' if period_value > 1 else ''
                parts.append(f"{period_value} {period_name}{plural}")
        
        if not parts:
            return "0 seconds"
        
        return ", ".join(parts[:2])  # Show max 2 time periods (e.g., "1 day, 3 hours")

    # Register the filters with Jinja2
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['format_duration'] = format_duration


def build_app(**app_configuration):

    update_configuration(config,app_configuration)

    app = Flask(
        __name__,
        template_folder=config['app']['templates_folder'],
        static_folder=config['app']['static_folder']
    )

    secret_key = config['app'].get('secret_key','')
    app.secret_key = secret_key if len(secret_key) > 0 else generate_secret_key(32)
    app.config.update({k:v for k,v in config['app'].items() if not type(v) is dict})
    app.config['LANGUAGES'] = {language["code"]:language for language in LANGUAGES}
    app.config['DICTIONNARY'] = dictionnary

    register_jinja_filters(app)

    # ** Section ** Authentification
    AUTHENTICATOR = Authenticator(TemodUserHandler(
        joins.UserAccount, "mysql", logins=['email'], **config['storage']['credentials']
    ),login_view="auth.login")
    AUTHENTICATOR.init_app(app)
    # ** EndSection ** Authentification

    import blueprints

    auth_blueprint_config = config['app'].get('blueprints',{}).get('auth',{})
    auth_blueprint_config['authenticator'] = AUTHENTICATOR
    app.register_blueprint(blueprints.auth_bp.setup(auth_blueprint_config))

    register_plugins_blueprints(app, **config['app'].get('blueprints',{}))

    # ** Section ** AppMainRoutes
    @app.route('/healthcheck', methods=['GET'])
    def health_check():
        return {"status":"ok"}
    # ** EndSection ** AppMainRoutes

    return app

# ** EndSection ** AppCreation


if __name__ == '__main__':

    app = build_app(**config)

    server_configs = {
        "host":config['app']['host'], "port":config['app']['port'],
        "threaded":config['app']['threaded'],"debug":config['app']['debug']
    }
    if config['app'].get('ssl',False):
        server_configs['ssl_context'] = (config['app']['ssl_cert'],config['app']['ssl_key'])

    app.run(**server_configs)
