import tomlkit
from pathlib import Path
from enum import IntEnum
from .version import __version__
from .logger import log
from traceback import format_exc
import sys

'''
# Config example:
app-theme = 0 # 0/1/2
reload-on-export = false # true/false
hijack-target = ".../.../hl2.exe" # path/""
'''

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
	root_path = getattr(sys, '_MEIPASS')
	config_path = Path(root_path).parent / 'appconfig.toml'
else:
	config_path = Path('./appconfig.toml').absolute()

class AppTheme(IntEnum):
	Default = 0
	Fusion = 1
	Native = 2

class AppConfig():
	__toml__: tomlkit.TOMLDocument|None = None
	def getToml(self):
		return self.__toml__ or tomlkit.TOMLDocument()
	def setToml(self, toml: tomlkit.TOMLDocument):
		self.__toml__ = toml

	appTheme = AppTheme.Default
	reloadOnExport = True
	hijackTarget: str|None = None

def load_config(gui=True) -> AppConfig:
	log.info("Attempting to load configuration...")
	
	if not config_path.is_file():
		make_config()
		return AppConfig()
	
	parsed = AppConfig()
	
	try:
		with open(config_path, 'rb') as file:
			rawConf = tomlkit.load(file)
			parsed.setToml(rawConf)

			rawAppTheme: AppTheme = rawConf.get('app-theme', AppTheme.Default)
			if not isinstance(rawAppTheme, int): rawAppTheme = AppTheme.Default
			parsed.appTheme = rawAppTheme

			rawReloadOpt: bool = rawConf.get('reload-on-export', False)
			if not isinstance(rawReloadOpt, bool): rawReloadOpt = False
			parsed.reloadOnExport = rawReloadOpt
			
			rawHijackOpt: str|None = rawConf.get('hijack-target', None)
			if not rawHijackOpt: rawHijackOpt = None
			parsed.hijackTarget = rawHijackOpt
	
	except Exception:
		log.warning('Failed to parse the configuration!\n\n', format_exc())
		if gui:
			from PySide6.QtWidgets import QMessageBox
			message = QMessageBox(QMessageBox.Icon.Warning, 'Configuration Error', 'Invalid app configuration!', QMessageBox.StandardButton.Reset)
			message.exec()
		make_config()

	
	return parsed

def save_config(conf: AppConfig):
	with open(config_path, 'w') as file:
		toml = conf.getToml()
		toml['app-theme'] = conf.appTheme
		toml['reload-on-export'] = conf.reloadOnExport
		toml['hijack-target'] = conf.hijackTarget or ''
		tomlkit.dump(toml, file)

def make_config():
	log.info('Writing new configuration...')
	with open(config_path, 'w') as file:
		file.writelines([
			f'# Generated by PBR-2-Source v{__version__}\n'
			'app-theme = 0\n',
			'reload-on-export = true\n',
			'hijack-target = ""\n'
		])
