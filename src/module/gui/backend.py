# from PySide6.QtCore import Signal, Slot
# from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QColorSpace

from ..core.io.qtio import QtIOBackend, qimage_to_image, image_to_qimage

from ..core import texops
from ..core.convert import export as core_export
from ..core.vmt import make_vmt as core_make_vmt
from ..core.io.image import Image
from ..core.material import Material, MaterialMode, GameTarget, NormalType
from ..preset import Preset
from ..logger import log

from pathlib import Path
from enum import StrEnum
from typing import Callable

class ImageRole(StrEnum):
	Albedo = 'albedo'
	Roughness = 'roughness'
	Metallic = 'metallic'
	Emit = 'emit'
	AO = 'ao'
	Normal = 'normal'
	Height = 'height'

class CoreBackend():
	albedo: Image|None = None
	roughness: Image|None = None
	metallic: Image|None = None
	emit: Image|None = None
	ao: Image|None = None
	normal: Image|None = None
	height: Image|None = None

	albedoPath: str|None = None
	roughnessPath: str|None = None
	metallicPath: str|None = None
	emitPath: str|None = None
	aoPath: str|None = None
	normalPath: str|None = None
	heightPath: str|None = None

	path: Path|None = None
	# envmap: str = 'env_cubemap'
	name: str = 'ThisShouldNeverAppear'
	game: GameTarget = Preset.game
	mode: MaterialMode = Preset.mode
	normalType: NormalType = Preset.normalType
	scaleTarget: int = Preset.scaleTarget

	def __init__(self) -> None:
		pass

	def load_preset(self, preset: Preset):
		self.game = preset.game
		self.mode = preset.mode
		pass
	
	def save_preset(self, preset: Preset):
		preset.game = self.game
		preset.mode = self.mode
		preset.normalType = self.normalType
		preset.scaleTarget = self.scaleTarget
		preset.set_path(ImageRole.Albedo, self.albedoPath)
		preset.set_path(ImageRole.Roughness, self.roughnessPath)
		preset.set_path(ImageRole.Metallic, self.metallicPath)
		preset.set_path(ImageRole.Emit, self.emitPath)
		preset.set_path(ImageRole.AO, self.aoPath)
		preset.set_path(ImageRole.Normal, self.normalPath)
		preset.set_path(ImageRole.Height, self.heightPath)

	def convert(self, path: str, role: ImageRole) -> tuple[QImage, Image]:
		image: QImage = QImage()
		converted: Image|None = None
		if path.endswith('.vtf') or path.endswith('.hdr'):
			converted = QtIOBackend.load(path)
			image = image_to_qimage(converted)
		else:
			image = QtIOBackend.load_qimage(path)
			converted = qimage_to_image(image)

		match role:
			case ImageRole.Albedo: self.albedo = converted
			case ImageRole.Roughness: self.roughness = converted
			case ImageRole.Metallic: self.metallic = converted
			case ImageRole.Emit: self.emit = converted
			case ImageRole.AO: self.ao = converted
			case ImageRole.Normal: self.normal = converted
			case ImageRole.Height: self.height = converted

		# converted.convert(np.uint8).save('./TEST.vtf')
		return (image, converted)

	def pick(self, path: str|None, role: ImageRole) -> QImage|None:
		# Update current path
		self.__setattr__(role+'Path', path)
			
		if path:
			# Cache image
			return self.convert(path, role)[0]
		else:
			# Remove cached image
			self.__setattr__(role, None)
			return None

	def pick_vmt(self, pathStr: str):
		path = Path(pathStr)
		self.path = path.parent

		name = path.name.removesuffix('.vmt')
		namePath = ''
		useNamePath = False
		for component in reversed(path.parts[:-1]):
			if component == 'materials':
				useNamePath = True
				break
			namePath = component + '/' + namePath

		self.name = namePath+name if useNamePath else name

	def make_material(self, noCache: bool=False):
		''' Generate the material from the collected textures. '''

		def getImage(role: ImageRole) -> Image|None:
			''' Helper function for re-fetching images when the cache is disabled. '''
			if noCache:
				rolePath = self.__getattribute__(role+'Path')
				if rolePath == None: return None
				return self.convert(rolePath, role)[1]
			return self.__getattribute__(role)

		albedo = getImage(ImageRole.Albedo)
		assert albedo != None, 'A basetexture is required to convert the material!'

		roughness = getImage(ImageRole.Roughness)
		assert roughness != None, 'A roughness map is required to convert the material!'

		metallic = getImage(ImageRole.Metallic) or Image.blank(roughness.size, (0.0,))
		emit = getImage(ImageRole.Emit)
		ao = getImage(ImageRole.AO)
		normal = getImage(ImageRole.Normal) or Image.blank(roughness.size, (0.5, 0.5, 1.0))
		height = getImage(ImageRole.Height) or Image.blank(normal.size, (0.5,))

		texSize = (self.scaleTarget, self.scaleTarget) if (self.scaleTarget and self.scaleTarget <= albedo.size[0]) else albedo.size
		detailSize = (texSize[0]*2, texSize[1]*2) if (self.scaleTarget and texSize[0]*2 <= normal.size[0]) else normal.size
		log.info('Determined size', texSize, 'for albedo and', detailSize, 'for details via scale target', self.scaleTarget)

		log.info('Constructing material...')

		return Material(
			self.mode,
			self.game,
			texSize,
			detailSize,
			self.name,
			albedo=texops.normalize(albedo, detailSize, mode='RGB'),
			roughness=texops.normalize(roughness, detailSize, mode='L'),
			metallic=texops.normalize(metallic, detailSize, mode='L'),
			emit=texops.normalize(emit, detailSize, noAlpha=True) if emit else None,
			ao=texops.normalize(ao, detailSize, mode='L') if ao else None,
			normal=texops.normalize(normal, detailSize, mode='RGB'),
			height=texops.normalize(height, detailSize, mode='L') if height else None,
			normalType=self.normalType
		)

	def export(self, material: Material, callback: Callable[[str], None] | None = None):
		assert self.path != None and self.name != None, 'Something has gone very very wrong. Find a developer!'

		# TODO: This is kinda dumb
		material.name = self.name

		if callback:
			callback('Processing textures...')

		textures = core_export(material)
		textureVersion = GameTarget.vtf_version(material.target)

		if callback:
			callback('Making VMT...')

		vmt = core_make_vmt(material)
		
		isolatedName = self.name.rsplit('/', 1)[-1]
		vmtPath = self.path / (isolatedName + '.vmt')

		if callback:
			callback('Writing files...')

		with open(vmtPath, 'w') as vmtFile:
			vmtFile.write(vmt)

		for texture in textures:
			fullPath = self.path / (isolatedName + texture.name + '.vtf')
			texture.image.save(fullPath, version=textureVersion, compressed=texture.compressed)

		if callback:
			callback(f'Finished exporting {isolatedName}.vmt!')
