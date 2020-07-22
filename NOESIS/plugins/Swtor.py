#Noesis Python model import+export test module, imports/exports some data from/to a made-up format

#bs.seek(0xEC,NOESEEK_REL) #seek to header info
#red=bs.read("hh")
#testU=noesis.getFloat16(red[0])
#testV=noesis.getFloat16(red[1])
#print(testU,testV)
from inc_noesis import *

import noesis

#rapi methods should only be used during handler callbacks
import rapi

#registerNoesisTypes is called by Noesis to allow the script to register formats.
#Do not implement this function in script files unless you want them to be dedicated format modules!
def registerNoesisTypes():
	handle = noesis.register("Star Wars: The Old Republic", ".gr2")
	noesis.setHandlerTypeCheck(handle, noepyCheckType)
	noesis.setHandlerLoadModel(handle, noepyLoadModel) #see also noepyLoadModelRPG
	#noesis.setHandlerWriteModel(handle, noepyWriteModel)
	#noesis.setHandlerWriteAnim(handle, noepyWriteAnim)
	#noesis.logPopup()
	#print("The log can be useful for catching debug prints from preview loads.\nBut don't leave it on when you release your script, or it will probably annoy people.")
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
	bs = NoeBitStream(data)
	bs.seek(0x18,NOESEEK_ABS) #seek 0x18h/24
	numMeshes=bs.read("h") #number of meshes
	numTextures=bs.read("h") #number of textures
	bs.seek(0x50,NOESEEK_ABS) #seek 0x50h/80
	offset50offset=bs.read("i")
	offsetMeshHeader=bs.read("i")
	offsetMaterialNameOffsets=bs.read("i")
	bs.seek(0x70,NOESEEK_ABS) #seek to Mesh Header
	meshHeader=[] #mesh header data
	meshName=[] #mesh names
	matName=[] #materialname used by meshes
	texName=[] #texture names will be used
	matList=[] #Noesis built-in must have material list
	texList=[] #Noesis built-in must have texture list
	offsetMaterialUsageMesh=[]
	offsetMaterialUsageTexture=[]
	
	#for loop to get meshHeader data
	for i in range(0,numMeshes[0]): 
		offsetMeshName=bs.read("i") 
		unkFloat=bs.read("f") #nem kell offsetMeshName olvassa
		numUsedTextures=bs.read("h")
		numBones=bs.read("h")
		unKnown=bs.read("h") #nem kell numBones olvassa
		numVertexBytes=bs.read("h")
		numVertices=bs.read("i")
		numFaces=bs.read("i")
		offsetVertices=bs.read("i")
		offsetMaterialUsage=bs.read("i")
		offsetFace=bs.read("i") 
		unkOffset=bs.read("i") #nem kell offsetFace olvassa
		meshHeader.append([offsetMeshName[0],numUsedTextures[0],numVertexBytes[0],numVertices[0],numFaces[0],offsetVertices[0],offsetMaterialUsage[0],offsetFace[0]])
							#0					#1					#2			#3				#4				#5					#6					#7
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
		meshName.append(bs.readBytes(nameLength).decode("ASCII").rstrip("\0"))
	#-------------------------------------------------------------
	
	#for loop to get matName data
	matNameOffsetList=[]
	bs.seek(offsetMaterialNameOffsets[0],NOESEEK_ABS) #seek to 0x50 offsetMaterialNameOffset
	for i in range(0,numTextures[0]): #fill matNameOffsetList
		matNameOffsetList.append(bs.read("i"))
	
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
		matName.append(bs.readBytes(nameLength).decode("ASCII").rstrip("\0"))
		texName=[s + "_d" for s in matName]
	#-------------------------------------------------------------
	
	#for loop to get materialUsage data
	for i in range(0,numMeshes[0]): # meshszamszor vegrehajt pl 3 mesh
		bs.seek((meshHeader[i][6]),NOESEEK_ABS)
		for j in range(0,(meshHeader[i][1])): #hasznalt textura szamszor vegrehajt pl 4 texture
			materialFacesIndex=bs.read("i")
			materialNumFaces=bs.read("i") #szorozni harommal a vertex szamhoz
			textureID=bs.read("i")
			numIdx=materialNumFaces*3
			bs.seek(0x24,NOESEEK_REL)
			offsetMaterialUsageMesh.append([materialFacesIndex[0],materialNumFaces[0],textureID[0],numIdx[0]])
													#0					#1					#2		    #3
		offsetMaterialUsageTexture.append(offsetMaterialUsageMesh)
		offsetMaterialUsageMesh=[]
	#-------------------------------------------------------------
	
	#material naming
	for i in range(0,numTextures[0]):
		material=NoeMaterial(matName[i],"")
		material.setTexture(matName[i]+"_d.dds")
		material.nrmTexName=(matName[i]+"_n.dds")
		material.specTexName=(matName[i]+"_s.dds")
		material.setDefaultBlend(0)
		matList.append(material)
	#-------------------------------------------------------------
	
	#the draw
	for i in range(0,numMeshes[0]):
		bs.seek(meshHeader[i][5],NOESEEK_ABS) #set pointer to vertex offset
		if meshHeader[i][2]==12:
			VertBuff = bs.seek(((meshHeader[i][3]) * 0xC),NOESEEK_REL)
			#rapi.rpgBindPositionBufferOfs(VertBuff, noesis.RPGEODATA_FLOAT, 12, 0)
		elif meshHeader[i][2]==24:
			VertBuff = bs.readBytes((meshHeader[i][3]) * 0x18)
			rapi.rpgBindPositionBufferOfs(VertBuff, noesis.RPGEODATA_FLOAT, 24, 0)
			rapi.rpgBindUV1BufferOfs(VertBuff,noesis.RPGEODATA_HALFFLOAT,24,20)
		elif meshHeader[i][2]==32:
			VertBuff = bs.readBytes((meshHeader[i][3]) * 0x20)
			rapi.rpgBindPositionBufferOfs(VertBuff, noesis.RPGEODATA_FLOAT, 32, 0)
			rapi.rpgBindUV1BufferOfs(VertBuff,noesis.RPGEODATA_HALFFLOAT,32,28)
		#rapi.rpgCommitTriangles(None, noesis.RPGEODATA_USHORT, meshHeader[i][3], noesis.RPGEO_POINTS, 1)
		bs.seek(meshHeader[i][7],NOESEEK_ABS)
		for j in range(0,meshHeader[i][1]):
			FaceBuff=bs.readBytes((offsetMaterialUsageTexture[i][j][1]*3)*2)
			rapi.rpgSetMaterial(matName[offsetMaterialUsageTexture[i][j][2]])
			rapi.rpgSetName(meshName[i])
			rapi.rpgCommitTriangles(FaceBuff, noesis.RPGEODATA_USHORT, offsetMaterialUsageTexture[i][j][1]*3, noesis.RPGEO_TRIANGLE, 1)
		rapi.rpgClearBufferBinds()
	mdl=rapi.rpgConstructModel()
	mdl.setModelMaterials(NoeModelMaterials(texList,matList))
	mdlList.append(mdl)
	rapi.rpgClearBufferBinds()
	return 1