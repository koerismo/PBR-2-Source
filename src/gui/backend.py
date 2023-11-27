from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QImage, QColorSpace
from PySide6.QtCore import Qt

from core import texops
from core.convert import export as core_export
from core.io.image import Image
from core.material import Material, MaterialMode, GameTarget

from enum import IntEnum
import numpy as np

class ImageRole(IntEnum):
	Albedo = 0
	Roughness = 1
	Metallic = 2
	Emit = 3
	AO = 4
	Normal = 5
	Height = 6

class CoreBackend():
	albedo: Image|None
	roughness: Image|None
	metallic: Image|None
	emit: Image|None
	ao: Image|None
	normal: Image|None
	height: Image|None

	name: str
	game: GameTarget
	mode: MaterialMode

	def __init__(self) -> None:
		pass

	def open_file(self, path: str, role: ImageRole) -> QImage:
		image = QImage()
		image.load(path)
		image.convertToColorSpace(QColorSpace.NamedColorSpace.SRgbLinear)
		image.convertToFormat_inplace(QImage.Format.Format_RGBA32FPx4, Qt.ImageConversionFlag.AvoidDither)

		ptr = image.constBits()
		arr = np.array(ptr).reshape(image.width(), image.height(), 4)
		converted = Image(arr)

		match role:
			case ImageRole.Albedo: self.albedo = converted
			case ImageRole.Roughness: self.roughness = converted
			case ImageRole.Metallic: self.metallic = converted
			case ImageRole.Emit: self.emit = converted
			case ImageRole.AO: self.ao = converted
			case ImageRole.Normal: self.normal = converted
			case ImageRole.Height: self.height = converted

		return image

	def export(self):
		albedo = self.albedo
		assert albedo != None

		roughness = self.roughness
		assert roughness != None

		metallic = self.metallic or Image.blank(roughness.size, (0.0,))
		emit = self.emit
		ao = self.ao
		normal = self.normal or Image.blank(roughness.size, (0.5, 0.5, 1.0))
		height = self.height or Image.blank(normal.size, (0.5,))

		Material(
			self.mode,
			GameTarget.V2011,
			normal.size,
			self.name,
			albedo=texops.normalize(albedo, mode='RGB'),
			roughness=texops.normalize(roughness, normal.size, mode='L'),
			metallic=texops.normalize(metallic, normal.size, mode='L'),
			emit=texops.normalize(emit, albedo.size, mode='L') if emit else None,
			ao=texops.normalize(ao, albedo.size, mode='L') if ao else None,
			normal=texops.normalize(normal, mode='RGB'),
			height=texops.normalize(height, normal.size, mode='L') if height else None
		)
