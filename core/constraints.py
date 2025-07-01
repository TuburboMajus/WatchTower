from temod.base.constraint import *
from .entity import *


############## USER ###################
class CSTR_USER_PRIVILEGE(EqualityConstraint):
	ATTRIBUTES = [
		{"name":"id","entity":Privilege},
		{"name":"privilege","entity":User},
	]