import logging
import logging.handlers
import os

def log():
	configure_logging()
	return logging.getLogger(__name__)

def userdata_dir():
	if os.name == "posix":
		return os.path.join(os.getenv("HOME"), ".fuse")
	else:
		return os.path.join(os.getenv("LOCALAPPDATA"), "Fusetools", "Fuse")

def log_dir():
	return os.path.join(userdata_dir(), "logs")

def log_file():
	return os.path.join(log_dir(), "fuse.sublimeplugin.log")

def ensure_dir_exists(dir):
	try:
		os.makedirs(dir)
	except FileExistsError:
		return
	except Exception as e:
		sublime.error_message("Could not create directory '" + dir + "'. Please make sure you have the correct permissions: " + str(e))

def configure_logging():
	log = logging.getLogger(__name__.split(".")[0])
	if (len(log.handlers) > 0): #Already configured
		return

	print("logging to " + log_file())
	ensure_dir_exists(log_dir())
	handler = logging.handlers.RotatingFileHandler(log_file(), 'a', 500000, 5, "utf-8")
	formatter = logging.Formatter('%(asctime)s [%(process)d] %(levelname)s %(message)s')
	handler.setFormatter(formatter)
	handler.setLevel(logging.INFO)
	log.setLevel(logging.INFO)
	log.addHandler(handler)
	log.info("Finished configuring logging for " + log.name)
	log.info(__name__)

