from datetime import datetime, timedelta
from temod.base.condition import *
from temod.base.attribute import *
import json


class ServiceFileLoader(object):

	def get(*args,**kwargs):
		return ServiceFile(Service.storage.get(*args,**kwargs),None)

	def list(*args,**kwargs):
		return (ServiceFile(service,None) for service in Service.storage.list(*args,**kwargs))

	def create(file, *args,**kwargs):
		Service.storage.create(file.service)
		return file

	def updateOnSnapshot(file, *args,**kwargs):
		return Service.storage.updateOnSnapshot(file.service, *args,**kwargs)

	def update(*args,**kwargs):
		return Service.storage.update(*args,**kwargs)

	def delete(file, *args,**kwargs):
		return Service.storage.delete(service_id=file.service_id,**kwargs)

	def count(*args,**kwargs):
		return Service.storage.count(*args,**kwargs)
		

class ServiceFile(object):
	"""docstring for ServiceFile"""
	storage = ServiceFileLoader

	def __init__(self, service, file, load_checks=True):
		super(ServiceFile, self).__init__()
		self.service = service
		self.file = file
		for attribute,value in self.service.attributes.items():
			setattr(self,attribute,value.value)
		if load_checks:
			self.load()

	def calculate_uptime(self):
		successful = sum(1 for check in self.checks if check['status'].name == "healthy")
		return (successful / len(self.checks)) * 100 if self.checks else 100

	def load(self):
		self.checks = sorted(HealthCheck.storage.list(
			Superior(DateTimeAttribute("timestamp",value=datetime.now() - timedelta(days=7))),
			service_id=self.service_id,
			limit=1000
		),key = lambda x:x['timestamp'])

	@property
	def avg_response_time(self):
		success_check = [check['response_time'] for check in self.checks if check['status'].name == "healthy"]
		if len(success_check):
			return (sum(success_check) / len(success_check))
		return None

	@property
	def specifics(self):
		if not hasattr(self,"_specifics"):
			self._specifics = json.loads(self.service['details'])
		return self._specifics

	@property
	def latest_check(self):
		if not hasattr(self,"_latest_check"):
			self._latest_check = self.checks[-1] if len(self.checks) else None
		return self._latest_check

	@property
	def current_status(self):
		try:
			return (False if self.latest_check['status'].name == "unhealthy" else None) if (self.latest_check['timestamp'] < datetime.now()-timedelta(seconds=self.check_interval+300)) else self.latest_check['status'].name == "healthy"
		except:
			import traceback
			traceback.print_exc()
			return None

	@property
	def uptime(self):
		if not hasattr(self,"_uptime"):
			self._uptime = self.calculate_uptime() if self.checks else 0
		return self._uptime

	@property
	def error_logs(self):
		if not hasattr(self,"_error_logs"):
			self._error_logs = [
				{"timestamp": hc['timestamp'], "message": hc['error_message']}
				for hc in self.checks if hc['status'].name != "healthy"
			]
		return self._error_logs

	def to_dict(self):
		dct = self.service.to_dict()
		dct.update({
			"health_checks":[check.to_dict() for check in self.checks],
			"uptime": self.uptime,
			"avg_response_time": self.avg_response_time
		})
		return dct


	