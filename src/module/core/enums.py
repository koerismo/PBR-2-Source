from enum import IntEnum

class ImageFlags(IntEnum):
	PointSample					= 1 <<  0
	Trilinear					= 1 <<  1
	ClampS						= 1 <<  2
	ClampT						= 1 <<  3
	Anistrophic					= 1 <<  4
	PWLCorrected				= 1 <<  6
	LoadAllMips					= 1 << 10
	NoDebugOverride				= 1 << 17
	SingleCopy					= 1 << 18
	sRGB						= 1 << 19
	# DefaultPool				= 1 << 20
	# TF2_IgnorePickup			= 1 << 21
	# NoDepthBuffer				= 1 << 23
	# CSGO_SkipInitialDownload	= 1 << 24
	ClampU						= 1 << 25
	VertexTexture				= 1 << 26
	SSBump						= 1 << 27
	# LoadMostMips				= 1 << 28
	Border						= 1 << 29
	# StreamableCoarse			= 1 << 30
