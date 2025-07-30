from enum import IntEnum, Enum
from traceback import format_exc
from dataclasses import dataclass, asdict, field

from io import SEEK_SET
from pathlib import Path
import logging as log
import sys, json

from ..version import __version__

CONFIG_NAME = 'appconfig.json'
CACHE_NAME = 'appcache.json'

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
	Basecolor	= 'COLOR'	# 0
	Bumpmap		= 'BUMP'	# 1
	Emit		= 'EMIT'	# 2
	PhongExp	= 'PHONG'	# 3
	EnvmapMask	= 'ENVMASK'	# 4
	Mrao		= 'MRAO'	# 5 # :3

@dataclass
class TargetConfig():
	postfix: str
	lossy: bool
	zip: bool = False
	scale: float = 1.0
	mipmaps: int = -1
	flags: int = 0

	def encode(self):
		return asdict(self)

	def copy(self):
		return TargetConfig(**asdict(self))

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

@dataclass
class AppConfig():
	appTheme: AppTheme = AppTheme.Default
	''' The app visual theme. '''
	hijackMode: HijackMode = HijackMode.Disabled
	''' The game hijacking mode. If enabled, triggers a material reload on export. '''
	hijackPort: int = 8020
	''' The game `-netconport` port. Used when hijack mode is set to NetCon. '''
	overwriteVmts: bool = False
	''' If true, always writes to the VMT, even if one already exists. '''
	watchTimeout: int = 500
	''' The timeout (milliseconds) to use when listening for input changes before initiating an export. '''
	targets: dict[TargetRole, TargetConfig] = field(default_factory=lambda: {
		TargetRole.Basecolor:	TargetConfig("_basecolor.vtf", True),
		TargetRole.Bumpmap:		TargetConfig("_bump.vtf", False),
		TargetRole.Emit:		TargetConfig("_emit.vtf", False),
		TargetRole.PhongExp:	TargetConfig("_phongexp.vtf", False),
		TargetRole.EnvmapMask:	TargetConfig("_envmask.vtf", False),
		TargetRole.Mrao:		TargetConfig("_mrao.vtf", False)
	})

	def encode(self):
		return {
			**asdict(self),
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
			**asdict(self),
			"targets": { k: v.copy() for k, v in self.targets.items() }
		})

def load_config(gui=True, pathOverride: str|None=None) -> AppConfig:
	log.info("Attempting to load configuration...")
	global __config__, __configPath__

	# Custom config path
	if pathOverride != None:
		__configPath__ = Path(pathOverride)
		if __configPath__.is_dir():
			__configPath__ = __configPath__ / CONFIG_NAME
	
	# Default config path
	else:
		__configPath__ = root_path / CONFIG_NAME

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

@dataclass
class AppCache():
	recent: list[str] = field(default_factory=lambda: [])

def load_cache() -> AppCache:
	cache_path = root_path / CACHE_NAME

	try:
		with open(cache_path, 'r') as file:
			log.info('Reading cache...')
			return AppCache(**json.load(file))
	
	except FileNotFoundError as e:
		log.info('Using fresh cache...')
		return AppCache()
	
	except json.JSONDecodeError as e:
		log.error(f'Failed to parse cache! Falling back to fresh cache.\n{format_exc()}')
		return AppCache()

def save_cache(cache: AppCache) -> None:
	cache_path = root_path / CACHE_NAME

	with open(cache_path, 'w') as file:
		json.dump(asdict(cache), file)
