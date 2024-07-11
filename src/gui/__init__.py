from version import __version__

from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtWidgets import QMainWindow, QWidget, QApplication, QBoxLayout, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QToolButton, QSizePolicy, QFileDialog, QFrame
from PySide6.QtGui import QImage, QPixmap, QFontDatabase, QColor

STYLESHEET_REQUIRED = '''
border-color: #999;
'''

STYLESHEET = '''
* {
	font-size: 12px;
	font-weight: 350;
	color: #ccc;
}

QLabel#hint {
	color: #777;
	font-size: 10px;
	font-weight: normal;
}

QLineEdit {
	font-weight: normal;
}

QToolButton {
	border: 1px solid #555;
	background-color: #333;
}

QToolButton[fulfilled="true"] {
	border-color: green;
}

QToolButton[fulfilled="false"] {
	border-color: red;
}

QToolButton:hover {
	border-color: #666;
	background-color: #444;
}

QToolButton:pressed {
	background-color: #333;
}

QLineEdit:disabled {
	background-color: #282828;
	border: 1px solid #282828;
	color: #888;
}
'''

# def registerFonts():
# 	QFontDatabase.addApplicationFont('./res/Inter-Regular.ttf')

class PickableImage( QWidget ):
	picked = Signal( str, Path, name='Picked', arguments=['Kind', 'Path'] )
	''' Fires when an image has been picked from the filesystem. (Path|None) '''

	name: str
	kind: str
	required: bool
	path: Path|None = None
	
	path_box: QLineEdit
	icon_label: QToolButton
	icon: QPixmap

	def __init__(self, name: str, kind: str, required: bool, parent: QWidget | None = None, f: Qt.WindowType = Qt.WindowType.Widget) -> None:
		super().__init__(parent, f)
		self.name = name
		self.kind = kind
		self.required = required

		layout = QHBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)
		
		self.setLayout(layout)
		self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
		self.setFixedHeight(48)

		self.icon = QPixmap()
		self.icon_label = QToolButton()
		self.icon_label.setFixedSize(48, 48)
		self.icon_label.setIcon(self.icon)
		self.icon_label.setIconSize(QSize(48, 48))
		self.icon_label.clicked.connect(self.on_icon_click)
		self.update_required()

		layout.addWidget(self.icon_label)
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
		self.path_box.setFixedWidth(250)
		self.path_box.setEnabled(False)
		vlayout.addWidget(self.path_box)

	def update_required(self):
		if self.required:
			self.icon_label.setStyleSheet('' if self.path else STYLESHEET_REQUIRED)
			self.icon_label.update()

	
	def on_icon_click(self):
		fileUrls = QFileDialog.getOpenFileNames(self, caption=f'Selecting {self.kind} image', filter='Images (*.png *.jpg *.jpeg *.bmp *.tga *.vtf)')[0]
		
		if len(fileUrls) == 0:
			self.path_box.setText('')
			self.icon.fill(QColor(0, 0, 0, 0))
			self.icon_label.setIcon(self.icon)
			self.picked.emit(self.kind, None)
			self.path = None
		else:
			url = Path(fileUrls[0])
			self.path_box.setText(url.name)
			self.icon.load(str(url))
			self.icon_label.setIcon(self.icon)
			self.picked.emit(self.kind, url)
			self.path = url
		
		self.update_required()

class MainWindow( QWidget ):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)

		self.setWindowTitle( 'PBR-2-Source v'+__version__ )
		self.setMinimumSize( 600, 400 )
		
		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignmentFlag.AlignTop)
		# layout.addWidget(QLabel('HELLO'))

		def registerWidgets(parent: QBoxLayout, entries: list[PickableImage]):
			for widget in entries:
				widget.picked.connect(self.picked)
				parent.addWidget(widget)

		registerWidgets(layout, [
			PickableImage('Basecolor', 'albedo', True),
			PickableImage('Roughness', 'roughness', True),
			PickableImage('Metallic', 'metallic', True),
			PickableImage('Bumpmap', 'normal', False),
			PickableImage('Heightmap', 'height', False),
			PickableImage('Ambient Occlusion', 'ao', False),
			PickableImage('Emission', 'emit', False)
		])


	
	def picked(self, kind: str, path: Path|None):
		print('Selected', kind, path)

def start_gui():
	app = QApplication()
	app.setStyle( 'Fusion' )
	app.setFont( 'Inter' )
	win = MainWindow()
	win.setStyleSheet( STYLESHEET )
	win.show()
	app.exec()

if __name__ == '__main__':
	start_gui()
