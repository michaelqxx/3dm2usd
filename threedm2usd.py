from rhino3dm import *
from pxr import Usd, Vt, UsdGeom, UsdShade, Sdf
import shutil
from os import path, mkdir, chdir, getcwd
import png
import uuid
import subprocess
import os
import sys
from theMesher import MeshMeshItRealGood as convertMesh

if len(sys.argv) != 2:
    quit()

cwd = getcwd()

modelPath = path.abspath(sys.argv[1])
if not os.access(modelPath, os.F_OK):
    print(modelPath + " does not exist")
    quit()

modelDir = path.dirname(modelPath)
baseFilename = path.basename(modelPath).replace('.3dm','')
usda = path.join(modelDir, baseFilename + '.usda')
usdc = path.join(modelDir, baseFilename + '.usdc')
usdz = path.join(modelDir, baseFilename + '.usdz')
texDirName = '0'
absTexDir = path.join(modelDir, texDirName)

if path.exists(absTexDir):
    shutil.rmtree(absTexDir)

mkdir(absTexDir)

def getTexture(material):
    tex = material.GetBitmapTexture()
    if tex:
        texBase = path.basename(tex.FileName)
        dst = path.join(absTexDir, texBase)
        if os.access(tex.FileName, os.F_OK):
            shutil.copyfile(tex.FileName, dst)
        elif os.access(path.join(modelDir, texBase), os.F_OK):
            shutil.copyfile(path.join(modelDir, texBase), dst)

        return path.join(texDirName, texBase)
    else: # doing the vectary thing, creating a 2x2 image of the color value
        d = material.DiffuseColor

        img = [(d[0],d[1],d[2], d[0],d[1],d[2]),
             (d[0],d[1],d[2], d[0],d[1],d[2])]       

        dst = path.join(absTexDir, material.Name+'_diffuse.png')
        f = open(dst, 'wb')
        w = png.Writer(2,2)
        w.write(f,img)
        f.close()
        return path.join(texDirName, material.Name+'_diffuse.png')


# open 3dm
model = File3dm.Read(modelPath)

# create usd
stage = Usd.Stage.CreateNew(usda)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y) ######## XYZ -> XZ-Y
xformPrim = UsdGeom.Xform.Define(stage, '/root')

### Materials
matScope = UsdGeom.Scope.Define(stage, '/materials')
u_mats = []
count = 0
for mat in model.Materials:

    materialScope = '/materials/'
    if not mat.Name:
        nodeName = materialScope + 'material_' + str(count)
    else:
        nodeName = materialScope + mat.Name.replace(' ', '_').replace('-', '_') + str(count)

    u_mat = UsdShade.Material.Define(stage, nodeName)
    stinput = u_mat.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
    stinput.Set('Texture_uv')

    pbrShader = UsdShade.Shader.Define(stage, nodeName + '/pbr')
    pbrShader.CreateIdAttr("UsdPreviewSurface")

    # Shine to roughness?
    roughness = 1.0 - (mat.Shine / 255.0) # MaxShine
    pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    # ?
    pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(mat.Shine / 255.0) # ?

    u_mat.CreateSurfaceOutput().ConnectToSource(pbrShader, "surface")

    primvarReader = UsdShade.Shader.Define(stage, nodeName + '/Primvar')
    primvarReader.CreateIdAttr('UsdPrimvarReader_float2')
    primvarReader.CreateInput('varname', Sdf.ValueTypeNames.Token).ConnectToSource(stinput)

    diffuseTextureSampler = UsdShade.Shader.Define(stage, nodeName + '/color_map')
    diffuseTextureSampler.CreateIdAttr('UsdUVTexture')

    diffuse = getTexture(mat)
    diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(diffuse)

    diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primvarReader, 'result')
    pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Float3).ConnectToSource(diffuseTextureSampler, 'rbg')

    u_mats.append(u_mat)
    count += 1


count = 0

# Meshes
for obj in model.Objects:
 

    attr = obj.Attributes
    if not attr.Visible:
        continue
    
    geo = obj.Geometry

    name = attr.Name
    if not name:
        name = 'object_'

    name = 'o_' + name.replace(' ', '_').replace('-', '_') + str(count)

    matIndex = -1
    if attr.MaterialSource == ObjectMaterialSource.MaterialFromLayer:
        matIndex = model.Layers[attr.LayerIndex].RenderMaterialIndex
    else:
        matIndex = attr.MaterialIndex

    usdPath = '/root/' + name

    if isinstance(geo, Mesh):
        #geo.CombineIdenticalVertices(False, False)
        #geo.ConvertQuadsToTriangles()
        mesh = convertMesh(stage, geo, usdPath)
    elif isinstance(geo, Brep):
        r_mesh = Mesh()
        for i in range(geo.Faces.__len__()):
            face = geo.Faces[i]
            r_mesh.Append(face.GetMesh(MeshType.Render))
        mesh = convertMesh(stage, r_mesh, usdPath)
    elif isinstance(geo, Extrusion):
        r_mesh = geo.GetMesh(MeshType.Render)
        mesh = convertMesh(stage, r_mesh, usdPath)
    else:
        continue
    
    if mesh:
        UsdShade.MaterialBindingAPI(mesh).Bind(u_mats[matIndex])

    count += 1

# save usda
stage.GetRootLayer().Save()

# make usdc
subprocess.call(["usdcat", usda, "-o", usdc])
# make usdz

chdir(modelDir)
subprocess.call(["usdzip", usdz, usdc, texDirName])
chdir(cwd)
