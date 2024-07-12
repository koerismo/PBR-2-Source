from .core.io.qtio import QtIOBackend
from .core.io.image import Image
from . import gui

def init():
	Image.set_backend(QtIOBackend)
	gui.start_gui()
