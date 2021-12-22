from PIL.ImageOps import flip
from PySide6.QtWidgets import QApplication, QMessageBox, QErrorMessage, QFileDialog
from gui import mainWin
from pathlib import Path
from math import log2

from os.path import join as joinPath
from tempfile import gettempdir

from PIL import Image, ImageChops
from srctools import VTF
from srctools.vtf import ImageFormats as VTFFormats

class frontend( mainWin ):
	def __init__( self ):
		super().__init__()

		self.data = {
			'OutputShader': 'LightmappedGeneric',
			'OutputEnvmap': 'None',
			'OutputReflectIntensity': 30,
			'ImageDiffuse': None,
			'ImageRoughness': None,
			#'ImageMetallic': None,
			'ImageNormal': None,
			'SizeOverride': False
		}

		self.exportBtn.setDisabled( True )

	def setProperty( self, property, value ):
		self.data[property] = value

		self.exportBtn.setEnabled( all([
			self.data['ImageDiffuse'],
			self.data['ImageRoughness'],
			#self.data['ImageMetallic'],
			self.data['ImageNormal']
		]) )

	def getPathRelative( self, origpath:Path ):
		newpath = origpath
		while newpath.name != 'materials' and newpath != newpath.parent:
			newpath = newpath.parent
		
		if newpath == newpath.parent: return None
		return origpath.relative_to( newpath )
	
	def removeSuffix( self, path:Path ):
		if path is None: return None
		return Path( str(path)[:-len(path.suffix)] )

	def doExport( self ):

		''' ---------- CHECK IMAGES ---------- '''

		def checkImageSize( img ):
			def isPowerOfTwo( v ): return log2(v)%1 == 0
			return isPowerOfTwo(img.width) and isPowerOfTwo(img.height)

		for img in [
			self.data['ImageDiffuse'],
			#self.data['ImageMetallic'], # Roughness is baked into the ImageDiffuse texture, so it'll be resized anyways.
			self.data['ImageNormal']]:
			if img is None: continue
			if not checkImageSize( img ):
				msg = QErrorMessage( self )
				msg.showMessage( 'An image has a non-power of two size!' )
				msg.activateWindow()
				return


		''' ---------- DO PATH MAGIC ---------- '''

		rawpath = QFileDialog.getSaveFileName( caption='Create material', filter='Valve Material Type (*.vmt)' )
		if not len(rawpath[0]): return
		path = rawpath[0]

		vmtPathRelative = self.removeSuffix(self.getPathRelative( Path(path) ))

		if vmtPathRelative is None:
			msg = QErrorMessage( self )
			msg.setWindowTitle( 'Error' )
			msg.showMessage( 'Failed to find materials directory! Be sure that you are exporting into a content folder.' )
			msg.activateWindow()
			return

		vmtPathStr = str( vmtPathRelative ).replace( '\\', '/' )
		vmtDirRelative = vmtPathRelative.parent


		''' ---------- WRITE VMT ---------- '''

		self.progressBar.setValue( 1 )

		with open( path, 'w' ) as vmt:
			if self.data['OutputEnvmap'] == None:
				vmt.writelines([
					'"'+self.data.get('OutputShader')+'"\n',
					'{\n',
					'    $basetexture          "'+vmtPathStr+'_basecolor"\n',
					'    $bumpmap              "'+vmtPathStr+'_bump"\n',
					'}'
				])
			else:
				vmt.writelines([
					'"'+self.data.get('OutputShader')+'"\n',
					'{\n',
					'    $basetexture          "'+vmtPathStr+'_basecolor"\n',
					'    $bumpmap              "'+vmtPathStr+'_bump"\n',
					'\n',
					'    $envmap               "'+self.data['OutputEnvmap']+'"\n',
					'    $envmaptint           '+str(round(self.data['OutputReflectIntensity']/100,2))+'\n',
					'    $envmaplightscale     0.98\n',
					'    $basealphaenvmapmask  1\n',
					'}'
				])

		''' ---------- PROCESS BASETEXTURE ---------- '''

		self.progressBar.setValue( 2 )

		def applyAlphaToTexture( tex:Image, alpha:Image ):
			r, g, b = tex.split()
			r2, g2, b2 = alpha.split()
			return Image.merge( 'RGBA', (r, g, b, r2) )

		# Register basetexture

		BaseTexture = self.data['ImageDiffuse'].convert('RGB')
		if self.data['SizeOverride']: BaseTexture = BaseTexture.resize( (self.data['SizeOverride'], self.data['SizeOverride']) )

		# Register AO, Apply AO to basetexture

		AOTexture = None
		if self.data.get('ImageAo') != None:
			AOTexture = self.data['ImageAo'].convert('RGB').resize( (BaseTexture.width,BaseTexture.height) )
			BaseTexture = ImageChops.multiply( BaseTexture, AOTexture )

		# Register roughness, apply roughness to basetexture (ONLY IF ENVMAPS ARE ENABLED)

		if self.data['OutputEnvmap'] != None:
			RoughnessTexture = self.data['ImageRoughness'].convert('RGB').resize( (BaseTexture.width,BaseTexture.height) )
			BaseTexture = applyAlphaToTexture( BaseTexture, RoughnessTexture )


		''' ---------- PROCESS NORMAL MAP ---------- '''

		self.progressBar.setValue( 3 )

		NormalTexture = self.data['ImageNormal'].convert('RGB')
		if self.data['SizeOverride']: NormalTexture = NormalTexture.resize( (self.data['SizeOverride'], self.data['SizeOverride']) )

		if self.checkFlipY.isChecked():
			def flipG( tex ):
				r, g, b = tex.split()
				g = ImageChops.invert(g)
				return Image.merge( 'RGB', (r, g, b) )
			NormalTexture = flipG( NormalTexture )


		''' ---------- CONVERT IMAGES ---------- '''
		
		self.progressBar.setValue( 4 )

		def PILToVTF( img:Image, fmt ) -> VTF:
			v = VTF( img.width, img.height, frames=1, fmt=fmt )
			v.get( frame=0 ).copy_from( img.convert('RGBA').tobytes() )
			return v

		if self.data['OutputEnvmap'] == None:
			BaseTextureVTF = PILToVTF( BaseTexture, VTFFormats.DXT1 )
		else:
			BaseTextureVTF = PILToVTF( BaseTexture, VTFFormats.DXT5 )
		NormalTextureVTF = PILToVTF( NormalTexture, VTFFormats.UV88 )

		targetDir = str( self.removeSuffix(Path(path)) )


		''' ---------- SAVE IMAGES ---------- '''

		with open( targetDir+'_basecolor.vtf', 'wb' ) as targetfile:
			BaseTextureVTF.save( targetfile )
		with open( targetDir+'_bump.vtf', 'wb' ) as targetfile:
			NormalTextureVTF.save( targetfile )

		self.progressBar.setValue( 5 )

		msgBox = QMessageBox()
		msgBox.setWindowTitle( self.windowTitle() )
		msgBox.setText( 'Export successful!' )
		msgBox.exec()

		self.progressBar.reset()

		
		


app = QApplication()
win = frontend()
win.show()
app.exec()