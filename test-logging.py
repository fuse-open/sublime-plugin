# import os
# import logging
# import logging.handlers

# print os.name

# def log_file():
#     return os.path.join(
#         os.path.join(os.getenv("HOME"), ".fuse") if os.name == "posix" else os.getenv("LOCALAPPDATA"),
#         "logs",
#         "fuse.sublimeplugin.log")

# handler = logging.handlers.RotatingFileHandler(log_file(), maxBytes=1000, backupCount=5)
# handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s [%(process)d:%(thread)d] %(levelname)s %(name)s - %(message)s')
# handler.setFormatter(formatter)

# log1 = logging.getLogger("foo")
# log1.addHandler(handler)
# log1.warn("log1")
# log2 = logging.getLogger("foo.bar")
# log2.warn("log2")
# log3 = logging.getLogger("bar")
# log3.warn("log2")
