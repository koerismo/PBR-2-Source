from typing import Any
from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit, QLabel, QVBoxLayout, QGroupBox, QCheckBox
from PySide6.QtCore import QAbstractTableModel, QEvent, QModelIndex, Qt, QModelIndex
from PySide6.QtGui import QIntValidator, QDoubleValidator
from ..core.config import AppConfig, TargetRole, TargetConfig, get_config

TEX_COLUMNS = [
	'Texture',
	'Postfix',
	'Lossy',
	'Zip',
	'Scale',
	'Mipmaps'
]

""" 
class TextureSettingsTableModel(QAbstractTableModel):
	def __init__(self, conf: dict[TextureRole, TextureConfig]):
		super().__init__()
		self.conf = conf
		self.confKeys = [k for k, v in self.conf.items()]
		
	# def data(self)

	def rowCount(self, parent: QModelIndex) -> int:
		return len(self.confKeys)
	
	def columnCount(self, parent: QModelIndex) -> int:
		return len(TEX_COLUMNS)
	
	def headerData(self, section: int, orientation: Qt.Orientation, role: int=-1) -> Any:
		match role:
			case Qt.ItemDataRole.DisplayRole:
				if orientation == Qt.Orientation.Horizontal:
					return TEX_COLUMNS[section]
				else:
					return section
			case _:
				return super().headerData(section, orientation, role)
	
	def data(self, section: QModelIndex, role: int=-1) -> Any:
		col = section.column()
		row = section.row()

		match role:
			case Qt.ItemDataRole.EditRole:
				if col == 0: return None
				return "d-"+str(section.column())
			case Qt.ItemDataRole.DisplayRole:
				if col == 0: return TextureRole(row).name
				return "d-"+str(section.column())
			case Qt.ItemDataRole.TextAlignmentRole:
				if col == 0: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
				return None
			case _:
				return None
"""

class QBoundLineEdit(QLineEdit):
	def __init__(self, obj, key: str, t: str):
		super().__init__()
		self.obj = obj
		self.key = key
		self.keyType = type(getattr(obj, key))

		match t:
			case 'int':
				self.setValidator(QIntValidator())
				self.keyType = int
			case 'float':
				self.setValidator(QDoubleValidator())
				self.keyType = float
			case _:
				self.keyType = str

		self.reset()
		self.editingFinished.connect(self.__valueChanged__)

	def reset(self):
		value = self.keyType(getattr(self.obj, self.key))
		self.setText(str(value))

	def __valueChanged__(self):
		value = self.keyType(self.text())
		self.setText(str(value))
		setattr(self.obj, self.key, value)

class QBoundToggleEdit(QCheckBox):
	def __init__(self, obj, key: str):
		super().__init__()
		self.obj = obj
		self.key = key
		self.reset()
		self.toggled.connect(self.__valueChanged__)

	def reset(self):
		value = getattr(self.obj, self.key)
		self.setChecked(value)
	
	def __valueChanged__(self) -> None:
		setattr(self.obj, self.key, self.isChecked())

class TextureSettingsGroup(QGroupBox):
	def __init__(self, config: dict[TargetRole, TargetConfig], parent: QWidget|None=None):
		super().__init__(parent)

		self.setTitle('Textures')
		self.config = config

		layout = QGridLayout()
		layout.setColumnStretch(1, 1) # Texture postfix
		layout.setSpacing(5)

		for i, header in enumerate(TEX_COLUMNS):
			head = QLabel('**'+header+'**', textFormat=Qt.TextFormat.MarkdownText)
			layout.addWidget(head, 0, i)


		for i, (role, tex) in enumerate(config.items()):
			layout.addWidget(QLabel(role.name), i+1, 0)
			layout.addWidget(QBoundLineEdit(tex, 'postfix', 'str'), i+1, 1)
			layout.addWidget(QBoundToggleEdit(tex, 'lossy'), i+1, 2, Qt.AlignmentFlag.AlignHCenter)
			layout.addWidget(QBoundLineEdit(tex, 'scale', 'float'), i+1, 4)
			layout.addWidget(QBoundLineEdit(tex, 'mipmaps', 'int'), i+1, 5)

		self.setLayout(layout)


class SettingsWindow(QWidget):
	def __init__(self, parent: QWidget|None=None):
		super().__init__(parent)

		self.setMinimumSize(200, 200)
		self.setWindowTitle("PBR-2-Source: Settings")

		layout = QVBoxLayout()

		test_config = get_config() # AppConfig().textures
		# test_model = TextureSettingsTableModel(test_config)

		# table = QTableView()
		# table.setModel(test_model)
		# layout.addWidget(table)

		texSettings = TextureSettingsGroup(test_config.targets)
		layout.addWidget(texSettings)

		self.setLayout(layout)


# if __name__ == '__main__':
# 	from PySide6.QtWidgets import QApplication

# 	app = QApplication()
# 	win = SettingsWindow()

# 	win.show()
# 	app.exec()
