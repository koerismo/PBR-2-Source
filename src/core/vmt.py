from srctools.keyvalues import Keyvalues
from .material import Material, MaterialMode


'''
"VertexLitGeneric"
{
	$basetexture "pbr2source_test0_albedo"
	$bumpmap "pbr2source_test0_bump"

	$envmap "env_cubemap"
	$envmaptint "[.05 .05 .05]"
	$envmapcontrast 1.0

	$phong 1
	$phongfresnelranges "[0.2 0.8 1.0]"
	$phongexponenttexture "pbr2source_test0_phongexp"
	$phongboost 1.0
}
'''


def make_vmt(mat: Material) -> Keyvalues:

	pbr = mat.mode < 2
	shader = "PBR" if pbr else "LightmappedGeneric"
	root = Keyvalues(shader, [])

	with root.build() as vmt:
		vmt["$basetexture"]			(mat.name + "_albedo")

		if pbr:
			vmt["$mraotexture"]		(mat.name + "_mrao")
			vmt["$emissiontexture"]	(mat.name + "_emit")
			vmt["$model"]			("1" if mat.mode == MaterialMode.PBRModel else "0")

		else:
			vmt["$envmap"]						("env_cubemap")
			vmt["$envmapmask"]					(mat.name + "_envmask")
			vmt["$envmaplightscale"]			("1")
			vmt["$envmaplightscaleminmax"]		("[0 1.0]")
			# vmt["$normalmapalphaenvmapmask"]	("1")
			vmt["$fresnelreflection"]			("1")

			vmt["$phongexponenttexture"]		(mat.name + "_phong")
			# vmt["$phongexponentfactor"]			("256")
			vmt["$phongboost"]					("10")

			if mat.mode == MaterialMode.PhongEnvmapEmit:
				vmt["$selfillum"]				("1")
				vmt["$selfillummask"]			(mat.name + "_emit")

			if mat.mode == MaterialMode.PhongEnvmapAlpha:
				vmt["$alphatest"]				("1")

	return root