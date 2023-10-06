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
	size: (int, int)
	name: str

	albedo: Image|None		# Linear RGB
	specular: Image|None	# Linear RGB
	glossy: Image|None		# Linear L
	emit: Image|None		# Linear RGB
	ao: Image|None			# Linear L

	normal: Image|None		# Linear XYZ
	height: Image|None		# Linear L

	def __init__(self,
			mode: MaterialMode,
			size: (int, int),
			name: str,

			albedo: Image=None,
			specular: Image=None,
			glossy: Image=None,
			emit: Image=None,
			ao: Image=None,
			
			normal: Image=None,
			height: Image=None):

		self.mode = mode
		self.size = size

		self.albedo = albedo
		self.glossy = glossy
		self.specular = specular
		self.emit = emit
		self.ao = ao

		self.normal = normal
		self.height = height