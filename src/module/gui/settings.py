from typing import Any, Literal
from enum import IntEnum
from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit, QLabel, QVBoxLayout, QGroupBox, QCheckBox, QComboBox
from PySide6.QtCore import Qt, Slot, QSignalMapper
from PySide6.QtGui import QIntValidator, QDoubleValidator
from ..core.config import AppConfig, TargetRole, TargetConfig, get_config
from ..core.enums import ImageFlags

from sourcepp import vtfpp

class BoundEdit():
	def __init__(self, obj: Any, key: str) -> None:
		super().__init__()
		self.obj = obj
		self.key = key
	
	def getValue(self):
		return getattr(self.obj, self.key)
	
	def setValue(self, v: Any):
		setattr(self.obj, self.key, v)
	
	def bind(self, obj: Any):
		self.obj = obj
		self.fromValue(self.getValue())

	def fromValue(self, value: Any):
		...

class QBoundLineEdit(BoundEdit, QLineEdit):
	def __init__(self, obj, key: str, t: Literal['int'] | Literal['float'] | None):
		super().__init__(obj, key)
		self.type = type(self.getValue())

		match t:
			case 'int':
				self.setValidator(QIntValidator())
				self.type = int
			case 'float':
				self.setValidator(QDoubleValidator())
				self.type = float
			case _:
				self.type = str

		self.fromValue(self.getValue())
		self.editingFinished.connect(self.__onEdited__)

	def fromValue(self, value):
		value = self.type(value)
		self.setText(str(value))

	def __onEdited__(self):
		value = self.type(self.text())
		self.setText(str(value))
		self.setValue(value)

class QBoundToggleEdit(BoundEdit, QCheckBox):
	def __init__(self, obj: Any, key: str):
		super().__init__(obj, key)
		self.fromValue(self.getValue())
		self.toggled.connect(self.__onEdited__)

	def fromValue(self, value: bool):
		self.setChecked(value)
	
	def __onEdited__(self) -> None:
		self.setValue(self.isChecked())

class QBoundComboEdit(BoundEdit, QComboBox):
	def __init__(self, obj: Any, key: str, enum: type[IntEnum]):
		super().__init__(obj, key)

		self.enum = enum
		for item in enum:
			self.addItem(item.name, userData=item.value)

		self.fromValue(self.getValue())
		self.currentIndexChanged.connect(self.__onEdited__)

	def fromValue(self, value: Any):
		value = getattr(self.obj, self.key)
		for i, item in enumerate(self.enum):
			if value == item or value == item.value:
				return self.setCurrentIndex(i)
		self.setCurrentIndex(0)

	@Slot()
	def __onEdited__(self, idx: int) -> None:
		self.setValue(self.enum(self.itemData(idx)))

class QBoundFlagsEdit(BoundEdit, QWidget):
	def __init__(self, obj: Any, key: str, enum: type[IntEnum]):
		super().__init__(obj, key)

		self.mapper = QSignalMapper(self)
		self.mapper.mappedInt.connect(self.__onEdited__)
		self.mapper.blockSignals(True)
		self.buttons: dict[int, QCheckBox] = {}

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)

		for v in enum:
			btn = QCheckBox(v.name)
			btn.checkStateChanged.connect(self.mapper.map)
			self.mapper.setMapping(btn, v.value)
			self.buttons[v.value] = btn
			layout.addWidget(btn)

		self.setLayout(layout)
		self.fromValue(self.getValue())

	def fromValue(self, value: Any):
		self.mapper.blockSignals(True)
		for flag, button in self.buttons.items():
			button.setChecked((flag & value) != 0)
		self.mapper.blockSignals(False)
	
	@Slot()
	def __onEdited__(self, flag: int):
		v = self.getValue()
		if self.buttons[flag].isChecked():
			self.setValue(v | flag)
		else:
			self.setValue(v & (~flag))

TextureConfigDict = dict[TargetRole, TargetConfig]

class TextureSettingsWindow(QWidget):
	settings: list[tuple[str, QBoundToggleEdit | QBoundLineEdit | QBoundComboEdit | QBoundFlagsEdit]]

	def __init__(self, targets: TextureConfigDict, parent: QWidget|None=None):
		super().__init__(parent)

		self.setWindowTitle('PBR-2-Source - Target Settings')
		self.targets = targets

		layout = QGridLayout(self)

		tex = self.targets[TargetRole.Basecolor]
		self.settings = [
			('Postfix',		QBoundLineEdit(tex, 'postfix', None)),
			('Lossy',		QBoundToggleEdit(tex, 'lossy')),
			('Zip',			QBoundToggleEdit(tex, 'zip')),
			# ('Scale',		QBoundLineEdit(tex, 'scale', 'float')),
			('Mipmaps',		QBoundLineEdit(tex, 'mipmaps', 'int')),
			('Filter',		QBoundComboEdit(tex, 'mipmapFilter', vtfpp.ImageConversion.ResizeFilter)),
			('Flags',		QBoundFlagsEdit(tex, 'flags', ImageFlags))
		]

		self.combo = QComboBox()
		self.combo.currentIndexChanged.connect(self.onCurrentRoleChanged)

		for role in TargetRole:
			self.combo.addItem(role.name, userData=role.value)

		layout.addWidget(self.combo, 0, 0, 1, 2)

		for i, (title, setting) in enumerate(self.settings):
			# head = QLabel('**'+title+'**', textFormat=Qt.TextFormat.MarkdownText)
			head = QLabel(title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
			layout.addWidget(head, i+1, 0)
			layout.addWidget(setting, i+1, 1) # type: ignore

		self.setLayout(layout)

	@Slot()
	def onCurrentRoleChanged(self, idx: int):
		self.setSelectedRole(TargetRole(self.combo.itemData(idx)))

	def copySettings(self, a: TextureConfigDict, b: TextureConfigDict):
		for role in TargetRole:
			b[role] = a[role].clone()

	def setSelectedRole(self, role: TargetRole):
		for (_, setting) in self.settings:
			setting.bind(self.targets[role])
