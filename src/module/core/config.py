from enum import IntEnum, Enum
from traceback import format_exc
from recordclass import RecordClass

from pathlib import Path
import logging as log
import sys, json

from ..version import __version__

DEFAULT_NAME = 'appconfig.json'

__config__: 'AppConfig'
__configPath__: Path

def get_config():
	assert __config__, 'Config not loaded yet!'
	return __config__

''' Get application root path '''

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
	root_path = Path(getattr(sys, '_MEIPASS')).parent
else:
	root_path = Path('./').resolve()

def get_root() -> Path:
	return root_path

''' Config structures '''

class TargetRole(Enum):
	Basecolor	= 'COLOR' # 0
	Bumpmap		= 'BUMP' # 1
	Emit		= 'EMIT' # 2
	PhongExp	= 'PHONG' # 3
	EnvmapMask	= 'ENVMASK' # 4
	Mrao		= 'MRAO' # 5 # :3

class TargetConfig(RecordClass):
	postfix: str
	lossy: bool
	zip: bool
	scale: float = 1
	mipmaps: int = -1
	flags: int = 0

	def encode(self):
		return self._asdict()

	def copy(self):
		return TargetConfig(**self._asdict())

	@staticmethod
	def decode(data) -> 'TargetConfig':
		assert isinstance(data, dict)
		return TargetConfig(**data)

class AppTheme(IntEnum):
	Default = 0
	Fusion = 1
	Native = 2

class HijackMode(IntEnum):
	Disabled = 0
	Windows = 1
	NetCon = 2

class AppConfig(RecordClass):
	appTheme: AppTheme = AppTheme.Default
	''' The app visual theme. '''
	hijackMode: HijackMode = HijackMode.Disabled
	''' The game hijacking mode. If enabled, triggers a material reload on export. '''
	hijackPort: int = 8020
	''' The game `-netconport` port. Used when hijack mode is set to NetCon. '''
	overwriteVmts: bool = False
	''' If true, always writes to the VMT, even if one already exists. '''
	compressThreshold: int = 8_000
	''' The maximum size (kB) of the largest mipmap before lossless compression is enabled. (Strata-only) '''
	targets: dict[TargetRole, TargetConfig] = {
		TargetRole.Basecolor:	TargetConfig("_basecolor", True, False),
		TargetRole.Bumpmap:		TargetConfig("_bump", False, True),
		TargetRole.Emit:		TargetConfig("_emit", False, False),
		TargetRole.PhongExp:	TargetConfig("_phongexp", False, False),
		TargetRole.EnvmapMask:	TargetConfig("_envmask", False, False),
		TargetRole.Mrao:		TargetConfig("_mrao", False, True)
	}

	def encode(self):
		return {
			**self._asdict(),
			"targets": { str(k.value): v.encode() for k, v in self.targets.items() }
		}
	
	@staticmethod
	def decode(data) -> 'AppConfig':
		assert isinstance(data, dict)
		appConfig =  AppConfig(**{
			**data,
			"targets": { TargetRole(k): TargetConfig.decode(v) for k,v in data["targets"].items() }
		})

		return appConfig

	def copy(self):
		return AppConfig(**{
			**self._asdict(),
			"targets": { k: v.copy() for k, v in self.targets.items() }
		})

def load_config(gui=True, pathOverride: str|None=None) -> AppConfig:
	log.info("Attempting to load configuration...")
	global __config__, __configPath__

	# Custom config path
	if pathOverride != None:
		__configPath__ = Path(pathOverride)
		if __configPath__.is_dir():
			__configPath__ = __configPath__ / DEFAULT_NAME
	
	# Default config path
	else:
		__configPath__ = root_path / DEFAULT_NAME

	# Create a new config if necessary
	if not __configPath__.is_file():
		__config__ = make_config()
		return __config__

	parsed: AppConfig

	try:
		with open(__configPath__, 'rb') as file:
			data = json.load(file)
			parsed = AppConfig.decode(data)

	except Exception as e:
		log.warning(f'Failed to parse the configuration!\n\n{format_exc()}')
		
		if gui:
			from PySide6.QtWidgets import QMessageBox
			message = QMessageBox(QMessageBox.Icon.Warning, 'Configuration Error', f'Invalid app configuration:\n{e}')
			message.addButton(QMessageBox.StandardButton.Cancel)
			message.addButton(QMessageBox.StandardButton.Reset)
			message.setDefaultButton(QMessageBox.StandardButton.Reset)
			result = message.exec()
			if result != QMessageBox.StandardButton.Reset:
				exit(0)

		parsed = make_config()

	__config__ = parsed
	return parsed

def save_config(conf: AppConfig):
	assert __configPath__, 'Config path not loaded yet!'
	with open(__configPath__, 'w') as file:
		json.dump(conf.encode(), file, indent='\t')

def make_config():
	log.info('Writing new configuration...')
	config = AppConfig()
	save_config(config)
	return config
