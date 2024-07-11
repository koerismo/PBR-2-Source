from core.io.qtio import QtIOBackend
from core.io.image import Image
import gui

if __name__ == '__main__':
	# Use the Qt backend for loading and saving files
	Image.set_backend(QtIOBackend)

	gui.start_gui()
