import json
from pathlib import Path
from .core.material import MaterialMode, GameTarget

class Preset():
	paths: dict[str, Path] = {}
	game: GameTarget = GameTarget.V2011
	mode: MaterialMode = MaterialMode.PBRModel

	@staticmethod
	def load(pathStr: str):
		path = Path(pathStr)
		folder = path.parent.absolute()
		preset = Preset()
	
		with open(path, 'r') as file:
			rawDict = json.load(file)
			pathDict = rawDict['paths']

			game: GameTarget
			if isinstance(game := rawDict.get('game', 0), int):
				preset.game = game
			
			mode: MaterialMode
			if isinstance(mode := rawDict.get('mode', 0), int):
				preset.mode = mode

			for key in pathDict:
				value = pathDict[key]
				result = folder / value
				if not result.is_file(): continue
				preset.paths[key] = result

		return preset
	
	def get_path(self, key: str):
		return self.paths.get(key)
	
	def get_path_str(self, key: str):
		p = self.paths.get(key)
		return str(p) if p else None
	
	def set_path(self, key: str, value: str|Path|None):
		if value == None:
			if key in self.paths:
				del self.paths[key]
		else:
			value = Path(value)
			self.paths[key] = value
	
	def save(self, pathStr: str):
		path = Path(pathStr)
		folder = path.parent.absolute()

		with open(path, 'w') as file:
			outPaths: dict[str, str] = {}

			for key in self.paths:
				value = self.paths[key]
				try:				value = value.relative_to(folder)
				except Exception: 	value = value.absolute()
				outPaths[key] = str(value)
			
			json.dump({
				'game': self.game,
				'mode': self.mode,
				'paths': outPaths
			}, file, indent=4)
