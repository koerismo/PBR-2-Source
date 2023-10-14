from srctools.keyvalues import Keyvalues
from .material import Material, MaterialMode

def make_vmt(mat: Material) -> Keyvalues:
	pbr = mat.mode < 2
	plainshader = "VertexLitGeneric" if mat.name.startswith("models") else "LightmappedGeneric"
	shader = "PBR" if pbr else plainshader
	root = Keyvalues(shader, [])

	with root.build() as vmt:
		vmt["$basetexture"]			(mat.name + "_albedo")
		vmt["$bumpmap"]				(mat.name + "_bump")

		if pbr:
			vmt["$mraotexture"]		(mat.name + "_mrao")
			vmt["$emissiontexture"]	(mat.name + "_emit")
			vmt["$model"]			("1" if mat.mode == MaterialMode.PBRModel else "0")

		else:
			vmt["$envmap"]						("env_cubemap")
			vmt["$envmaptint"]					("[.05 .05 .05]")
			vmt["$envmapcontrast"]				("1.0")

			vmt["$phong"]						("1")
			vmt["$phongexponenttexture"]		(mat.name + "_phong")
			vmt["$phongfresnelranges"]			("[0.2 0.8 1.0]")
			vmt["$phongboost"]					("5.0")

			if mat.mode == MaterialMode.PhongEnvmapEmit:
				vmt["$selfillum"]				("1")
				vmt["$selfillummask"]			(mat.name + "_emit")

			if mat.mode == MaterialMode.PhongEnvmapAlpha:
				vmt["$alphatest"]				("1")

	return root
