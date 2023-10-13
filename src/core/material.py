from .io.image import Image
from enum import IntEnum

class MaterialMode(IntEnum):
	PBRModel = 0			# PBR model mode
	PBRBrush = 1			# PBR brush mode
	PhongEnvmap = 2			# Phong mask is in normal map alpha, envmap uses basetexture alpha
	PhongEnvmapAlpha = 3	# Phong mask is in normal map alpha, envmap uses its own mask
	PhongEnvmapEmit = 4		# Phong mask is in normal map alpha, envmap uses its own mask, emission uses basetexture alpha

class MaterialTarget(IntEnum):
	PBR = 0
	LightmappedGeneric = 1
	VertexLitGeneric = 2

class NormalType(IntEnum):
	GL = 0
	DX = 1

class Material:
	mode: MaterialMode
	size: tuple[int, int]
	name: str

	albedo: Image			# Linear RGBAf
	roughness: Image		# Linear f
	metallic: Image			# Linear f
	emit: Image|None		# Linear RGBf
	ao: Image|None			# Linear f

	normal: Image			# Linear RGBAf
	normal_type: NormalType

	height: Image|None		# Linear f

	def __init__(self,
			mode: MaterialMode,
			size: tuple[int, int],
			name: str,

			albedo: Image,
			roughness: Image,
			metallic: Image,
			emit: Image|None,
			ao: Image|None,

			normal: Image,
			height: Image|None):

		self.mode = mode
		self.size = size
		self.name = name

		self.albedo = albedo
		self.roughness = roughness
		self.metallic = metallic
		self.emit = emit
		self.ao = ao

		self.normal = normal
		self.height = height

class Texture():
	image: Image
	name: str

	def __init__(self, image: Image, name: str) -> None:
		self.image = image
		self.name = name