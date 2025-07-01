from temod.base.entity import Entity
from temod.base.attribute import *

class AlertSubscription(Entity):
    ENTITY_NAME = "AlertSubscription"
    ATTRIBUTES = [
        {"name":"user_id","type":IntegerAttribute,"required":True,"is_id":True,"is_nullable":False},
        {"name":"service_id","type":IntegerAttribute,"required":True,"is_id":True,"is_nullable":False},
        {"name":"created_at","type":DateTimeAttribute,"default_value":"CURRENT_TIMESTAMP"}
    ]