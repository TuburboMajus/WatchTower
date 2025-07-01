from temod.base.entity import Entity
from temod.base.attribute import *

class HealthCheck(Entity):
    ENTITY_NAME = "HealthCheck"
    ATTRIBUTES = [
        {"name":"check_id","type":IntegerAttribute,"required":True,"is_id":True,"is_auto":True,"is_nullable":False},
        {"name":"service_id","type":IntegerAttribute,"required":True,"is_nullable":False},
        {"name":"timestamp","type":DateTimeAttribute,"required":True,"default_value":"CURRENT_TIMESTAMP","is_nullable":False},
        {"name":"status","type":EnumAttribute,"values":["healthy","unhealthy","unknown"],"required":True,"is_nullable":False},
        {"name":"response_time","type":RealAttribute,"min":0},
        {"name":"error_message","type":StringAttribute}
    ]