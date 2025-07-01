from temod.storage.mysql import MysqlEntityStorage
from subprocess import Popen, PIPE, STDOUT
from pathlib import Path
from uuid import uuid4 

import sys
import os

if not os.getcwd() in sys.path:
	sys.path.append(os.getcwd())

from install import common_funcs
from core.entity import *

import mysql.connector
import traceback
import argparse
import toml
import re


APP_VERSION = "1.0.0"


def search_existing_database(credentials):
	try:
		connexion = mysql.connector.connect(**credentials)
	except:
		LOGGER.error("Can't connect to the specified database using these credentials. Verify the credentials and the existence of the database.")
		LOGGER.error(traceback.format_exc())
		sys.exit(1)

	cursor = connexion.cursor()
	cursor.execute('show tables;')

	try:
		return len(cursor.fetchall()) > 0
	except:
		raise
	finally:
		cursor.close()
		connexion.close()


def confirm_database_overwrite():
	print(); common_funcs.print_decorated_title("! DANGER"); print()
	LOGGER.info("The specified database already exists and is not empty. This installation script will erase all the database content and overwrite it with a clean one.")
	rpsn = input("Continue the installation (y/*) ?").lower()
	return rpsn == "y"

def is_valid_email(email):
    """
    Check if the provided string is a valid email address syntax.
    
    Args:
        email (str): The email address to validate
        
    Returns:
        bool: True if the email syntax is valid, False otherwise
    """
    # Regular expression for email validation (RFC 5322 compliant)
    pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
    
    return bool(re.fullmatch(pattern, email))


def ask_for_domain_name():
	rpsn = input("What is the domain name to manage ?").lower()
	if rpsn.startswith("@"):
		rpsn = rpsn[1:]

	if not is_valid_email(f"jhon.doe@{rpsn}"):
		raise Exception(f"Invalid domain name {rpsn}")

	print(f"domain name selected is {rpsn}")
	return rpsn


def ask_for_admin_credentials():
	account_name = ""
	while account_name == "":
		account_name = input("What is the admin account username ?").lower()

	password = ""
	while password == "":
		password = input("What is the admin account password ?")
		if len(password) < 8:
			print("Admin password must be at least 8 chars long")
			password = ""

	cpassword = input("Confirm admin password ?")
	if password != cpassword:
		raise Exception('Passwords do not match')

	return {"username":account_name,"password":password}


def install_preset_objects(credentials, admin_credentials):	

	watchtower = WatchTower(version=APP_VERSION)

	language_en = Language("en","English")
	language_fr = Language("fr","Français")
	language_ar = Language("ar","العربية")

	admin_privilege = Privilege(id=str(uuid4()), label="admin", roles="*")
	admin_user = User(
		id=str(uuid4()),privilege=admin_privilege['id'],email=admin_credentials['username']
	)
	admin_user['password'] = admin_credentials['password']

	HealthCheckerJob = Job(name="HeatlthChecker")

	MysqlEntityStorage(WatchTower,**credentials).create(watchtower)

	languages = MysqlEntityStorage(Language,**credentials)
	languages.create(language_en)
	languages.create(language_fr)
	languages.create(language_ar)

	MysqlEntityStorage(Privilege,**credentials).create(admin_privilege)
	MysqlEntityStorage(User,**credentials).create(admin_user)
	MysqlEntityStorage(Job,**credentials).create(HealthCheckerJob)

	return True


def install_healthcheck_service(root_path, virtual_env, logging_dir, services_dir):
	# Install Overlord service
	with open(os.path.join(root_path,"services","healthchecker","healthchecker.service")) as file:
		service = file.read()
	service = service.replace("$script_path", os.path.join(root_path,"services","healthchecker","healthchecker.sh"))
	if virtual_env is not None:
		service = service.replace("$venv_path", f'-v "{os.path.join(virtual_env,"bin","activate")}"')
	else:
		service = service.replace("$venv_path", "")
	if logging_dir is not None:
		service = service.replace("$logging_dir", f'-l "{logging_dir}"')
	else:
		service = service.replace("$logging_dir", "")
	try:
		with open(os.path.join(services_dir,"healthchecker.service"),"w") as file:
			file.write(service)
		with open(os.path.join(services_dir,"healthchecker.timer"),"w") as file:
			with open(os.path.join(root_path,"services","healthchecker","healthchecker.timer"),"r") as ofile:
				file.write(ofile.read())
	except:
		LOGGER.error(f"Unable to save healthchecker.service file in directory {services_dir}. You can either install the files in another directory with 'install.py -s [DIRECTORY]' or give enough rights to the install script.")
		LOGGER.error("Trace of the exception: ")
		LOGGER.error(traceback.format_exc())
		return False
	return True


def setup(app_paths, args):

	virtual_env = common_funcs.detect_virtual_env(app_paths['root'])
	logging_dir = args.logging_dir if not args.quiet else None
	if not install_healthcheck_service(app_paths['root'], virtual_env, logging_dir, args.services_dir):
		return False

	admin_credentials = ask_for_admin_credentials()
	credentials = common_funcs.get_mysql_credentials()

	already_created = search_existing_database(credentials)
	if already_created:
		if not confirm_database_overwrite():
			LOGGER.warning("If you which to just update the app, run the script install/update.py")
			return False

	with open(app_paths['mysql_schema_file']) as file:
		if not common_funcs.execute_mysql_script(credentials, file.read().replace("$database",credentials['database'])):
			return False

	template_config = common_funcs.load_toml_config(app_paths['template_config_file'])
	template_config['storage']['credentials'].update(credentials)
	common_funcs.save_toml_config(template_config, app_paths['config_file'])

	return install_preset_objects(credentials, admin_credentials)


if __name__ == "__main__":

	print("\n"); width = common_funcs.print_pattern("W.T Server"); print(); print("#"*width); print()

	parser = argparse.ArgumentParser(prog="Installs a WatchTower server")
	parser.add_argument(
		'-l', '--logging-dir', help='Directory where log files will be stored', 
		default=os.path.join("/","var","log","WatchTower")
	)
	parser.add_argument(
		'-s', '--services-dir', 
		help='Directory where WatchTower services files will be stored', 
		default=os.path.join("/","lib","systemd","system")
	)
	parser.add_argument('-q', '--quiet', action="store_true", help='No logging', default=False)
	args = parser.parse_args()

	setattr(__builtins__,'LOGGER', common_funcs.get_logger(args.logging_dir, quiet=args.quiet))
	app_paths = common_funcs.get_app_paths(Path(os.path.realpath(__file__)).parent)

	if not os.path.isfile(app_paths['mysql_schema_file']):
		LOGGER.error("DB schema file not found at",app_paths['mysql_schema_file'])
		sys.exit(1)

	if not os.path.isfile(app_paths['template_config_file']):
		LOGGER.error("Config template file not found at",app_paths['template_config_file'])
		sys.exit(1)

	if setup(app_paths, args):
		LOGGER.info("WatchTower setup completed successfully")
	else:
		LOGGER.error("Error while installing Over")
		exit(1)