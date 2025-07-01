# ** Section ** Imports
from temod.base.entity import Entity
from temod.base.attribute import *
from copy import deepcopy
# ** EndSection ** Imports


# ** Section ** Entity_Bostagi
class WatchTower(Entity):
	ENTITY_NAME = "watchtower"
	ATTRIBUTES = [
		{"name":"version","type":StringAttribute, "max_length":20, "required":True,"is_id":True,"non_empty":True,"is_nullable":False},
	]
# ** EndSection ** Entity_Bostagi


# ** Section ** Entity_Job
class Job(Entity):
	ENTITY_NAME = "job"
	ATTRIBUTES = [
		{"name":"name","type":StringAttribute,"max_length":50, "required":True,"is_id":True,"is_nullable":False},
		{"name":"state","type":StringAttribute,"max_length":20, "is_nullable":False, "default_value": "IDLE"},
		{"name":"last_exit_code","type":IntegerAttribute}
	]
# ** EndSection ** Entity_Job


# ** Section ** Entity_Language
class Language(Entity):
	ENTITY_NAME = "language"
	ATTRIBUTES = [
		{"name":"code","type":StringAttribute,"max_length":10, "required":True,"is_id":True,"is_nullable":False},
		{"name":"name","type":StringAttribute,"max_length":30,"is_nullable":False}
	]
# ** EndSection ** Entity_Language
