import json
from pathlib import Path
from .material import MaterialMode, GameTarget, NormalType

class Preset():
	paths: dict[str, Path]
	name: str | None = None
	game: GameTarget = GameTarget.V2011
	mode: MaterialMode = MaterialMode.PhongEnvmap
	normalType: NormalType = NormalType.DX
	scaleTarget: int = 0

	def __init__(self) -> None:
		self.paths = {}

	@staticmethod
	def load(pathStr: str):
		path = Path(pathStr)
		folder = path.parent.absolute()
		preset = Preset()
	
		with open(path, 'r') as file:
			rawDict: dict = json.load(file)
			pathDict = rawDict['paths']

			if name := rawDict.get('name', None):
				preset.name = name

			if isinstance(game := rawDict.get('game', None), int):
				preset.game = GameTarget(game)

			if isinstance(mode := rawDict.get('mode', None), int):
				preset.mode = MaterialMode(mode)

			normalType: NormalType | None
			if isinstance(normalType := rawDict.get('normalType', None), int):
				preset.normalType = NormalType(normalType)

			scaleTarget: int | None
			if isinstance(scaleTarget := rawDict.get('scaleTarget', None), int):
				preset.scaleTarget = scaleTarget

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
				'name': self.name,
				'game': self.game,
				'mode': self.mode,
				'normalType': self.normalType,
				'scaleTarget': self.scaleTarget,
				'paths': outPaths
			}, file, indent=4)
