from version import __version__
from config import AppConfig, AppTheme, load_config

from .style import STYLESHEET_TILE_REQUIRED, STYLESHEET
from .backend import CoreBackend, ImageRole
from sys import argv
from traceback import format_exc

from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot, QSize, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QMouseEvent, QImage, QPixmap, QFontDatabase, QColor, QDrag
from PySide6.QtWidgets import (
	QWidget, QFrame, QApplication, QMessageBox,
	QBoxLayout, QHBoxLayout, QVBoxLayout,
	QLabel, QLineEdit, QToolButton,
	QFileDialog, QGroupBox, QProgressBar, QPushButton,
	QSizePolicy
)

from urllib.parse import unquote_plus, urlparse
def uri_to_path(uri: str) -> str:
	return unquote_plus(urlparse(uri).path)


class RClickToolButton( QToolButton ):
	rightClicked = Signal( name='RightClicked' )
	def mouseReleaseEvent(self, e: QMouseEvent) -> None:
		if e.button() == Qt.MouseButton.RightButton: self.rightClicked.emit()
		else: self.clicked.emit()


class PickableImage( QFrame ):
	# TODO: Emit loaded image instead of path to avoid reloading? Maybe use self.icon.toImage()
	picked = Signal( str, Path, object, name='Picked', arguments=['Kind', 'Path', 'ReturnBack'] )
	''' Fires when an image has been picked from the filesystem. (Path|None) '''

	name: str
	kind: str
	required: bool
	path: Path|None = None
	
	path_box: QLineEdit
	iconButton: QToolButton
	icon: QPixmap

	def __init__(self, name: str, kind: str, required: bool, parent: QWidget | None = None, f: Qt.WindowType = Qt.WindowType.Widget) -> None:
		super().__init__(parent, f)
		self.name = name
		self.kind = kind
		self.required = required
		self.setAcceptDrops(True)

		layout = QHBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)
		
		self.setLayout(layout)
		self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
		self.setFixedHeight(48)

		self.icon = QPixmap()
		self.iconButton = RClickToolButton()
		self.iconButton.setFixedSize(48, 48)
		self.iconButton.setIcon(self.icon)
		self.iconButton.setIconSize(QSize(48, 48))
		self.iconButton.clicked.connect(self.on_icon_click)
		self.iconButton.rightClicked.connect(self.on_icon_rclick)
		self.update_required()

		layout.addWidget(self.iconButton)
		vlayout = QVBoxLayout()
		layout.addLayout(vlayout)

		hlayout = QHBoxLayout()
		hlayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
		hlayout.setSpacing(10)
		hlayout.setContentsMargins(0, 0, 0, 0)
		vlayout.addLayout(hlayout)

		hlayout.addWidget(QLabel(text=name))
		if self.required:
			hint_text = QLabel(text='(Required)')
			hint_text.setObjectName('hint')
			hlayout.addWidget(hint_text)

		self.path_box = QLineEdit()
		self.path_box.setEnabled(False)
		vlayout.addWidget(self.path_box)

	def update_required(self):
		if self.required:
			self.iconButton.setStyleSheet('' if self.path else STYLESHEET_TILE_REQUIRED)
			self.iconButton.update()

	def mousePressEvent(self, event: QMouseEvent) -> None:
		if self.path == None or event.button() != Qt.MouseButton.LeftButton:
			return super().mousePressEvent(event)
	
		drag = QDrag(self)
		mimeData = QMimeData()
		mimeData.setText(self.path.as_uri())
		drag.setMimeData(mimeData)
		drag.setHotSpot(event.position().toPoint())
		drag.exec()

	def dragEnterEvent(self, event: QDragEnterEvent) -> None:
		if event.mimeData().hasText():
			event.accept()
		else:
			event.ignore()

	def dropEvent(self, event):
		fileUrl = event.mimeData().text()
		rawFilePath = uri_to_path(fileUrl)
		filePath = Path(rawFilePath)
		if not filePath.is_file(): return
		event.accept()

		self.path_box.setText(filePath.name)
		self.path = filePath
		self.picked.emit(self.kind, self.path, self.set_icon)
		self.update_required()
	
	def set_icon(self, img: QImage|None):
		if img:
			self.icon = self.icon.fromImage(img)
			self.iconButton.setIcon(self.icon)
		else:
			self.icon.fill(QColor(0, 0, 0, 0))
			self.iconButton.setIcon(self.icon)
		print('Icon updated!')

	def on_icon_click(self):
		fileUrls = QFileDialog.getOpenFileNames(self, caption=f'Selecting {self.kind} image', filter='Images (*.png *.jpg *.jpeg *.bmp *.tga *.tiff *.hdr)')[0]
		if len(fileUrls) == 0: return
		
		url = Path(fileUrls[0])
		self.path_box.setText(url.name)
		self.path = url
		self.picked.emit(self.kind, self.path, self.set_icon)
		self.update_required()

	def on_icon_rclick(self):
		self.path_box.setText('')
		self.path = None
		self.picked.emit(self.kind, None, self.set_icon)
		self.update_required()


class MainWindow( QWidget ):
	config: AppConfig
	backend: CoreBackend
	progressBar: QProgressBar

	def __init__(self, config: AppConfig, parent=None) -> None:
		super().__init__(parent)

		self.setWindowTitle( 'PBR-2-Source v'+__version__ )
		self.setMinimumSize( 300, 450 )
		self.resize(600, 450)
		self.setObjectName('window')

		self.config = config
		self.backend = CoreBackend()

		root = QVBoxLayout(self)

		inner = QHBoxLayout()
		root.addLayout(inner)

		left = QGroupBox(title='Input')
		leftLayout = QVBoxLayout(left)
		inner.addWidget(left)

		right = QGroupBox(title='Output')
		rightLayout = QVBoxLayout(right)
		inner.addWidget(right)

		footer = QHBoxLayout()
		root.addLayout(footer)

		''' ========================== LEFT ========================== '''

		def registerWidgets(parent: QBoxLayout, entries: list[PickableImage]):
			for widget in entries:
				widget.picked.connect(self.picked)
				parent.addWidget(widget)

		registerWidgets(leftLayout, [
			PickableImage('Basecolor', 'albedo', True),
			PickableImage('Roughness', 'roughness', True),
			PickableImage('Metallic', 'metallic', False),
			PickableImage('Bumpmap', 'normal', False),
			PickableImage('Heightmap', 'height', False),
			PickableImage('Ambient Occlusion', 'ao', False),
			PickableImage('Emission', 'emit', False)
		])

		''' ========================== RIGHT ========================== '''



		''' ========================== FOOTER ========================== '''

		self.progressBar = QProgressBar()
		self.progressBar.setValue(10)
		self.progressBar.setMaximum(100)
		footer.addWidget(self.progressBar)

		self.exportButton = QPushButton('Export')
		self.exportButton.clicked.connect(self.export)
		footer.addWidget(self.exportButton)
		
	
	def picked(self, kind: ImageRole, path: Path|None, set_icon):
		img = self.backend.pick(str(path) if path else None, kind)
		set_icon(img)

	def export(self):
		print('Exporting...')
		self.exportButton.setEnabled(False)
		self.progressBar.setValue(0)

		try:
			material = self.backend.make_material(self.config.reloadOnExport)
			self.progressBar.setValue(50)
			self.progressBar.setValue(100)
	
		except Exception as e:
			print('The export failed!\n\n', format_exc())
			message = QMessageBox(QMessageBox.Icon.Critical, 'Failed to export!', str(e))
			message.exec()
			self.progressBar.setValue(0)
		
		finally:
			self.exportButton.setEnabled(True)

def start_gui():
	app_config = load_config()
	app = QApplication()

	if '--style-fusion' in argv: app_config.appTheme = AppTheme.Fusion
	if '--style-native' in argv: app_config.appTheme = AppTheme.Native

	match app_config.appTheme:
		case AppTheme.Default:
			app.setStyle( 'Fusion' )
			app.setFont( 'Inter' )
			app.setStyleSheet( STYLESHEET )
		case AppTheme.Fusion:
			app.setStyle( 'Fusion' )

	win = MainWindow( app_config )
	win.show()
	app.exec()

if __name__ == '__main__':
	start_gui()
