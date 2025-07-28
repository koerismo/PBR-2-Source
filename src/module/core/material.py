from .io.image import Image
from .config import TargetRole
from enum import IntEnum

class MaterialMode(IntEnum):
	PBRModel			= 0		# PBR: PBR model mode
	PBRBrush			= 1		# PBR: PBR brush mode
	Phong				= 10	# VertexLitGeneric: Phong mask is in normal map alpha
	PhongEnvmap			= 11	# VertexLitGeneric: Phong mask is in normal map alpha, envmap uses basetexture alpha
								# GMOD: phong mask uses basetexture alpha, envmap mask uses normal map alpha
	PhongEnvmapAlpha	= 12	# VertexLitGeneric: Phong mask is in normal map alpha, envmap uses its own mask
	PhongEnvmapEmit		= 13	# VertexLitGeneric: Phong mask is in normal map alpha, envmap uses its own mask, emission uses basetexture alpha
	Envmap				= 20	# LightmappedGeneric: Envmap uses basetexture alpha
	EnvmapAlpha			= 21	# LightmappedGeneric: Envmap uses its own mask
	EnvmapEmit			= 22	# LightmappedGeneric: Envmap uses ist own mask, emission uses basetexture alpha

	@staticmethod
	def is_pbr(mat: 'MaterialMode'): return mat <= 1

	@staticmethod
	def is_model(mat: 'MaterialMode'): return mat == 0 or (mat >= 10 and mat <= 13)

	@staticmethod
	def has_phong(mat: 'MaterialMode'): return mat >= 10 and mat <= 13

	@staticmethod
	def has_envmap(mat: 'MaterialMode'): return mat >= 11 and mat <= 22

	@staticmethod
	def is_vlg(mat: 'MaterialMode'): return mat >= 10 and mat <= 13

	@staticmethod
	def has_alpha(mat: 'MaterialMode'): return mat == 12 or mat == 21

	@staticmethod
	def has_selfillum(mat: 'MaterialMode'): return mat == 13 or mat == 22

	@staticmethod
	def get_shader(mat: 'MaterialMode'):
		if mat <= 1:  return 'PBR'
		if mat <= 13: return 'VertexLitGeneric'
		return 'LightmappedGeneric'

	@staticmethod
	def embed_envmap(mat: 'MaterialMode'):
		return mat == MaterialMode.Envmap or mat == MaterialMode.PhongEnvmap

	@staticmethod
	def embed_selfillum(mat: 'MaterialMode'):
		return mat == MaterialMode.PhongEnvmapEmit or mat == MaterialMode.EnvmapEmit

class GameTarget(IntEnum):
	V2007 = 1	# EP2, Portal, TF2
	VGMOD = 2	# Garry's Mod
	V2011 = 3	# Alien Swarm, Portal 2
	V2023 = 4	# CS:GO, Strata Source

	@staticmethod
	def vtf_version(target: 'GameTarget'):
		if target >= GameTarget.V2011: return 5
		if target <= GameTarget.V2007: return 2
		return 3


class NormalType(IntEnum):
	GL = 0
	DX = 1

class Material:
	mode: MaterialMode
	target: GameTarget
	size: tuple[int, int]
	name: str

	albedo: Image			# Linear RGBAf
	roughness: Image		# Linear f
	metallic: Image			# Linear f
	emit: Image|None		# Linear RGBf
	ao: Image|None			# Linear f

	normal: Image			# Linear RGBAf
	normalType: NormalType = NormalType.DX

	height: Image|None		# Linear f

	def __init__(self,
			mode: MaterialMode,
			target: GameTarget,
			size: tuple[int, int],
			name: str,

			albedo: Image,
			roughness: Image,
			metallic: Image,
			emit: Image|None,
			ao: Image|None,

			normal: Image,
			height: Image|None,
			normalType: NormalType=NormalType.DX):

		self.mode = mode
		self.target = target
		self.size = size
		self.name = name

		self.albedo = albedo
		self.roughness = roughness
		self.metallic = metallic
		self.emit = emit
		self.ao = ao

		self.normal = normal
		self.normalType = normalType
		self.height = height
	
	def swap_phong_envmap(self):
		''' If true, phong mask uses basetexture alpha, and envmap mask uses normal map alpha. '''
		return self.target == GameTarget.VGMOD and self.mode == MaterialMode.PhongEnvmap

class Texture():
	image: Image
	role: TargetRole

	def __init__(self, image: Image, role: TargetRole) -> None:
		self.image = image
		self.role = role
