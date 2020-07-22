#Noesis Python model import+export test module, imports/exports some data from/to a made-up format

from inc_noesis import *

import noesis
#rapi methods should only be used during handler callbacks
import rapi
import math
import sys
from bs4 import BeautifulSoup
import array

#registerNoesisTypes is called by Noesis to allow the script to register formats.
#Do not implement this function in script files unless you want them to be dedicated format modules!
def registerNoesisTypes():
	handle = noesis.register("Star Wars: The Old Republic", ".gr2")
	noesis.setHandlerTypeCheck(handle, noepyCheckType)
	noesis.setHandlerLoadModel(handle, noepyLoadModel) #see also noepyLoadModelRPG
	#noesis.setHandlerWriteModel(handle, noepyWriteModel)
	#noesis.setHandlerWriteAnim(handle, noepyWriteAnim)
	#noesis.logPopup()
	print("The log can be useful for catching debug prints from preview loads.\nBut don't leave it on when you release your script, or it will probably annoy people.")
	return 1

NOEPY_HEADER="GAWB"

#check if it's this type based on the data
def noepyCheckType(data):
	bs = NoeBitStream(data)
	if len(data) < 4:
		return 0
	if bs.readBytes(4).decode("ASCII").rstrip("\0") != NOEPY_HEADER:
		return 0
	return 1	   


#load the model
def noepyLoadModel(data, mdlList):
	ctx = rapi.rpgCreateContext()
	
	filelist=[]
	filecount=0
	matFilelist=[]
	matFilecount=0
	dirPath = rapi.getDirForFilePath(rapi.getInputName())
	resourcePath = ""
	pluginPath = noesis.getPluginsPath()
	configName = "python\\swtor-config.xml"
	if (rapi.checkFileExists(pluginPath + configName)):
		print("found the config file!")
		f = open(pluginPath + configName, 'r')
		config = BeautifulSoup(f)
		f.close()
		resourcePath = config.configuration.resourcepath.string
	workingfile=rapi.getInputName().split('\\')[-1]
	toLoadList = dirPath + workingfile + '.txt'
	if (rapi.checkFileExists(toLoadList)):
		f = open(toLoadList, 'r') #list of gr2 files to load
		for line in f:
			filelist.append(line.strip())
			print(line.strip())
			filecount += 1;
		print(filecount)
		if filecount > 0:
			for model in filelist:
				print(model)
			print('File Count: ' + str(filecount))
		else:
			print("Empty model_list.txt")
		f.close()

	matList=[] #Noesis built-in must have material list
	texList=[] #Noesis built-in must have texture list
	bones=[]
	anims=[]

	while (filecount >= 0 ): #change this when adding support for list of submodels to be loaded
		rapi.setPreviewOption("noTextureLoad","1")
		rapi.setPreviewOption("setAngOfs","0 0 90") #sets the default preview angle
		print("filecount=" +str(filecount))
		currentPath = dirPath
		if (rapi.checkFileExists(dirPath + workingfile) == False):
			if (rapi.checkFileExists(resourcePath + workingfile)):
				currentPath = resourcePath
			else:
				filecount -= 1
				if (filecount >= 0):
					workingfile=filelist[filecount]
				else:
					break
				continue

		meshHeader=[] #mesh header data
		meshName=[] #mesh names
		matName=[] #materialname used by meshes
		attachments=[]
		offsetMeshPiecesMesh=[]
		offsetMeshPiecesTexture=[]
		print(workingfile)
		fileHandle = open(currentPath + workingfile,"rb")
		fileReader = fileHandle.read()
		bs = NoeBitStream(fileReader)
		bs.seek(0x10,NOESEEK_ABS) #seek 0x10h/24
		num50Offsets=bs.read("i")
		gr2Type=bs.read("i")
		numMeshes=bs.read("h") #number of meshes
		numTextures=bs.read("h") #number of textures
		numBones=bs.read("h")
		numAttachs=bs.read("h")
		print( str(numAttachs))
		bs.seek(0x50,NOESEEK_ABS) #seek 0x50h/80
		offset50offset=bs.read("i")
		offsetMeshHeader=bs.read("i")
		offsetMaterialNameOffsets=bs.read("i")
		offsetBoneStructure=bs.read("i")
		offsetAttachments=bs.read("i")
		print (str(offsetAttachments))
		print("numMeshes: " + str(numMeshes[0]) + ", numTextures: " + str(numTextures[0]) + ", offset50offset: " + str(offset50offset[0]) + ", offsetMeshHeader: " + str(offsetMeshHeader[0]) + ", offsetMaterialNameOffsets=" + str(offsetMaterialNameOffsets[0]))
		
		if(offsetMeshHeader[0] != 0x70): #0x70
			print("Non-standard Mesh header: " + str(offsetMeshHeader))
		else:
			bs.seek(0x70,NOESEEK_ABS) #seek to Mesh Header
		
			#for loop to get meshHeader data
			for i in range(0,numMeshes[0]): 
				offsetMeshName=bs.read("i") 
				unkFloat=bs.read("f") #nem kell offsetMeshName olvassa
				numPieces=bs.read("h")
				numUsedBones=bs.read("h")
				unKnown=bs.read("h") #nem kell numBones olvassa
				print("Unknown: " + str(unKnown))
				numVertexBytes=bs.read("h")
				numVertices=bs.read("i")
				numFaces=bs.read("i")
				offsetMeshVertices=bs.read("i")
				offsetMeshPieces=bs.read("i")
				offsetFaces=bs.read("i") 
				offsetBones=bs.read("i") #nem kell offsetFaces olvassa
				print("offsetMeshName: " + str(offsetMeshName[0]) + ", numPieces: " + str(numPieces[0])+ ", numVertexBytes: " + str(numVertexBytes[0])+ ", numVertices: " + str(numVertices[0]) + ", numFaces: " + str(numFaces[0]))
				print("offsetMeshVertices: " + str(offsetMeshVertices[0]) + ", offsetMeshPieces: " + str(offsetMeshPieces[0]) + ", offsetFaces: " + str(offsetFaces[0]))
				meshHeader.append([offsetMeshName[0],numPieces[0],numVertexBytes[0],numVertices[0],numFaces[0],offsetMeshVertices[0],offsetMeshPieces[0],offsetFaces[0],offsetBones[0]])
										#0				#1				#2				#3				#4			#5						#6				#7				#8
			#-------------------------------------------------------------
		
			#for loop to get meshName data
			for i in range(0,numMeshes[0]):
				bs.seek((meshHeader[i][0]),NOESEEK_ABS)
				nameLength=0
				boolP=True
				while (boolP==True):
					wak=bs.read("b")
					if (wak[0]!=0):
						nameLength=nameLength+1
					else:
						boolP=False
				bs.seek((meshHeader[i][0]),NOESEEK_ABS)
				meshName.append(bs.readBytes(nameLength).decode("ASCII"))
			#-------------------------------------------------------------
		
			#for loop to get meshPieces data
			for i in range(0,numMeshes[0]): # meshszamszor vegrehajt pl 3 mesh
				bs.seek((meshHeader[i][6]),NOESEEK_ABS)
				for j in range(0,(meshHeader[i][1])): #hasznalt textura szamszor vegrehajt pl 4 texture
					materialFacesIndex=bs.read("i")
					materialNumFaces=bs.read("i") #szorozni harommal a vertex szamhoz
					textureID=bs.read("i")
					if (textureID[0]== -1):
						textureID = (0,)
					numIdx=materialNumFaces*3
					bs.seek(0x24,NOESEEK_REL)
					offsetMeshPiecesMesh.append([materialFacesIndex[0],materialNumFaces[0],textureID[0],numIdx[0]])
															#0				#1					#2			#3
					print("materialFacesIndex: " + str(materialFacesIndex[0])+ ", materialNumFaces: " + str(materialNumFaces[0])+ ", textureId: " + str(textureID[0])+ ", numIdx: " + str(numIdx[0]))
				offsetMeshPiecesTexture.append(offsetMeshPiecesMesh)
				offsetMeshPiecesMesh=[]
			#-------------------------------------------------------------
					
			#for loop to get Attached Objects data
			attachmentsOffsetList=[]
			bs.seek(offsetAttachments[0],NOESEEK_ABS) #seek to offsetAttachments
			for i in range(0,numAttachs[0]): #fill attachmentsOffsetList
				offsetAttachmentName=bs.read("i")
				offsetBoneName=bs.read("i")
				matrix=NoeMat44.fromBytes(bs.readBytes(64))
				attachmentsOffsetList.append([offsetAttachmentName[0],offsetBoneName[0],matrix])
				#print (matrix)

			for i in range(0,numAttachs[0]):
				bs.seek((attachmentsOffsetList[i][0]),NOESEEK_ABS)
				nameLength=0
				boolP=True
				while (boolP==True):
					wak=bs.read("b")
					if (wak[0]!=0):
						nameLength=nameLength+1
					else:
						boolP=False
				bs.seek(attachmentsOffsetList[i][0],NOESEEK_ABS)
				attachmentName=bs.readBytes(nameLength).decode("ASCII").rstrip("\0").rstrip("\\")

				bs.seek((attachmentsOffsetList[i][1]),NOESEEK_ABS)
				nameLength=0
				boolP=True
				while (boolP==True):
					wak=bs.read("b")
					if (wak[0]!=0):
						nameLength=nameLength+1
					else:
						boolP=False
				bs.seek(attachmentsOffsetList[i][1],NOESEEK_ABS)
				boneName=bs.readBytes(nameLength).decode("ASCII").rstrip("\0").rstrip("\\")

				attachments.append([attachmentName,boneName,attachmentsOffsetList[i][2]])

			for i in range(0,numAttachs[0]):
				print ("attachments: " + str(attachments[i]))
		
			#-------------------------------------------------------------
		
			#for loop to get materialName data
			matNameOffsetList=[]
			bs.seek(offsetMaterialNameOffsets[0],NOESEEK_ABS) #seek to 0x50 offsetMaterialNameOffset
			for i in range(0,numTextures[0]): #fill matNameOffsetList
				matNameOffsetList.append(bs.read("i"))

			if (offsetMaterialNameOffsets[0] == 0):
				print (str(meshHeader[0][0]))
				matNameOffsetList.append((meshHeader[0][0],))
				numTextures = (1,)
						
			for i in range(0,numTextures[0]):
				bs.seek((matNameOffsetList[i][0]),NOESEEK_ABS)
				nameLength=0
				boolP=True
				while (boolP==True):
					wak=bs.read("b")
					if (wak[0]!=0):
						nameLength=nameLength+1
					else:
						boolP=False
				bs.seek(matNameOffsetList[i][0],NOESEEK_ABS)
				matName.append(bs.readBytes(nameLength).decode("ASCII").rstrip("\0").rstrip("\\"))

			#-------------------------------------------------------------
		
			#material loading
			for i in range(0,numTextures[0]):
				print ("Material Name:" + matName[i])
				material=NoeMaterial(matName[i],"")

				materialFileName = matName[i]
				shaderLocation = resourcePath + "\\resources\\art\\shaders\\materials\\"
				if ("irror" in str(matName[i])):
					materialFileName = "eye_" + workingfile.split(".")[0].split("_")[1] + "_non_a01_c01"
				elif ("efault" in matName[i]): #uh oh this is a file with no regular materials defined. Checking for common material names based on model name.
					materialFileName = workingfile.split(".")[0]
					if (rapi.checkFileExists(shaderLocation + materialFileName + "_v01" + ".mat")):
						materialFileName = materialFileName + "_v01"
					elif (rapi.checkFileExists(shaderLocation + materialFileName + "_v02" + ".mat")):
						materialFileName = materialFileName + "_v02"
					elif (rapi.checkFileExists(shaderLocation + materialFileName + "_v03" + ".mat")):
						materialFileName = materialFileName + "_v03"
				
				materialFile = shaderLocation + materialFileName + ".mat"
				print(materialFile)
				
				inputs = {'DiffuseMap': 'default', 'GlossMap': 'default', 'UvScaling': '1,1', 'UsesReflection': 'False', 'ReflectionSpecInfluence': '0', 'ReflectionIntensity': '0', 'UsesEmissive': 'False', 'ReflectionContrast': '0', 'ReflectionBlurIntensity': '0', 'RotationMap1': 'default'} #setting up defaults
				inputsTypes = {'DiffuseMap': 'texture', 'GlossMap': 'texture', 'UvScaling': 'uvscale', 'UsesReflection': 'bool', 'ReflectionSpecInfluence': 'float', 'ReflectionIntensity': 'float', 'UsesEmissive': 'False', 'ReflectionContrast': 'float', 'ReflectionBlurIntensity': 'float', 'RotationMap1': 'texture'}
				alphaTestValue = 0
				alphaTestMode = "None"
				isTwoSided = False
				derived = "noMaterial"
				if (rapi.checkFileExists(materialFile)):
					f = open(materialFile, 'r') #material file
					xml = BeautifulSoup(f)
					#print(str(xml.material.input.semantic))
					f.close()
					rawMat = xml.material.find_all(lambda tag: len(tag.name) > 1, recursive=False)
					for mFlag in rawMat:
						if (mFlag.name != "input"):
							print(str(mFlag.name) + ": " + (mFlag.string or ""))
					rawInputs = xml.find_all("input")
					#print(str(rawInputs))
					for input in rawInputs:
						inputs[input.semantic.string] = input.value.string
						inputsTypes[input.semantic.string] = input.type.string
						print(input.semantic.string + " (" + input.type.string + "): " + input.value.string)

					alphaTestValue = float(xml.alphatestvalue.string)
					#print("AlphaTestValue: " + str(alphaTestValue))
					alphaTestMode = xml.alphamode.string
					#print("AlphaTestMode: " + alphaTestMode)
					isTwoSided = bool(xml.istwosided.string)
					#print("IsTwoSided: " + str(isTwoSided))
					derived = str(xml.derived.string)
					#print("Derived: " + derived)
				
				flags = 0
				if (isTwoSided):
					flags += noesis.NMATFLAG_TWOSIDED 

				#diffuseFile = resourcePath + "\\resources\\" + "art\\defaultassets\\gray.dds" #for testing normal/spec maps with a flat gray texture
				diffuseFile = resourcePath + "\\resources\\" + inputs["DiffuseMap"] + ".dds"
				rotationFile = resourcePath + "\\resources\\" + inputs["RotationMap1"] + ".dds"
				glossFile = resourcePath + "\\resources\\" + inputs["GlossMap"] + ".dds"

				UsesEmissive = False
				if ("True" in inputs["UsesEmissive"]):
					UsesEmissive = True
				print("UsesEmissive: " + str(UsesEmissive))
				usesReflection = False
				if ("True" in inputs["UsesReflection"]):
					usesReflection = True
				#print("UsesReflection: " + str(usesReflection))
				reflectionIntensity = float(inputs["ReflectionIntensity"])
				#print("ReflectionIntensity: " + str(reflectionIntensity))
				reflectionBlurIntensity = float(inputs["ReflectionBlurIntensity"])
				#print("ReflectionBlurIntensity: " + str(reflectionBlurIntensity))
				reflectionSpecInfluence = float(inputs["ReflectionSpecInfluence"])
				#print("ReflectionSpecInfluence: " + str(reflectionSpecInfluence))
				reflectionContrast = float(inputs["ReflectionContrast"])
				#print("ReflectionContrast: " + str(reflectionContrast))

				#print("d " + diffuseFile)
				#print("n " + rotationFile)
				#print("s " + glossFile)

				#print ("texPath: " + texPath)
				if (matName[i] == "util_collision_hidden"): #Disable the material for the collision geometry meshes
					material.setSkipRender(1)

				if(alphaTestMode != "None"):
					material.setAlphaTest(alphaTestValue)

				if (derived =="AnimatedUV"):
					animatedTexture1File = resourcePath + "\\resources\\" + inputs["AnimatedTexture1"] + ".dds"
					animatedTexture2File = resourcePath + "\\resources\\" + inputs["AnimatedTexture2"] + ".dds"
					FresnelGradientFile = resourcePath + "\\resources\\" + inputs["FresnelGradient"] + ".dds"

					animTexTint0 = (0,0,0,1.0)
					if(inputsTypes["animTexTint0"] == "float"):
						tintValue = float(inputs["animTexTint0"])
						animTexTint0 = (tintValue,tintValue,tintValue,tintValue)
					elif (inputsTypes["animTexTint0"] == "vector4"):
						tL = inputs["animTexTint0"].split(',')
						animTexTint0 = [float(tL[0]),float(tL[1]),float(tL[2]),float(tL[3])]
					#print("animTexTint0: " + str(animTexTint0))

					animFresnelHue0 = (0,0,0,1.0)
					if(inputsTypes["animFresnelHue0"] == "float"):
						animTexTint0 = float(inputs["animFresnelHue0"]) + .5
						#tintValue = float(inputs["animFresnelHue0"]) + .5
						#animFresnelHue0 = (tintValue,tintValue,tintValue,tintValue)
					if (inputs["animFresnelHue0"] == "0,0,0,1"):
						animFresnelHue0 = animTexTint0
					elif (inputsTypes["animFresnelHue0"] == "vector4"):
						tL = inputs["animFresnelHue0"].split(',')
						animFresnelHue0 = [float(tL[0]),float(tL[1]),float(tL[2]),float(tL[3])]
					#print("animFresnelHue0: " + str(animFresnelHue0))
					if(inputsTypes["animTexTint0"] == "float"):
						animTexTint0Vec = [animFresnelHue0[0] * animTexTint0, animFresnelHue0[1] * animTexTint0, animFresnelHue0[2] * animTexTint0, 1]
						material.setDiffuseColor(animTexTint0Vec)
						material.setAmbientColor(animFresnelHue0)
					else:
						material.setAmbientColor(animTexTint0)
						material.setDiffuseColor(animFresnelHue0)
					material.setFlags(flags)

					animTexTint1 = (0,0,0,1.0)
					if(inputsTypes["animTexTint1"] == "float"):
						animTexTint1 = float(inputs["animTexTint1"])
						#tintValue = float(inputs["animTexTint1"])
						#animTexTint1 = (tintValue,tintValue,tintValue,1)
					elif (inputsTypes["animTexTint1"] == "vector4"):
						tL = inputs["animTexTint1"].split(',')
						animTexTint1 = [float(tL[0]),float(tL[1]),float(tL[2]),float(tL[3])]
					#print("animTexTint1: " + str(animTexTint1))

					animFresnelHue1 = (0.0,0.0,0.0,1.0)
					if(inputsTypes["animFresnelHue1"] == "float"):
						tintValue = float(inputs["animFresnelHue1"])
						animFresnelHue1 = (tintValue,tintValue,tintValue,tintValue)
					elif (inputsTypes["animFresnelHue1"] == "vector4"):
						tL = inputs["animFresnelHue1"].split(',')
						animFresnelHue1 = [float(tL[0]),float(tL[1]),float(tL[2]),float(tL[3])]
					#print("animFresnelHue1: " + str(animFresnelHue1))

					animTexTint2 = (0.0,0.0,0.0,1.0)
					if(inputsTypes["animTexTint2"] == "float"):
						tintValue = float(inputs["animTexTint2"])
						animTexTint2 = (tintValue,tintValue,tintValue,tintValue)
					elif (inputsTypes["animTexTint2"] == "vector4"):
						tL = inputs["animTexTint2"].split(',')
						animTexTint2 = [float(tL[0]),float(tL[1]),float(tL[2]),float(tL[3])]
					#print("animTexTint2: " + str(animTexTint2))

					if (alphaTestMode == "Add"):
						material.setBlendMode("GL_ONE", "GL_ONE")
					else:
						material.setBlendMode("GL_SRC_COLOR", "GL_ONE_MINUS_SRC_ALPHA")

					animTexUVScrollSpeed0 = inputs["animTexUVScrollSpeed0"]
					#print("animTexUVScrollSpeed0: " + str(animTexUVScrollSpeed0))
					animTexRotationPivot0 = inputs["animTexRotationPivot0"]
					#print("animTexRotationPivot0: " + str(animTexRotationPivot0))
					animTexRotationSpeed0 = float(inputs["animTexRotationSpeed0"])
					#print("animTexRotationSpeed0: " + str(animTexRotationSpeed0))
					
					if (rapi.checkFileExists(animatedTexture1File)):
						animTexUVScrollSpeed1 = inputs["animTexUVScrollSpeed1"]
						#print("animTexUVScrollSpeed1: " + str(animTexUVScrollSpeed1))
						animTexRotationPivot1 = inputs["animTexRotationPivot1"]
						#print("animTexRotationPivot1: " + str(animTexRotationPivot1))
						animTexRotationSpeed1 = float(inputs["animTexRotationSpeed1"])
						#print("animTexRotationSpeed1: " + str(animTexRotationSpeed1))

						animatedMaterial = NoeMaterial(inputs["AnimatedTexture1"],"")
						
						animatedTextureMap = noesis.loadImageRGBA(animatedTexture1File)
						animatedTextureData = animatedTextureMap.pixelData
						aniHeight = animatedTextureMap.height
						aniWidth = animatedTextureMap.width

						animatedTexture = NoeTexture(inputs["AnimatedTexture1"], aniWidth, aniHeight, animatedTextureData)
						texList.append(animatedTexture)
						animatedMaterial.setTexture(inputs["AnimatedTexture1"])

						if(False): #inputs['FresnelGradient'] != ""): #need to figure out how to blend fresnel gradients
							FresnelGradient = noesis.loadImageRGBA(FresnelGradientFile)
							fgWidth = FresnelGradient.width
							fgHeight = FresnelGradient.height
							cubeMap = NoeTexture(inputs["FresnelGradient"], fgWidth, fgHeight, FresnelGradient.pixelData * 6)
							cubeMap.setFlags(noesis.NTEXFLAG_CUBEMAP)
							texList.append(cubeMap)
							animatedMaterial.setEnvTexture(inputs["FresnelGradient"])
							animatedMaterial.setEnvColor(animFresnelHue1)

						xPivot = float(animTexRotationPivot1.split(',')[0])
						yPivot = float(animTexRotationPivot1.split(',')[1])

						xScroll = float(animTexUVScrollSpeed1.split(',')[0])
						yScroll = float(animTexUVScrollSpeed1.split(',')[1])
						animatedMaterial.setExpr_uvtrans_x(str(xScroll) + " * time*.001");
						animatedMaterial.setExpr_uvtrans_y(str(yScroll) + " * time*.001");
					
						animatedMaterial.setExpr_uvrot_x(str(animTexRotationSpeed1 + xPivot * xScroll) + " * time*.001")
						animatedMaterial.setExpr_uvrot_y(str(animTexRotationSpeed1 + yPivot * yScroll) + " * time*.001")

						#animatedMaterial.setExpr_vclr_r("mtl_diffuse_r")
						#animatedMaterial.setExpr_vclr_g("mtl_diffuse_g")
						#animatedMaterial.setExpr_vclr_b("mtl_diffuse_b")
						#animatedMaterial.setExpr_vclr_a("mtl_diffuse_a * 1 - max(min(max((vert_idx - 0), 0), 1),0)")
	
						if(alphaTestMode != "None"):
							animatedMaterial.setAlphaTest(alphaTestValue)

						if (alphaTestMode == "Add"):
							animatedMaterial.setBlendMode("GL_SRC_COLOR", "GL_ONE")
						elif (alphaTestMode == "None"):
							animatedMaterial.setBlendMode("GL_SRC_COLOR", "GL_SRC_COLOR")
						#matList.append(animatedMaterial)
						material.setNextPass(animatedMaterial)
						
						
						if(inputsTypes['animTexTint1'] == "float"):
							animTexTint1Vec = [animFresnelHue0[0] * animTexTint1, animFresnelHue0[1] * animTexTint1, animFresnelHue0[2] * animTexTint1, 1]
							animatedMaterial.setDiffuseColor(animTexTint1Vec)
							animatedMaterial.setAmbientColor(animFresnelHue1)
						else:
							animatedMaterial.setAmbientColor(animTexTint1)
							animatedMaterial.setDiffuseColor(animFresnelHue1)
						aFlags = noesis.NMATFLAG_USELMUVS + flags
						animatedMaterial.setFlags(aFlags)
						#animatedMaterial.setSkipRender(1)

					if (rapi.checkFileExists(animatedTexture2File)): #Disabled till I find a way to implment a 3rd set of UV coordinates
						animTexUVScrollSpeed2 = inputs["animTexUVScrollSpeed2"]
						#print("animTexUVScrollSpeed2: " + str(animTexUVScrollSpeed2))
						animTexRotationPivot2 = inputs["animTexRotationPivot2"]
						#print("animTexRotationPivot2: " + str(animTexRotationPivot2))
						animTexRotationSpeed2 = float(inputs["animTexRotationSpeed2"])
						#print("animTexRotationSpeed2: " + str(animTexRotationSpeed2))

						animatedMaterial2 = NoeMaterial(inputs["AnimatedTexture2"],"")

						animatedTextureMap = noesis.loadImageRGBA(animatedTexture2File)
						animatedTextureData = animatedTextureMap.pixelData
						aniHeight = animatedTextureMap.height
						aniWidth = animatedTextureMap.width

						animatedTexture = NoeTexture(inputs["AnimatedTexture2"], aniWidth, aniHeight, animatedTextureData)
						texList.append(animatedTexture)
						animatedMaterial2.setTexture(inputs["AnimatedTexture2"])

						xPivot = float(animTexRotationPivot2.split(',')[0])
						yPivot = float(animTexRotationPivot2.split(',')[1])

						xScroll = float(animTexUVScrollSpeed2.split(',')[0])
						yScroll = float(animTexUVScrollSpeed2.split(',')[1])
						animatedMaterial2.setExpr_uvtrans_x(str(xScroll) + " * time*.001");
						animatedMaterial2.setExpr_uvtrans_y(str(yScroll) + " * time*.001");
						
						animatedMaterial2.setExpr_uvrot_x(str(animTexRotationSpeed2) + " * time*.001")
						animatedMaterial2.setExpr_uvrot_y(str(animTexRotationSpeed2) + " * time*.001")

						if(alphaTestMode != "None"):
							animatedMaterial2.setAlphaTest(alphaTestValue)
						animatedMaterial2.setBlendMode("GL_SRC_ALPHA", "GL_ONE_MINUS_SRC_ALPHA")
						animatedMaterial.setNextPass(animatedMaterial2)

						animatedMaterial2.setAmbientColor(animTexTint2)
						aFlags = noesis.NMATFLAG_USELMUVS + flags #This texture actually uses a third set of UVs that we don't have access to in noesis, it's passed through as a user stream when exported as: "SUV_MASK_UVs"
						animatedMaterial2.setFlags(aFlags)
						animatedMaterial2.setSkipRender(1)

				if (rapi.checkFileExists(diffuseFile)):
					rgbaMap1 = noesis.loadImageRGBA(diffuseFile)
					rgbaMap1Data = rgbaMap1.pixelData
					height = rgbaMap1.height
					width = rgbaMap1.width
					
					if (derived =="AnimatedUV"):
						xPivot = float(animTexRotationPivot0.split(',')[0])
						yPivot = float(animTexRotationPivot0.split(',')[1])

						xScroll = float(animTexUVScrollSpeed0.split(',')[0])
						yScroll = float(animTexUVScrollSpeed0.split(',')[1])
						material.setExpr_uvtrans_x(str(xScroll) + " * time*.001");  #apply the rotation to the base material as well.
						material.setExpr_uvtrans_y(str(yScroll) + " * time*.001");
					
						#material.setExpr_vclr_r("mtl_diffuse_r")
						#material.setExpr_vclr_g("mtl_diffuse_g")
						#material.setExpr_vclr_b("mtl_diffuse_b")
						#material.setExpr_vclr_a("mtl_diffuse_a* max(vert_idx-31, 0)")
						#material.setExpr_vclr_a("mtl_diffuse_a* ( 1 + sin(min(max(4-mod(vert_idx,8), 0),1)* time*.001))") # + "+ vert_uv_v*" + str(yPivot) +

						material.setExpr_uvrot_x(str(animTexRotationSpeed0) + " + vert_uv_u * pi * time*.001")
						material.setExpr_uvrot_y(str(animTexRotationSpeed0) + " * sin(time*.001)")

					if (alphaTestMode == "Add" or derived =="AnimatedUV"):
						diffuseData = rgbaMap1Data
						if(inputs['FresnelGradient'] != ""): #need to figure out how to blend fresnel gradients
							FresnelGradient = noesis.loadImageRGBA(FresnelGradientFile)
							fgWidth = FresnelGradient.width
							fgHeight = FresnelGradient.height
							fresnelTexture = NoeTexture(matName[i] + "_fresnel", fgWidth, fgHeight, FresnelGradient.pixelData)
							texList.append(fresnelTexture)
							#material.setEnvTexture(matName[i] + "_fresnel")
							#material.setEnvColor(animFresnelHue0)
					else:
						diffuseData = rapi.imageDecodeRaw(rapi.imageEncodeRaw(rgbaMap1Data, width, height, "r8g8b8a0"), width, height, "r8g8b8a0") #have to remove the alpha channel

					diffuseMap1 = NoeTexture(inputs["DiffuseMap"], width, height, diffuseData)
					texList.append(diffuseMap1)
					material.setTexture(inputs["DiffuseMap"])

					#if ("irror" in matName[i]):
						#diffuseData = rapi.imageFlipRGBA32(diffuseData, width, height, 1, 0)
						#material.setSkipRender(1) #skipping "mirrored" materials for now as they don't load properly

					#experimental section to apply pallete files to a texture
					#if (rapi.checkFileExists(dirPath + matName[i] + ".mat")):
						#code to pull pallete dds name from .mat file
						#palleteRGBA = noesis.loadImageRGBA(dirPath + matName[i]+".dds") #get pallet dds here into a Noetexture
						#
						#rapi.imageDecodeRawPal(dataToApplyPalleteTo, palleteRGBA, pixWidth, pixHeight, 8, "r8g8b8a8")

					#material.setDiffuseColor([1,1,1,0])
					if (derived !="AnimatedUV" and derived !="Glass"):
						material.setAmbientColor([.5,.5,.5,0])

					if (alphaTestMode == "Add"):
						material.setBlendMode("GL_ONE", "GL_ONE")

					rotationFileExists = False
					if (rapi.checkFileExists(rotationFile)):
						rotationFileExists = True
						rotationMap1 = noesis.loadImageRGBA(rotationFile)
						rotationMap1Data = rotationMap1.pixelData
						rotHeight = rotationMap1.height
						rotWidth = rotationMap1.width

						opacityData = bytearray([])
						if (rotWidth == width and rotHeight == height):
							for k in range(0, rotWidth*rotHeight):
								opacityData.append(rgbaMap1Data[k*4 + 0])
								opacityData.append(rgbaMap1Data[k*4 + 1])
								opacityData.append(rgbaMap1Data[k*4 + 2])
								opacityData.append(255 - rotationMap1Data[k*4 + 0]) #have to flip the alpha channel
						else:
							opacityData = rapi.imageDecodeRaw(rapi.imageEncodeRaw(rotationMap1Data, rotWidth, rotHeight, "g0b0a0r8"), rotWidth, rotHeight, "r0g0b0a8")
							opacityData = rapi.imageResample(opacityData, rotWidth, rotHeight, width, height)
							for k in range(0, width*height):
								opacityData[k*4 + 0] = rgbaMap1Data[k*4 + 0]
								opacityData[k*4 + 1] = rgbaMap1Data[k*4 + 1]
								opacityData[k*4 + 2] = rgbaMap1Data[k*4 + 2]
								opacityData[k*4 + 2] = opacityData[k*4 + 2] #don't have to flip this alpha channel for some reason
						
						opacityMap1 = NoeTexture(inputs["DiffuseMap"] + "_opacity", width, height, opacityData)
						texList.append(opacityMap1)
						material.setTexture(inputs["DiffuseMap"] + "_opacity")

						if (alphaTestMode == "Test"):
							material.setBlendMode("None","None")
						elif (alphaTestMode == "MultipassFull"):
							material.setAlphaTest(0.0)
							material.setBlendMode("GL_SRC_COLOR", "GL_SRC_COLOR") #("GL_SRC_ALPHA", "GL_SRC_COLOR")
						elif(alphaTestMode == "Full"):
							material.setBlendMode("GL_SRC_COLOR", "GL_SRC_ALPHA") #"GL_ONE_MINUS_SRC_ALPHA")
			
						normalData = rapi.imageDecodeRaw(rapi.imageEncodeRaw(rotationMap1Data, rotWidth, rotHeight, "a8g8r0b0"), rotWidth, rotHeight, "r8g8b0a0")
						for k in range(0, rotWidth*rotHeight):
							#print( str(normalData[k*4 + 0]*normalData[k*4 + 0]/65536))
							x = float(normalData[k*4 + 0] / 127.5 - 1)
							y = float(normalData[k*4 + 1] / 127.5 - 1)
							h = int(math.sqrt(abs(1 - x*x - y*y)) * 255)
							#if ( k % 100 == 0):
								#print(str(x) + ", " + str(y) + ", " + str(h))
							normalData[k*4 + 2]  = h
						#heightmap = bytearray([])
						#for k in range(0, rotWidth*rotHeight):
							#h = int(normalData[k*4 + 3]*normalData[k*4 + 1]/256)
							#print(str(h))
							#heightmap.append(h)
							#heightmap.append(h)
							#heightmap.append(h)
							#heightmap.append(255)
						
						#normalData = rapi.imageNormalMapFromHeightMap(heightmap, rotWidth, rotHeight, 1, 2) #this turns our bump map into a normal map
						bumpMap1 = NoeTexture(inputs["RotationMap1"] + "_normal", rotWidth, rotHeight, normalData)
						#flags += noesis.NMATFLAG_NMAPSWAPRA
						texList.append(bumpMap1)
						if (derived !="AnimatedUV" and derived !="Glass"):
							material.setNormalTexture(inputs["RotationMap1"] + "_normal")

						if(UsesEmissive):
							emissiveMaterial=NoeMaterial(inputs["RotationMap1"] + "_emissive","")
							#emissiveMask = rapi.imageDecodeRaw(rapi.imageEncodeRaw(rotationMap1Data, rotWidth, rotHeight, "b8b8b8b8"), width, height, "r8g8b8a8")
							emissiveMask = rapi.imageResample(rgbaMap1Data, width, height, rotWidth, rotHeight)
							for k in range(0, rotWidth*rotHeight):
								emissiveMask[k*4 + 3] = rotationMap1Data[k*4 + 2]
							emissiveMaskMap1 = NoeTexture(inputs["RotationMap1"] + "_emissive", rotWidth, rotHeight, emissiveMask)
							emissiveMaterial.setAlphaTest(alphaTestValue)
							emissiveMaterial.setTexture(inputs["RotationMap1"] + "_emissive")
							texList.append(emissiveMaskMap1)
							emissiveMaterial.setBlendMode("GL_SRC_ALPHA","GL_ONE")
							material.setNextPass(emissiveMaterial)
					else:
						print ("Couldn't find the normal map: " + rotationFile)
					glossfileExists = False
					if (rapi.checkFileExists(glossFile)):
						glossfileExists = True
						glossMap1 = noesis.loadImageRGBA(glossFile)
						gloHeight = glossMap1.height
						gloWidth = glossMap1.width
						glossMapData = glossMap1.pixelData
						specularMap1 = NoeTexture(inputs["GlossMap"], gloWidth, gloHeight, glossMapData, noesis.NOESISTEX_RGBA32) #blurMap)
						texList.append(specularMap1)
						material.setSpecularTexture(inputs["GlossMap"])
						#material.setEnvColor([reflectionIntensity-.75, reflectionIntensity-.75, reflectionIntensity-.75, reflectionBlurIntensity])
						if(derived == "Creature"):
							#tones = inputs['FlushTone'].split(',')
							#material.setSpecularColor([float(tones[0]),float(tones[1]), float(tones[2]), 8])
							brightness = float(inputs['FleshBrightness']) + .5
							material.setAmbientColor([brightness, brightness, brightness, 1])
						material.setSpecularColor([.5, .5, .5, 8])
						#material.setSpecularColor([reflectionSpecInfluence, reflectionSpecInfluence, reflectionSpecInfluence, 8])
						flags += noesis.NMATFLAG_KAJIYAKAY #this flag is needed so that that the alpha channel of the specular map is used as the luminosity value\
					material.setFlags(flags)
					material.setDefaultBlend(0)
					
					if (usesReflection and 'RimWidth' in inputs and 'RimStrength' in inputs):
						rimWidth = float(inputs['RimWidth'])
						rimStrength  = float(inputs['RimStrength'])
						material.setRimLighting([[1.0,1.0,1.0], rimWidth, rimStrength, 0.0, [1.0,1.0,1.0]])
					if (False): #usesReflection and alphaTestMode != "Add"): #Disabled
						reflectionMaterial=NoeMaterial(inputs["DiffuseMap"] + "_reflection","")

						#reflectionData = rapi.imageDecodeRaw(rapi.imageEncodeRaw(rgbaMap1Data, width, height, "a8a8a8a8"), width, height, "r8g8b8a8")
						reflectionMap = NoeTexture(inputs["DiffuseMap"] + "_reflection", width, height, rgbaMap1Data, noesis.NOESISTEX_RGBA32) #blurMap)
						texList.append(reflectionMap)
						reflectionMaterial.setTexture(inputs["DiffuseMap"] + "_reflection")
						r = reflectionIntensity * .4
						s = reflectionSpecInfluence * .4
						reflectionMaterial.setEnvColor([r, r, r, reflectionBlurIntensity])
						reflectionMaterial.setSpecularColor([s, s, s, 8])
						#reflectionMaterial.setDiffuseColor([0.1,0.1,0.1,1])
						
						if (alphaTestMode == "MultipassFull"):
							reflectionMaterial.setBlendMode("GL_SRC_ALPHA", "GL_ONE") #man these blending options are ridiculous
						elif(alphaTestMode == "Full"):
							reflectionMaterial.setBlendMode("GL_SRC_ALPHA", "GL_DST_ALPHA")
						elif(alphaTestMode == "Test"):
							reflectionMaterial.setBlendMode("GL_SRC_COLOR", "GL_ONE")
						elif (alphaTestMode == "Add"):
							reflectionMaterial.setBlendMode("GL_ONE", "GL_ONE")
						elif(alphaTestMode == "None"):
							reflectionMaterial.setBlendMode("GL_SRC_ALPHA", "GL_ONE")
						if (glossfileExists):
							reflectionMaterial.setSpecularTexture(inputs["GlossMap"])
						if (rotationFileExists):
							reflectionMaterial.setNormalTexture(inputs["RotationMap1"] + "_normal")
						if (rapi.checkFileExists(resourcePath + "\\resources\\art\\environmentmaps\\coruscant_main\\area.dds")):
							enviromentMap = noesis.loadImageRGBA(resourcePath + "\\resources\\art\\environmentmaps\\coruscant_main\\area.dds")
							cubeMap = NoeTexture("envMap", enviromentMap.width, enviromentMap.height, enviromentMap.pixelData * 6)
							cubeMap.setFlags(noesis.NTEXFLAG_CUBEMAP)
							texList.append(cubeMap)
							reflectionMaterial.setEnvTexture("envMap")
						reflectionMaterial.setFlags(flags)
						if(UsesEmissive and rotationFileExists):
							material.setNextPass(reflectionMaterial)
							reflectionMaterial.setNextPass(emissiveMaterial)
						else:
							material.setNextPass(reflectionMaterial)
				#else:
					#material.setTexture("default_d.dds")

				print (texList)
				matList.append(material)
			#-------------------------------------------------------------
			#if (filecount == 0):
				#rapi.rpgSetPosScaleBias(NoeVec3((1,1,1)), NoeVec3((0,0,0))) #testing positioning of loaded models
			#else:
				#rapi.rpgSetPosScaleBias(NoeVec3((1,1,1)), NoeVec3((0,0,0)))
			#the draw
			for i in range(0,numMeshes[0]):
				if ("collision" in meshName[i]):
					continue
				bs.seek(meshHeader[i][5],NOESEEK_ABS) #set pointer to vertex offset
				if meshHeader[i][2]==12:
					VertBuff = bs.readBytes((meshHeader[i][3]) * 0xC)
					#rapi.rpgBindPositionBufferOfs(VertBuff, noesis.RPGEODATA_FLOAT, 12, 0) #this appears to be the collision model - disabled so it's invisible
					continue
				elif meshHeader[i][2]==24:
					VertBuff = bs.readBytes((meshHeader[i][3]) * 0x18)
					rapi.rpgBindPositionBufferOfs(VertBuff, noesis.RPGEODATA_FLOAT, 24, 0)
					rapi.rpgBindNormalBufferOfs(VertBuff,noesis.RPGEODATA_BYTE, 24, 12)
					rapi.rpgBindTangentBufferOfs(VertBuff,noesis.RPGEODATA_BYTE, 24, 16)
					rapi.rpgBindUV1BufferOfs(VertBuff,noesis.RPGEODATA_HALFFLOAT,24,20)
				elif meshHeader[i][2]==32:
					VertBuff = bs.readBytes((meshHeader[i][3]) * 0x20)
					rapi.rpgBindPositionBufferOfs(VertBuff, noesis.RPGEODATA_FLOAT, 32, 0)
					if ("multiUvExtraction" in meshName[i]):
						print("multiUV")
						rapi.rpgBindUV1BufferOfs(VertBuff,noesis.RPGEODATA_HALFFLOAT,32,20) #this value can either be 20 or 28. The vast majority of models use 28, but we need to find the flag that sets this.
						rapi.rpgBindUV2BufferOfs(VertBuff,noesis.RPGEODATA_HALFFLOAT,32,24)
						rapi.rpgBindUserDataBuffer("SUV_MASK_UVs", VertBuff, 4 ,32,28)
					else:
						rapi.rpgBindNormalBufferOfs(VertBuff,noesis.RPGEODATA_BYTE, 32, 12)
						rapi.rpgBindTangentBufferOfs(VertBuff,noesis.RPGEODATA_BYTE, 32, 16)
						rapi.rpgBindUV1BufferOfs(VertBuff,noesis.RPGEODATA_HALFFLOAT,32,28) #this value can either be 20 or 28. The vast majority of models use 28, but we need to find the flag that sets this.
				rapi.rpgCommitTriangles(None, noesis.RPGEODATA_USHORT, meshHeader[i][3], noesis.RPGEO_POINTS, 1)
				bs.seek(meshHeader[i][7],NOESEEK_ABS)
				for j in range(0,meshHeader[i][1]):
					FaceBuff=bs.readBytes((offsetMeshPiecesTexture[i][j][1]*3)*2)
					rapi.rpgSetMaterial(matName[offsetMeshPiecesTexture[i][j][2]])
					#rapi.rpgSetLightmap(matName[(offsetMeshPiecesTexture[i][j][2] - 1 )] + "_animated")
					rapi.rpgSetName(meshName[i])
					rapi.rpgCommitTriangles(FaceBuff, noesis.RPGEODATA_USHORT, offsetMeshPiecesTexture[i][j][1]*3, noesis.RPGEO_TRIANGLE, 1)
				rapi.rpgClearBufferBinds()
		fileHandle.close()
		filecount -= 1
		if (filecount >= 0):
			workingfile=filelist[filecount]
		
	mdl=rapi.rpgConstructModel()
	mdl.setModelMaterials(NoeModelMaterials(texList,matList))
	mdlList.append(mdl)
	rapi.rpgClearBufferBinds()
	rapi.setPreviewOption("autoLoadNonDiffuse", "1")
	return 1