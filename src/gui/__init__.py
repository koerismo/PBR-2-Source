from pathlib import Path
from typing import Optional
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtGui import QImage
from .backend import CoreBackend

class MainWindow( QMainWindow ):
	backend: CoreBackend

	def __init__(self, backend: CoreBackend) -> None:
		super().__init__()

		self.backend = backend
		self.setWindowTitle('PBR-2-Source V2')
		self.resize(600, 350)
		
		root = QVBoxLayout()

		inner = QHBoxLayout()
		root.addLayout(inner)

		left = QVBoxLayout()
		inner.addLayout(left)

		right = QVBoxLayout()
		inner.addLayout(right)

		footer = QHBoxLayout()
		root.addLayout(footer)

	