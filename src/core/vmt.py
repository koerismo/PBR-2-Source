from srctools.keyvalues import Keyvalues
from .material import Material, MaterialMode

def make_vmt(mat: Material) -> Keyvalues:

	pbr = mat.mode < 3
	shader = "PBR" if pbr else "VertexLitGeneric"
	root = Keyvalues(shader, [])

	with root.build() as vmt:
		vmt["$basetexture"]						= mat.name + "_albedo"

		if pbr:
			vmt["$mraotexture"]					= mat.name + "_mrao"
			vmt["$emissiontexture"]				= mat.name + "_emit"
			vmt["$model"]						= int(mat.mode == MaterialMode.PBRModel)
		else:
			vmt["$envmapmask"]					= mat.name + "_envmask"
			vmt["$phongexponenttexture"]		= mat.name + "_phong"
			vmt["$fresnelreflection"]			= 1
			vmt["$envmaplightscale"]			= 1
			vmt["$envmaplightscaleminmax"]		= "[0 1.1]"
			vmt["$normalmapalphaenvmapmask"]	= 1

			if mat.mode == MaterialMode.PhongEnvmapEmit:
				vmt["$selfillum"]				= 1
				vmt["$selfillummask"]			= mat.name + "_emit"

			if mat.mode == MaterialMode.PhongEnvmapAlpha:
				vmt["$alphatest"]				= 1

	return root