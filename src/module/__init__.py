def init():
	from .core.io.qtio import QtIOBackend
	from .core.io.image import Image
	from . import gui
	from sys import argv
	
	from logging import DEBUG, basicConfig, getLogger, FileHandler, root
	basicConfig(level=DEBUG)

	if '--logfile' in argv:
		from .config import root_path
		root.addHandler(FileHandler(root_path / 'debug.log'))

	Image.set_backend(QtIOBackend)
	gui.start_gui()
