import json
from pathlib import Path

class Preset():
	keys: dict[str, Path] = {}

	@staticmethod
	def load(pathStr: str):
		path = Path(pathStr)
		folder = path.parent.absolute()
		preset = Preset()
	
		with open(path, 'r') as file:
			rawDict = json.load(file)
			for key in rawDict:
				value = rawDict[key]
				result = folder / value
				if not result.is_file(): continue
				preset.keys[key] = result

		return preset
	
	def get(self, key: str):
		return self.keys.get(key)
	
	def get_str(self, key: str):
		p = self.keys.get(key)
		return str(p) if p else None
	
	def set(self, key: str, value: str|Path|None):
		if value == None:
			if key in self.keys:
				del self.keys[key]
		else:
			print('Making path from ', value)
			value = Path(value)
			self.keys[key] = value

	def count(self):
		return len(self.keys)
	
	def save(self, pathStr: str):
		path = Path(pathStr)
		folder = path.parent.absolute()

		with open(path, 'w') as file:
			outDict: dict[str, str] = {}

			for key in self.keys:
				value = self.keys[key]
				try:				value = value.relative_to(folder)
				except Exception: 	value = value.absolute()
				outDict[key] = str(value)
			
			json.dump(outDict, file, indent=4)
