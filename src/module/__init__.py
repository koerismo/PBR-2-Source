def init():
	from .core.io.qtio import QtIOBackend
	from .core.io.image import Image
	from . import gui
	
	from logging import DEBUG, basicConfig, FileHandler, root
	basicConfig(level=DEBUG)

	from argparse import ArgumentParser

	parser = ArgumentParser()
	parser.add_argument('--logfile', help='Writes errors and information to the specified file.')
	parser.add_argument('--config', help='Uses the specified config path instead of the installation config path.')
	args = parser.parse_args()

	if args.logfile != None:
		from .core.config import root_path
		root.addHandler(FileHandler(root_path / args.logfile))

	Image.set_backend(QtIOBackend)
	gui.start_gui(args)
