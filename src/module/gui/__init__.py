from ..version import __version__
import logging as log
from ..core.config import AppConfig, AppTheme, get_root, get_config
from ..core.material import GameTarget, MaterialMode, NormalType
from ..core.io.icns import ICNS
from ..core.preset import Preset

from .style import STYLESHEET_TILE_REQUIRED, STYLESHEET, STYLESHEET_MIN
from .backend import CoreBackend, ImageRole

from typing import Any
from sys import platform
from traceback import format_exc
from datetime import datetime

from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot, QSize, QMimeData, QKeyCombination, QFileSystemWatcher, QTimer, QUrl
from PySide6.QtGui import QDragEnterEvent, QMouseEvent, QImage, QPixmap, QColor, QDrag, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
	QWidget, QMainWindow, QFrame, QApplication, QMessageBox, QMenuBar,
	QBoxLayout, QHBoxLayout, QVBoxLayout, QSizePolicy,
	QLabel, QLineEdit, QToolButton, QFileDialog,
	QGroupBox, QProgressBar, QPushButton, QComboBox
)

# from .settings import SettingsWindow

# FONT_MONO = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)

from urllib.parse import unquote_plus, urlparse
def uri_to_path(uri: str) -> str:
	return unquote_plus(urlparse(uri).path)

def get_internal_path(filename: str) -> Path:
	return get_root() / filename

class QDataComboBox( QComboBox ):
	def setCurrentData(self, data: Any):
		index = -1
		for i in range(self.count()):
			if data == self.itemData(i):
				index = i
				break
		self.setCurrentIndex(index)
		# TODO: Qt Docs say this should fire when we do the above, but it doesn't.
		self.currentIndexChanged.emit(index)

class RClickToolButton( QToolButton ):
	rightClicked = Signal( name='RightClicked' )
	def mouseReleaseEvent(self, e: QMouseEvent) -> None:
		if e.button() == Qt.MouseButton.RightButton: self.rightClicked.emit()
		else: self.clicked.emit()


class PickableImage( QFrame ):
	name: str
	role: ImageRole
	required: bool
	path: Path|None = None
	
	path_box: QLineEdit
	iconButton: QToolButton
	icon: QPixmap

	backend: CoreBackend

	def __init__(self, backend: CoreBackend, name: str, kind: ImageRole, required: bool, parent: QWidget | None = None, f: Qt.WindowType = Qt.WindowType.Widget) -> None:
		super().__init__(parent, f)
		self.backend = backend
		self.name = name
		self.role = kind
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
		self.iconButton.clicked.connect(self.__on_icon_click__)
		self.iconButton.rightClicked.connect(self.__on_icon_rclick__)
		self.__update_required__()

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

	def __update_required__(self):
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
		if platform == 'win32': rawFilePath = rawFilePath[1:]
		filePath = Path(rawFilePath)
		if not filePath.is_file(): return
		event.accept()

		self.path = filePath
		self.__update_meta__()

	def __set_path__(self, path: str):
		self.path = Path(path)
		self.__update_meta__()
	
	def __set_icon__(self, img: QImage|None):
		if img:
			self.icon = self.icon.fromImage(img)
			self.iconButton.setIcon(self.icon)
		else:
			self.icon.fill(QColor(0, 0, 0, 0))
			self.iconButton.setIcon(self.icon)
		log.info(self.role.capitalize()+' icon updated!')

	def __on_icon_click__(self):
		fileUrls = QFileDialog.getOpenFileNames(self, caption=f'Selecting {self.name} image', filter='Images (*.png *.jpg *.jpeg *.bmp *.tga *.tiff *.hdr)')[0]
		if len(fileUrls) == 0: return
		self.__set_path__(fileUrls[0])
		self.backend.set_role_image(fileUrls[0], self.role)

	def __on_icon_rclick__(self):
		self.path = None
		self.backend.set_role_image(None, self.role)
		self.__update_meta__()

	def __update_meta__(self):
		''' Updates the text and styling for this widget. '''
		self.iconButton.setToolTip(f'{self.path.name} Right-click to remove' if self.path else '')
		self.path_box.setText(self.path.name if self.path else '')
		self.__update_required__()

	@Slot()
	def on_role_updated(self, role: ImageRole, path: str, qimage: QImage):
		if role != self.role: return
		self.__set_path__(path)
		self.__set_icon__(qimage)

class MainWindow( QMainWindow ):
	update_from_preset = Signal( Preset, name='UpdateFromPreset' )

	target: str|None = None
	exporting: bool = False
	watching: bool = False

	watcherTimeout: QTimer
	watcher: QFileSystemWatcher
	watcherModifiedFiles: set[str]

	config: AppConfig
	backend: CoreBackend
	progressBar: QProgressBar

	def __init__(self, config: AppConfig, parent=None) -> None:
		#region init
		super().__init__(parent)

		self.setWindowTitle()

		self.watcherTimeout = QTimer()
		self.watcherTimeout.setSingleShot(True)
		self.watcherTimeout.timeout.connect(self.export)
		self.watcherModifiedFiles = set()

		self.watcher = QFileSystemWatcher(self)
		self.watcher.fileChanged.connect(self.on_file_changed)

		self.config = config
		self.backend = CoreBackend()

		#endregion
		''' ========================== MENU ========================== '''
		#region menu

		menuBar = QMenuBar(self)
		# menuBar.setNativeMenuBar(False)

		self.setMenuBar(menuBar)
		fileMenu = menuBar.addMenu('File')
		loadAction = fileMenu.addAction('Load Preset')
		loadAction.setShortcut(QKeySequence.StandardKey.Open)
		loadAction.triggered.connect(self.load_preset)

		saveAction = fileMenu.addAction('Save Preset')
		saveAction.setShortcut(QKeySequence.StandardKey.Save)
		saveAction.triggered.connect(self.save_preset)
		
		fileMenu.addSeparator()

		self.watchAction = fileMenu.addAction('Watch')
		self.watchAction.triggered.connect(self.watch_toggle)

		exportAction = fileMenu.addAction('Export')
		exportAction.triggered.connect(self.export)
		exportAction.setShortcuts([
			QKeySequence(QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_E)),
			QKeySequence(QKeyCombination(Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier, Qt.Key.Key_E))
			])
		
		exportAsAction = fileMenu.addAction('Export As...')
		exportAsAction.triggered.connect(self.export_as)
		exportAsAction.setShortcuts([
			QKeySequence(QKeyCombination(Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_E)),
			QKeySequence(QKeyCombination(Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.AltModifier, Qt.Key.Key_E))
			])
		
		#endregion
		''' ========================== LAYOUT ========================== '''
		#region layout

		rootWidget = QWidget(self)
		root = QVBoxLayout(rootWidget)
		self.setCentralWidget(rootWidget)

		inner = QHBoxLayout()
		root.addLayout(inner)

		left = QGroupBox(title='Input')
		leftLayout = QVBoxLayout(left)
		inner.addWidget(left)

		right = QGroupBox(title='Output')
		rightLayout = QVBoxLayout(right)
		rightLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
		inner.addWidget(right)

		footer = QHBoxLayout()
		root.addLayout(footer)

		# endregion
		''' ========================== LEFT ========================== '''
		#region left

		def registerWidgets(parent: QBoxLayout, entries: list[PickableImage]):
			for widget in entries:
				self.backend.role_updated.connect(widget.on_role_updated)
				parent.addWidget(widget)

		registerWidgets(leftLayout, [
			PickableImage(self.backend, 'Basecolor', ImageRole.Albedo, True),
			PickableImage(self.backend, 'Roughness', ImageRole.Roughness, True),
			PickableImage(self.backend, 'Metallic', ImageRole.Metallic, False),
			PickableImage(self.backend, 'Bumpmap', ImageRole.Normal, False),
			PickableImage(self.backend, 'Heightmap', ImageRole.Height, False),
			PickableImage(self.backend, 'Ambient Occlusion', ImageRole.AO, False),
			PickableImage(self.backend, 'Emission', ImageRole.Emit, False)
		])
		leftLayout.addStretch(1)

		#endregion
		''' ========================== RIGHT ========================== '''
		#region right

		rightLayout.addWidget(QLabel('Game'))

		self.gameDropdown = gameDropdown = QDataComboBox()
		rightLayout.addWidget(gameDropdown)
		for text,data in [
			('HL2: E2 / Portal / TF2', GameTarget.V2007),
			('Portal 2 / Alien Swarm', GameTarget.V2011),
			('Garry\'s Mod', GameTarget.VGMOD),
			('CS:GO / Strata', GameTarget.V2023),
		]: gameDropdown.addItem(text, data)
		gameDropdown.setCurrentData(Preset.game)

		def on_changed_game(x: int):
			self.backend.game = gameDropdown.itemData(x)
		gameDropdown.currentIndexChanged.connect(on_changed_game)

		rightLayout.addWidget(QLabel('Mode'))

		self.modeDropdown = modeDropdown = QDataComboBox()
		rightLayout.addWidget(modeDropdown)
		for text,data in [
			('Model: PBR', MaterialMode.PBRModel),
			('Model: Phong', MaterialMode.Phong),
			('Model: Phong+Envmap', MaterialMode.PhongEnvmap),
			('Model: Phong+Envmap+Alpha', MaterialMode.PhongEnvmapAlpha),
			('Model: Phong+Envmap+Emission', MaterialMode.PhongEnvmapEmit),
			('Brush: PBR', MaterialMode.PBRBrush),
			('Brush: Envmap', MaterialMode.Envmap),
			('Brush: Envmap+Alpha', MaterialMode.EnvmapAlpha),
			('Brush: Envmap+Emission', MaterialMode.EnvmapEmit),
		]: modeDropdown.addItem(text, data)
		modeDropdown.setCurrentData(Preset.mode)
	
		def on_changed_mode(x: int):
			self.backend.mode = modeDropdown.itemData(x)
		modeDropdown.currentIndexChanged.connect(on_changed_mode)

		rightLayout.addWidget(QLabel('Bumpmap Type'))

		self.normalTypeDropdown = normalTypeDropdown = QDataComboBox()
		rightLayout.addWidget(normalTypeDropdown)
		for text,data in [
			('DirectX / 3DS Max', NormalType.DX),
			('OpenGL / Maya', NormalType.GL)
		]: normalTypeDropdown.addItem(text, data)

		def on_changed_normalType(x: int):
			self.backend.normalType = normalTypeDropdown.itemData(x)
		normalTypeDropdown.currentIndexChanged.connect(on_changed_normalType)

		rightLayout.addWidget(QLabel('Target Scale'))
		self.scaleTargetDropdown = scaleTargetDropdown = QDataComboBox()
		rightLayout.addWidget(scaleTargetDropdown)
		for text,data in [
			('None', 0),
			('2048x', 2048),
			('1024x', 1024),
			('512x', 512),
			('256x', 256),
			('128x', 128),
			('64x', 64),
		]: scaleTargetDropdown.addItem(text, data)

		def on_changed_scaleTarget(x: int):
			self.backend.scaleTarget = scaleTargetDropdown.itemData(x)
		scaleTargetDropdown.currentIndexChanged.connect(on_changed_scaleTarget)

		# rightLayout.addWidget(QLabel('Material Parameters'))
		# matParamEdit = QPlainTextEdit(lineWrapMode=QPlainTextEdit.LineWrapMode.NoWrap, tabStopDistance=16)
		# matParamEdit.setFont(FONT_MONO)
		# matParamEdit.setMinimumSize(10, 10)
		# matParamEdit.setMaximumSize(50, 50)
		# rightLayout.addWidget(matParamEdit, 0)

		#endregion
		''' ========================== FOOTER ========================== '''
		#region footer

		self.progressBar = QProgressBar()
		self.progressBar.setValue(0)
		self.progressBar.setMaximum(100)
		self.progressBar.setTextVisible(True)
		self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.progressBar.setFormat('') # Avoid displaying a percentage
		footer.addWidget(self.progressBar)


		# TODO: Qt doesn't seem to have a nice way to transfer the text color to an icon.
		self.revealButton = QPushButton(QPixmap(get_internal_path('res/reveal.svg')), '')
		self.revealButton.setMaximumWidth(32)
		self.revealButton.setToolTip('Reveal in folder')
		self.revealButton.setDisabled(True)
		self.revealButton.clicked.connect(self.reveal_folder)
		footer.addWidget(self.revealButton)


		self.exportButton = QPushButton('Export As...')
		self.exportButton.clicked.connect(self.export_as)
		footer.addWidget(self.exportButton)
		
		#endregion

		# Configure minimum size based on size hint, just so it looks good always
		self.setMinimumSize(self.sizeHint())
		self.resize(600, 450)

	def setWindowTitle(self):
		base_title = 'PBR-2-Source v'+__version__
		if self.watching: base_title += ' (Watching)'
		if self.target != None: base_title += ' - ' + Path(self.target).name
		super().setWindowTitle(base_title)

	# @Slot()
	# def on_image_picked(self, kind: ImageRole, path: Path|None, set_icon):
	# 	img = self.backend.set_image(str(path) if path else None, kind)
	# 	self.reset_watch()
	# 	set_icon(img)

	def pick_target(self, reset=False):
		if reset:
			log.debug('Resetting target')
			self.target = None
			self.revealButton.setDisabled(True)
			self.setWindowTitle()
			return

		log.debug('Picking target')
		options: Any = {'options': QFileDialog.Option.DontConfirmOverwrite } if not self.config.overwriteVmts else {}
		targetPath = QFileDialog.getSaveFileName(self, caption='Saving material...', filter='Valve Material (*.vmt)', **options)[0]
		if len(targetPath): self.target = targetPath

		if self.target:
			self.revealButton.setDisabled(False)

		self.setWindowTitle()

	#region Exporting

	@Slot()
	def export(self, noCache=True):
		if self.exporting: return
		self.exporting = True

		overwriteVmts = self.config.overwriteVmts
		if not overwriteVmts:
			keyModifiers = QApplication.queryKeyboardModifiers()
			overwriteVmts = bool(keyModifiers & keyModifiers.AltModifier)
			if overwriteVmts: log.info('Alt key active: VMT overwrite is enabled for this export.')

		log.info('Exporting...')
		self.exportButton.setEnabled(False)
		self.progressBar.setFormat('Exporting...')
		self.progressBar.setValue(0)
		QApplication.processEvents()

		try:
			self.progressBar.setFormat('Creating material...')
			material = self.backend.make_material(noCache)
			self.progressBar.setValue(20)

			if self.target == None: self.pick_target()
			if self.target == None: raise InterruptedError()
			
			targetPath: str = self.target

			def log_callback(msg: str|None, percent: int|None):
				log.info(f'Export ({self.progressBar.value()}%): {msg}')
				if msg: self.progressBar.setFormat(msg)
				if percent: self.progressBar.setValue(percent)
				QApplication.processEvents()

			self.backend.pick_vmt(targetPath)
			self.backend.export(material, log_callback, overwrite_vmt=overwriteVmts)
			self.progressBar.setValue(100)

			if self.config.hijackMode:
				self.backend.send_engine_command(f'mat_reloadmaterial {self.backend.name}')
	
		except Exception as e:
			self.progressBar.setValue(0)
			self.progressBar.setFormat('')

			if isinstance(e, InterruptedError):
				log.info('The export was cancelled by the user.')
			else:
				log.warning(f'The export failed!\n\n{format_exc()}')
				message = QMessageBox(QMessageBox.Icon.Critical, 'Failed to export!', str(e))
				message.exec()
		
		finally:
			self.exportButton.setEnabled(True)
			self.exporting = False

	@Slot()
	def export_as(self):
		if self.exporting: return
		self.pick_target(reset=True)
		self.export()

	@Slot()
	def reveal_folder(self):
		if self.target == None: return
		path = Path(self.target).parent
		QDesktopServices.openUrl(QUrl.fromLocalFile(path))

	#endregion
	#region Watching

	@Slot()
	def watch_toggle(self):
		if not self.watching and self.target == None:
			self.pick_target()
			if not self.target: return

		self.watching = not self.watching
		if self.watching:	self.start_watch()
		else:				self.stop_watch()
		log.info(f'Watching {len(self.watcher.files())} files.\n')
		self.setWindowTitle()

	def start_watch(self):
		self.watchAction.setText('Stop Watching')
		paths = [x for x in [
			self.backend.albedoPath,
			self.backend.roughnessPath,
			self.backend.metallicPath,
			self.backend.emitPath,
			self.backend.aoPath,
			self.backend.normalPath,
			self.backend.heightPath,
		] if x != None]
		self.watcher.addPaths(paths)

	def stop_watch(self):
		self.watchAction.setText('Watch')
		self.watcher.removePaths(self.watcher.files())

	def reset_watch(self):
		if not self.watching: return
		log.info('Resetting watch...')
		self.stop_watch()
		self.start_watch()
		log.info(f'Watching: {self.watcher.files()}')

	def force_stop_watch(self, issue: str='An error occurred!'):
		if not self.watching: return
		message = QMessageBox(QMessageBox.Icon.Information, 'Watch Error', issue)
		message.exec()

	@Slot()
	def on_file_changed(self, _file: str):
		assert self.watching, 'on_file_changed handler not detatched. Tell a programmer!'
		if not self.watcherTimeout.isActive():
			log.info(f'Files changed! Starting timeout...')
		self.watcherTimeout.start(500)

	#endregion
	#region Presets

	@Slot()
	def load_preset(self):
		selected = QFileDialog.getOpenFileName(self, caption='Loading preset...', filter='JSON Presets (*.json)')[0]
		if not len(selected): return

		# Reset target path
		if self.watching: self.stop_watch()
		self.pick_target(reset=True)

		preset = Preset.load(selected)
		self.gameDropdown.setCurrentData(preset.game)
		self.modeDropdown.setCurrentData(preset.mode)
		self.normalTypeDropdown.setCurrentData(preset.normalType)
		self.scaleTargetDropdown.setCurrentData(preset.scaleTarget)
		# self.hintDropdown.setCurrentData(preset.hint)
		# self.envmapDropdown.setCurrentData(preset.envmap)

		self.backend.load_preset(preset)
		self.update_from_preset.emit(preset)
	
	def save_preset(self):
		selected = QFileDialog.getSaveFileName(self, caption='Saving preset...', filter='JSON Presets (*.json)')[0]
		if not len(selected): return
		
		preset = Preset()
		self.backend.save_preset(preset)
		preset.save(selected)

	#endregion


def start_gui():
	app: QApplication = QApplication()
	app.setApplicationVersion(__version__)	
	app_config = get_config()

	match app_config.appTheme:
		case AppTheme.Default:
			app.setStyle( 'Fusion' )
			app.setFont( 'Inter' )
			app.setStyleSheet( STYLESHEET )
		case AppTheme.Fusion:
			app.setStyle( 'Fusion' )
			app.setStyleSheet( STYLESHEET_MIN )

	dt = datetime.now()
	with open(get_internal_path('res/icon.icns'), 'rb') as file:
		app_icon_file = ICNS.get_icon(file.read(), size=256, variant=(None if dt.month // 2 != 3 else b'stpr'))
		assert app_icon_file != None, 'Failed to read icon!'

	# Hack to make sure Windows applies the application icon correctly.
	# Only should be used when not showing a terminal - otherwise it causes the app to appear duplicated.
	# https://stackoverflow.com/a/27872625
	# if platform == 'win32':
	# 	from ctypes import windll
	# 	myappid = u'com.koerismo.pbr-2-source'
	# 	windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

	app_icon = QPixmap()
	app_icon.loadFromData(app_icon_file)
	app.setWindowIcon(app_icon)

	# settings = SettingsWindow()
	# settings.show()

	win = MainWindow( app_config )
	win.show()
	
	app.exec()

if __name__ == '__main__':
	start_gui()
