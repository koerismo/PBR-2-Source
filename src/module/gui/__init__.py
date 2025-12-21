from ..version import __version__
import logging as log
from ..core.config import AppConfig, AppTheme, get_res, load_config, AppCache, load_cache, save_cache
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
from PySide6.QtCore import Qt, Signal, Slot, QSize, QMimeData, QKeyCombination, QFileSystemWatcher, QTimer, QUrl, QSignalMapper
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QMouseEvent, QImage, QPixmap, QColor, QDrag, QDesktopServices, QKeySequence, QAction
from PySide6.QtWidgets import (
	QWidget, QMainWindow, QFrame, QApplication, QMessageBox, QMenuBar, QMenu,
	QBoxLayout, QHBoxLayout, QVBoxLayout, QSizePolicy,
	QLabel, QLineEdit, QToolButton, QFileDialog,
	QGroupBox, QProgressBar, QPushButton, QComboBox
)

# from .settings import TextureSettingsWindow

# FONT_MONO = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)

from urllib.parse import unquote_plus, urlparse
def uri_to_path(uri: str) -> str:
	return unquote_plus(urlparse(uri).path)

def get_internal_path(filename: str) -> Path:
	return get_res() / filename

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

	# This event is triggered when this image is set or reset by the user.
	on_user_modified = Signal( ImageRole, name='UserModified' )

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
		self.backend.set_role_image(rawFilePath, self.role)
		self.on_user_modified.emit(self.role)

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
		self.backend.set_role_image(fileUrls[0], self.role)
		self.on_user_modified.emit(self.role)

	def __on_icon_rclick__(self):
		self.backend.set_role_image(None, self.role)
		self.on_user_modified.emit(self.role)

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
	fileDirty: bool = False
	exporting: bool = False
	watching: bool = False

	watcherTimeout: QTimer
	watcher: QFileSystemWatcher
	watcherModifiedFiles: set[str]

	config: AppConfig
	backend: CoreBackend
	progressBar: QProgressBar
	loadRecentMenu: QMenu
	loadRecentMapper: QSignalMapper

	cache: AppCache

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
		self.cache = load_cache()

		#endregion
		''' ========================== MENU ========================== '''
		#region menu

		menuBar = QMenuBar(self)
		# menuBar.setNativeMenuBar(False)

		self.setMenuBar(menuBar)
		fileMenu = menuBar.addMenu('File')

		createAction = fileMenu.addAction('New')
		createAction.setShortcut(QKeySequence.StandardKey.New)
		createAction.triggered.connect(self.new_preset)

		loadAction = fileMenu.addAction('Open...')
		loadAction.setShortcut(QKeySequence.StandardKey.Open)
		loadAction.triggered.connect(self.load_preset)

		self.loadRecentMenu = fileMenu.addMenu('Open Recent')
		self.loadRecentMapper = QSignalMapper(self)
		self.loadRecentMapper.mappedString.connect(self.load_preset_recent)
		self.setupRecentFileMenu()

		saveAction = fileMenu.addAction('Save')
		saveAction.setShortcut(QKeySequence.StandardKey.Save)
		saveAction.triggered.connect(self.save_preset_current)

		saveAction = fileMenu.addAction('Save As...')
		saveAction.setShortcut(QKeySequence.StandardKey.Save)
		saveAction.triggered.connect(self.save_preset)
		
		fileMenu.addSeparator()

		self.watchAction = fileMenu.addAction('Watch')
		self.watchAction.setCheckable(True)
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

		presetMenu = menuBar.addMenu('View')
		advancedToggle = presetMenu.addAction('Advanced')
		advancedToggle.setCheckable(True)

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
				widget.on_user_modified.connect(self.mark_dirty)
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
			('CS:GO', GameTarget.V2023),
			('Strata Source', GameTarget.V2025),
		]: gameDropdown.addItem(text, data)
		gameDropdown.setCurrentData(Preset.game)

		def on_changed_game(x: int):
			self.backend.game = gameDropdown.itemData(x)
			self.mark_dirty()
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
			self.mark_dirty()
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
			self.mark_dirty()
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
			self.mark_dirty()
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

	def setWindowTitle(self, _title: str|None=None):
		base_title = '[*] PBR-2-Source v'+__version__
		if self.watching: base_title += ' (Watching)'
		if self.target != None: base_title += ' - ' + Path(self.target).name
		super().setWindowTitle(base_title)

	def pick_target(self, reset=False):
		if reset:
			log.debug('Resetting target')
			self.target = None
			self.revealButton.setDisabled(True)
			self.setWindowTitle()
			return

		log.debug('Picking target')

		pickOptions = {}
		if self.config.overwriteVmts == False:
			pickOptions['options'] = QFileDialog.Option.DontConfirmOverwrite
	
		# Initial filename to save to
		pickPath = Path(self.cache.lastTargetPath or self.cache.lastPresetPath or '')
		if self.backend.name:
			pickPath = pickPath.with_name(self.backend.name.rsplit('/', 2)[-1] + '.vmt')
		elif pickPath.name:
			pickPath = pickPath.with_suffix('.vmt')

		targetPath, _ = QFileDialog.getSaveFileName(self, caption='Saving material...', filter='Valve Material (*.vmt)', dir=str(pickPath), **pickOptions)

		if len(targetPath):
			self.cache.lastTargetPath = targetPath
			self.target = targetPath
			self.backend.pick_vmt(targetPath)

		if self.target:
			self.revealButton.setDisabled(False)

		self.setWindowTitle()

	#region Exporting

	@Slot()
	def export(self, *, noCache=True):
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
			material = self.backend.make_material(noCache=noCache)
			self.progressBar.setValue(20)

			if self.target == None: self.pick_target()
			if self.target == None: raise InterruptedError()

			def log_callback(msg: str|None, percent: int|None):
				log.info(f'Export ({self.progressBar.value()}%): {msg}')
				if msg: self.progressBar.setFormat(msg)
				if percent: self.progressBar.setValue(percent)
				QApplication.processEvents()

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
			self.watchAction.setChecked(False)
			self.pick_target()
			if not self.target: return

		if self.watching:	self.stop_watch()
		else:				self.start_watch()
		log.info(f'Watching {len(self.watcher.files())} files.\n')

	def start_watch(self):
		self.watching = True
		self.watchAction.setChecked(True)
		paths = [x for x in self.backend.paths.values() if x != None]
		self.watcher.addPaths(paths)
		self.setWindowTitle()

	def stop_watch(self):
		self.watching = False
		self.watchAction.setChecked(False)
		self.watcher.removePaths(self.watcher.files())
		self.setWindowTitle()

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
		self.watcherTimeout.start(self.config.watchTimeout)

	#endregion
	#region Presets

	def mark_dirty(self, *, dirty=True):
		self.fileDirty = dirty
		self.setWindowModified(dirty)

	def check_if_dirty(self) -> bool:
		if not self.fileDirty:
			return True

		message = QMessageBox(QMessageBox.Icon.Warning, f'Do you want to save the changes you made?', 'If you continue, your unsaved changes will be erased!')
		message.addButton(QMessageBox.StandardButton.Save)
		message.addButton(QMessageBox.StandardButton.Discard)
		message.addButton(QMessageBox.StandardButton.Cancel)
		message.setDefaultButton(QMessageBox.StandardButton.Save)
		result = message.exec()

		if result == QMessageBox.StandardButton.Save:
			if not self.save_preset_current():
				return False

		return result != QMessageBox.StandardButton.Cancel

	@Slot()
	def new_preset(self):
		self.load_preset(preset=Preset())

	@Slot()
	def load_preset_recent(self, path: str):
		self.load_preset(path=path)

	@Slot()
	def load_preset(self, *, preset: Preset|None=None, path: str|None=None):
		if not self.check_if_dirty():
			return

		if preset == None:
			if path == None:
				lastPresetPath = str(Path(self.cache.lastPresetPath).parent) if self.cache.lastPresetPath else str(Path.cwd())
				path = QFileDialog.getOpenFileName(self,
										caption='Loading preset...',
										filter='JSON Presets (*.json)',
										dir=lastPresetPath,
										)[0]

			if path == None or len(path) == 0:
				return

			# Reset target path
			if self.watching: self.stop_watch()
			self.pick_target(reset=True)
			preset = Preset.load(path)

		self.gameDropdown.setCurrentData(preset.game)
		self.modeDropdown.setCurrentData(preset.mode)
		self.normalTypeDropdown.setCurrentData(preset.normalType)
		self.scaleTargetDropdown.setCurrentData(preset.scaleTarget)

		self.backend.load_preset(preset)
		self.update_from_preset.emit(preset)
		self.mark_dirty(dirty=False)

		# Update last-used path
		# None values will force the program to ask for the path again on save
		self.cache.lastPresetPath = path

		# Append to recent files
		if path:
			self.pushRecentFile(path)

	def save_preset_current(self):
		return self.save_preset(presetPath=self.cache.lastPresetPath)

	def save_preset(self, *, presetPath: str|None=None) -> bool:
		if presetPath == None:
			presetPath, _ = QFileDialog.getSaveFileName(self,
										caption='Saving preset...',
										filter='JSON Presets (*.json)',
										dir=self.cache.lastPresetPath, # type: ignore
										)

		if not len(presetPath):
			return False

		# Keep track of last preset path
		self.cache.lastPresetPath = presetPath

		preset = Preset()
		self.backend.save_preset(preset)
		preset.save(presetPath)

		self.mark_dirty(dirty=False)
		return True

	#endregion
	#region Recents

	def makeRecentFileMenuAction(self, path: str) -> QAction:
		p = Path(path)
		rp = str(p.relative_to(p.parent.parent.parent))

		action = QAction(rp, self.loadRecentMenu)
		self.loadRecentMapper.setMapping(action, path)
		action.triggered.connect(self.loadRecentMapper.map)
		return action

	def setupRecentFileMenu(self) -> None:
		for path in self.cache.recent:
			self.loadRecentMenu.addAction(self.makeRecentFileMenuAction(path))

	def pushRecentFile(self, path: str) -> None:
		historyCount = len(self.cache.recent)
		actionList = self.loadRecentMenu.actions()
		assert len(actionList) == historyCount, 'File history desync! This should never happen!'

		# If this entry already exists, remove it.
		for i, file in enumerate(self.cache.recent):
			if file == path:
				# If this was the last file loaded, then we don't need to change anything. Return early!
				if i == 0: return
				self.cache.recent.pop(i)
				self.loadRecentMapper.removeMappings(actionList[i])
				self.loadRecentMenu.removeAction(actionList[i])
				break

		# Append to start of list
		action = self.makeRecentFileMenuAction(path)
		if len(actionList) == 0:
			self.loadRecentMenu.addAction(action)
			self.cache.recent.append(path)
		else:
			self.loadRecentMenu.insertAction(actionList[0], action)
			self.cache.recent.insert(0, path)

		# Re-fetch lists so we don't try to delete anything twice
		historyCount = len(self.cache.recent)
		actionList = self.loadRecentMenu.actions()

		# Remove history if we reach a limit
		if historyCount > 10:
			self.loadRecentMenu.removeAction(actionList[-1])
			self.cache.recent.pop(-1)

	def closeEvent(self, event: QCloseEvent) -> None:
		if not self.check_if_dirty():
			return

		log.info('Shutting down...')
		try:
			log.debug('Saving app cache...')
			save_cache(self.cache)

		except Exception as e:
			log.error(f'An error occurred during shutdown! Traceback:\n{format_exc()}')

		log.info('Goodbye!')
		event.accept()

	#endregion


def start_gui(args):
	app: QApplication = QApplication()
	app.setApplicationVersion(__version__)
	app_config = load_config(True, pathOverride=args.config)

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

	# settings = TextureSettingsWindow()
	# settings.show()

	win = MainWindow( app_config )
	win.show()

	app.exec()
