import logging

LOGGER = logging.getLogger("PyCloudSim")
LOGGER.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
LOGGER.addHandler(stream_handler)

file_handler = logging.FileHandler(filename=".log", mode="w")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
LOGGER.addHandler(file_handler)