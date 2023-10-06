from PIL.Image import Image
from enum import IntEnum

class MaterialMode(IntEnum):
	PBRModel = 0			# PBR model mode
	PBRBrush = 1			# PBR brush mode
	PhongEnvmap = 2			# Phong mask is in normal map alpha, envmap uses basetexture alpha
	PhongEnvmapAlpha = 3	# Phong mask is in normal map alpha, envmap uses its own mask
	PhongEnvmapEmit = 4		# Phong mask is in normal map alpha, envmap uses its own mask, emission uses basetexture alpha

class Material:
	mode: MaterialMode
	size: tuple[int, int]
	name: str

	albedo: Image			# Linear RGB
	specular: Image			# Linear RGB
	glossy: Image			# Linear L
	emit: Image|None		# Linear RGB
	ao: Image|None			# Linear L

	normal: Image			# Linear XYZ
	height: Image|None		# Linear L

	def __init__(self,
			mode: MaterialMode,
			size: tuple[int, int],
			name: str,

			albedo: Image,
			specular: Image,
			glossy: Image,
			emit: Image|None,
			ao: Image|None,

			normal: Image,
			height: Image|None):

		self.mode = mode
		self.size = size
		self.name = name

		self.albedo = albedo
		self.specular = specular
		self.glossy = glossy
		self.emit = emit
		self.ao = ao

		self.normal = normal
		self.height = height
