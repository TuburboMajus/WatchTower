from temod.base.entity import Entity
from temod.base.attribute import *

class Service(Entity):
    ENTITY_NAME = "Service"
    ATTRIBUTES = [
        {"name":"service_id","type":IntegerAttribute,"required":True,"is_id":True,"is_auto":True,"is_nullable":False},
        {"name":"name","type":StringAttribute,"max_length":100,"required":True,"is_nullable":False},
        {"name":"type","type":EnumAttribute,"values":["webserver","database","program"],"required":True,"is_nullable":False},
        {"name":"details","type":StringAttribute,"max_length":2000, "required":True,"is_nullable":False},
        {"name":"check_interval","type":IntegerAttribute,"required":True,"min":1,"is_nullable":False},
        {"name":"is_active","type":BooleanAttribute,"required":True,"default_value":True,"is_nullable":False},
        {"name":"created_at","type":DateTimeAttribute},
        {"name":"updated_at","type":DateTimeAttribute}
    ]