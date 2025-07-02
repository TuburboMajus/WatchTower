from temod.storage.directory import DirectoryStorage
from temod.storage import MysqlEntityStorage

from temod.base.condition import *
from temod.base.attribute import *

from datetime import datetime, timedelta
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import traceback
import requests
import argparse
import logging
import toml
import time
import json
import sys
import os


HEALTHCHECKER_JOB_NAME = "HeatlthChecker"
HEALTHCHECKER_LOG_NAME = "heatlthchecker"


def load_configs(root_dir):
	with open(os.path.join(root_dir,"config.toml")) as config_file:
		config = toml.load(config_file)
	return config


def get_logger(logging_dir):
	os.makedirs(logging_dir, exist_ok=True)

	logger = logging.getLogger()
	logger.setLevel(logging.INFO)

	if logger.handlers:
		return logger

	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

	if logging_dir is not None and os.path.isdir(logging_dir):
		fh = logging.RotatingFileHandler(
			os.path.join(logging_dir,f"{HEALTHCHECKER_LOG_NAME}.log"),
			maxBytes=5*1024*1024,  # 5MB
			backupCount=3,
			encoding='utf-8'
		) 
		fh.setLevel(logging.INFO)
		fh.setFormatter(formatter)
		logger.addHandler(fh)
	else:
		print("No valid logging directory specified. No logs will be kept.")

	dh = logging.StreamHandler(sys.stdout)
	dh.setLevel(logging.WARNING)
	dh.setFormatter(formatter)
	logger.addHandler(dh)

	return logger



class HealthCheckException(Exception):
	pass

class NoNeedForCheck(Exception):
	pass
		
		

class HealthChecker(object):

	"""docstring for HealthChecker"""
	def __init__(self, **mysql_credentials):
		super(HealthChecker, self).__init__()
		self.mysql_credentials = mysql_credentials
		self.storages = {
			"services":MysqlEntityStorage(entities.Service,**mysql_credentials),
			"healthChecks":MysqlEntityStorage(entities.HealthCheck,**mysql_credentials),
		}

	def check_on_webserver(self, service_file):
		scheme = service_file.specifics.get('scheme','http')
		method = service_file.specifics.get('method','get')
		try:
			host = service_file.specifics['host']
		except:
			raise Exception(f"Service(webserver) {service_file.service_id} host is not specified. Health check ignored.")
		port = service_file.specifics.get('port', None)
		path = service_file.specifics.get('path','/')
		try:
			headers = json.loads('{}' if service_file.specifics.get('headers',"") in ['',None] else service_file.specifics['headers'])
		except:
			raise Exception(f"Service(webserver){service_file.service_id} headers are malformed. Health check ignored.")

		url = f"{scheme}://{host}{':'+str(port) if port else ''}{'/'+path if not path.startswith('/') else path}"
		try:
			req = getattr(requests,method)(url, headers=headers)
			if req.status_code >= 400:
				raise HealthCheckException(f"Webserver at {url} is reachable but healthcheck request returned status_code {req.status_code}")
			return "healthy"
		except requests.exceptions.ConnectionError:
			raise HealthCheckException(f"Webserver at {url} is unreachable")
		except:
			raise

	def check_on(self, service_file):
		result = True

		service_file.checks = list(self.storages['healthChecks'].list(
			Superior(DateTimeAttribute("timestamp",value=datetime.now() - timedelta(days=7))),
			service_id=service_file.service_id,
			orderby="timestamp DESC",
			limit=1
		))

		if service_file.latest_check is not None and ((service_file.latest_check['timestamp'] + timedelta(seconds=service_file.check_interval)) > datetime.now()):
			raise NoNeedForCheck()

		start_time = time.time(); error_message = None
		if service_file.service['type'].name == "webserver":
			try:
				health_check = self.check_on_webserver(service_file)
			except HealthCheckException as exc:
				LOGGER.warning(f"Service {service_file.service_id} is unhealthy")
				error_message = str(exc)
				health_check = "unhealthy"
			except:
				LOGGER.error(f"Unexpected error while checking on service {service_file.service_id}. Health check ignored.")
				error_message = traceback.format_exc()
				LOGGER.error(error_message)
				health_check = "unknown"
		else:
			LOGGER.warning(f"Service type {service_file.service['type'].name} not implemented")
			return False

		response_time = time.time()-start_time

		self.storages['healthChecks'].create(entities.HealthCheck(
			check_id=-1,
			service_id=service_file.service_id,
			timestamp=datetime.now(),
			status=health_check,
			response_time=int(response_time*1000),
			error_message=error_message
		))

		return result
		

	def process(self):

		health_checks = []
		checked_on = 0; passed = 0;
		for service in self.storages['services'].list(is_active=True):

			try:
				health_checks.append(self.check_on(ServiceFile(service,None,load_checks=False)))
				checked_on += 1
			except NoNeedForCheck:
				health_checks.append(True)
				passed += 1
			except:
				LOGGER.error(f"Uncaught error treating data while checking on service {service['service_id']}")
				LOGGER.error(traceback.format_exc())
				health_checks.append(False)

		LOGGER.info(f"{checked_on} services were checked, {passed} were passed")
		if len(health_checks) == 0:
			if datetime.now().minute % 10 == 0 and datetime.now().second < 15:
				LOGGER.info("No new data to treat")
			return None

		return all(health_checks)


def already_running(**mysql_credentials):
	HcjoB = MysqlEntityStorage(entities.Job, **mysql_credentials).get(name=HEALTHCHECKER_JOB_NAME)
	if HcjoB['state'] == "RUNNING":
		return True
	return False

def start_run(**mysql_credentials):
	storage = MysqlEntityStorage(entities.Job, **mysql_credentials)
	HcjoB = storage.get(name=HEALTHCHECKER_JOB_NAME).takeSnapshot()
	HcjoB.setAttribute("state","RUNNING")
	storage.updateOnSnapshot(HcjoB)

def stop_run(exit_code, **mysql_credentials):
	storage = MysqlEntityStorage(entities.Job, **mysql_credentials)
	HcjoB = storage.get(name=HEALTHCHECKER_JOB_NAME).takeSnapshot()
	HcjoB.setAttribute("state","IDLE")
	HcjoB.setAttribute("last_exit_code",exit_code)
	storage.updateOnSnapshot(HcjoB)
	if exit_code != 0:
		sys.exit(exit_code)

def launch(config):
	if already_running(**config["storage"]["credentials"]):
		LOGGER.info("HeatlthChecker job is already ongoing. Postponing execution.")
		return
	start_run(**config["storage"]["credentials"])

	heatlhchecker = HealthChecker(**config["storage"]["credentials"])

	results = heatlhchecker.process()	
	exit_code=0	
	if results is not None:
		if results:
			LOGGER.info("All healthchecks were successful.")
		else:
			LOGGER.warning("Some healthchecks weren't successful.")
			exit_code=2
	return exit_code


if __name__ == "__main__":
	""" Defining and parsing args """
	parser = argparse.ArgumentParser(prog="Actively queries health checks from registered services")

	parser.add_argument('-r', '--root-dir', help='HeatlthCHEcker root directory', default=".")
	parser.add_argument('-l', '--logging-dir', help='Directory where to store logs.', default=None)

	args = parser.parse_args()

	if args.root_dir:
		if not os.path.isdir(args.root_dir):
			print(f"Root directory path must be a valid directory.")
			sys.exit(1)
		if not args.root_dir in sys.path:
			sys.path.append(args.root_dir)
	else:
		sys.exit(1)

	setattr(__builtins__,'LOGGER', get_logger(args.logging_dir))
	
	from core.object.service import ServiceFile
	import core.entity as entities

	config = load_configs(args.root_dir)

	try:
		exit_code = launch(config)
	except:
		LOGGER.error("HeatlthChecker failed with error. Traceback:")
		LOGGER.error(traceback.format_exc())
		stop_run(1,**config["storage"]["credentials"])
	else:
		stop_run(exit_code,**config["storage"]["credentials"])