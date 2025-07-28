# from PySide6.QtCore import Signal, Slot
# from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtCore import Signal, QObject

from ..core.io.qtio import QtIOBackend, qimage_to_image, image_to_qimage
from ..core import texops
from ..core.export import export as core_export
from ..core.vmt import make_vmt as core_make_vmt
from ..core.io.image import Image
from ..core.material import Material, MaterialMode, GameTarget, NormalType
from ..core.config import get_config, HijackMode
from ..core.preset import Preset
import logging as log
from math import ceil, log2
from time import perf_counter

from pathlib import Path
from enum import StrEnum
from typing import Callable

import sys
from sourcepp import gamepp
from socket import socket

class ImageRole(StrEnum):
	Albedo = 'albedo'
	Roughness = 'roughness'
	Metallic = 'metallic'
	Emit = 'emit'
	AO = 'ao'
	Normal = 'normal'
	Height = 'height'

# Used as a default dummy callback by export()
CALLBACK_NONE = lambda _a, _b: None

class CoreBackend(QObject):

	# This event is triggered when a file is picked or when a preset is loaded.
	role_updated = Signal( ImageRole, str, QImage, name='RoleUpdated' )

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
	name: str = 'ThisShouldNeverAppear'
	game: GameTarget = Preset.game
	mode: MaterialMode = Preset.mode
	normalType: NormalType = Preset.normalType
	scaleTarget: int = Preset.scaleTarget

	def __init__(self) -> None:
		super().__init__()

	def get_role_path(self, role: ImageRole) -> str:
		return getattr(self, role+'Path')
	
	def get_role_image(self, role: ImageRole) -> Image:
		return getattr(self, role)

	def set_role_path(self, role: ImageRole, path: str):
		setattr(self, role+'Path', path)

	def load_preset(self, preset: Preset):
		# Other properties are handled by widgets
		for role in ImageRole:
			self.set_role_image(preset.get_path_str(role), role)
	
	def save_preset(self, preset: Preset):
		preset.name = self.name
		preset.game = self.game
		preset.mode = self.mode
		preset.normalType = self.normalType
		preset.scaleTarget = self.scaleTarget
		for role in ImageRole:
			preset.set_path(role, self.get_role_path(role))

	def __load_image__(self, path: str) -> tuple[QImage, Image]:
		''' Loads the specified path as an image, returning a (QImage, Image) tuple. '''
		image: QImage = QImage()
		converted: Image|None = None

		if path.endswith('.vtf') or path.endswith('.hdr'):
			converted = QtIOBackend.load(path)
			image = image_to_qimage(converted)
		else:
			image = QtIOBackend.load_qimage(path)
			converted = qimage_to_image(image)

		return (image, converted)

	def set_role_image(self, path: str|None, role: ImageRole) -> tuple[QImage, Image] | tuple[None, None]:
		''' Loads the specified path and sets the specified backend image. This method emits the image_updated signal! '''
		conv: tuple[QImage, Image] | tuple[None, None] = (None, None)

		if path:
			# Load and cache image
			conv = self.__load_image__(path)
			setattr(self, role, conv[1])
		else:
			# Remove cached image
			setattr(self, role, None)

		# Update current path
		setattr(self, role+'Path', path)

		self.role_updated.emit(role, path, conv[0])
		return conv

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

	def make_material(self, *, noCache: bool=False):
		''' Generate the material from the collected textures. '''

		TIME_BEFORE = perf_counter()

		def getImage(role: ImageRole) -> Image|None:
			''' Helper function for re-fetching images when the cache is disabled. '''
			if noCache:
				rolePath = self.__getattribute__(role+'Path')
				if rolePath == None: return None
				return self.set_role_image(rolePath, role)[1]
			return self.__getattribute__(role)

		albedo = getImage(ImageRole.Albedo)
		assert albedo != None, 'A basetexture is required to convert the material!'

		roughness = getImage(ImageRole.Roughness)
		assert roughness != None, 'A roughness map is required to convert the material!'

		metallic = getImage(ImageRole.Metallic) or Image.blank(roughness.size, (0.0,))
		emit = getImage(ImageRole.Emit)
		ao = getImage(ImageRole.AO)
		normal = getImage(ImageRole.Normal) or Image.blank(roughness.size, (0.5, 0.5, 1.0))
		height = getImage(ImageRole.Height)

		TIME_AFTER = perf_counter()
		log.debug(f'(Re)loaded images in {round(TIME_AFTER - TIME_BEFORE, 4)}ms (noCache={noCache})')

		def to_pow2(x: float) -> int:
			return pow(2, ceil(log2(int(x))))

		albedoWidth, albedoHeight = albedo.size
		albedoMaxSize = max(albedoWidth, albedoHeight)
		texScale      = (min(albedoMaxSize, self.scaleTarget) / albedoMaxSize) if self.scaleTarget else 1
		texDims       = (to_pow2(albedoWidth * texScale), to_pow2(albedoHeight * texScale))
	
		log.info(f'Determined size {texDims} via scale target {self.scaleTarget}')

		log.info('Constructing material...')

		return Material(
			self.mode,
			self.game,
			texDims,
			self.name,
			albedo=texops.normalize(albedo, texDims, mode='RGBA'),
			roughness=texops.normalize(roughness, texDims, mode='L'),
			metallic=texops.normalize(metallic, texDims, mode='L'),
			emit=texops.normalize(emit, texDims, noAlpha=True) if emit else None,
			ao=texops.normalize(ao, texDims, mode='L') if ao else None,
			normal=texops.normalize(normal, texDims, mode='RGB'),
			height=texops.normalize(height, texDims, mode='L') if height else None,
			normalType=self.normalType
		)

	def export(self, material: Material, callback: Callable[[str|None, int|None], None] = CALLBACK_NONE, overwrite_vmt=True):
		assert self.path != None and self.name != None, 'Something has gone very very wrong. Find a developer!'

		appConfig = get_config()

		# TODO: This is kinda dumb
		material.name = self.name

		callback('Processing textures...', 20)

		TIME_BEFORE = perf_counter()
		
		textures = core_export(material)
		textureVersion = GameTarget.vtf_version(material.target)
		textureCount = len(textures)

		TIME_AFTER = perf_counter()
		log.debug(f'Processed textures in {round(TIME_AFTER - TIME_BEFORE, 4)}ms')

		materialName = self.name.rsplit('/', 1)[-1]
		vmtPath = self.path / (materialName + '.vmt')
		shouldWriteVmt = overwrite_vmt or (not Path(vmtPath).exists())

		callback(None, 50)
		if shouldWriteVmt:
			callback('Writing VMT...', None)
			vmt = core_make_vmt(material)
			with open(vmtPath, 'w') as vmtFile:
				vmtFile.write(vmt)
		else:
			log.info('Skipped generating VMT! (overwriteVmts is False)')

		callback(f'Writing textures...', 60)

		for i, texture in enumerate(textures):
			textureConfig = appConfig.targets[texture.role]
			fullPath = self.path / (materialName + textureConfig.postfix + '.vtf')
			texture.image.save(
				fullPath,
				version=textureVersion,
				lossy=textureConfig.lossy,
				zip=textureConfig.zip,
				flags=textureConfig.flags,
				mipmaps=textureConfig.mipmaps,
			)
			callback(f'Writing textures... [{i+1}/{textureCount}]', 60 + int((i+1) / textureCount * 40))

		if shouldWriteVmt:
			callback(f'Finished exporting {materialName}.vmt!', 100)
		else:
			callback(f'Finished exporting {materialName}_*.vtf!', 100)

	def send_engine_command(self, cmd: str) -> bool:
		config = get_config()
	
		match config.hijackMode:
			case HijackMode.Disabled:
				return False
			
			case HijackMode.Windows:
				if sys.platform == 'win32':
					gi = gamepp.GameInstance.find()
					gi.command(cmd)
					return True
				else:
					log.error('SendMessage hijacking is only available on Windows systems!')
					return False
			
			case HijackMode.NetCon:
				sock = socket()
				sock_err = sock.connect_ex(('localhost', config.hijackPort))
				if sock_err != 0:
					log.error(f'Failed to open socket! (errcode={sock_err})')
					return False

				sock.send((cmd + '\n').encode())
				sock.close()
				return True
