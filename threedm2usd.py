from rhino3dm import File3dm, Mesh, ObjectMaterialSource, Brep, Extrusion, MeshType
from pxr import Usd, UsdGeom, UsdShade, Sdf
import shutil
import png
import subprocess
import os
import sys

from theMesher import MeshMeshItRealGood as convertMesh
from theMaterializer import Materializer

# path names, tmp dir
cwd = os.getcwd()

modelPath = os.path.abspath(sys.argv[1])

if not os.access(modelPath, os.F_OK):
    print(modelPath + " does not exist")
    quit()

baseName = os.path.basename(modelPath)
baseFilename = baseName.replace('.3dm','')
usda = baseFilename + '.usda'
usdc = baseFilename + '.usdc'
usdz = baseFilename + '.usdz'

tmpDir = '_tmp'
if os.path.exists(tmpDir):
    shutil.rmtree(tmpDir)

os.mkdir(tmpDir)
os.chdir(tmpDir)

# open 3dm
model = File3dm.Read(modelPath)

# create usd
stage = Usd.Stage.CreateNew(usda)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y) ######## XYZ -> XZ-Y
xformPrim = UsdGeom.Xform.Define(stage, '/root')

# Materials
materializer = Materializer(stage)
u_mats = []
for mat in model.Materials:

    u_mat = materializer.convertMaterial(mat)
    u_mats.append(u_mat)

# Meshes
count = 0
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
subprocess.call(["usdzip", usdz, usdc, materializer.texDir])

#for arg in sys.argv:
#    print(path.splitext(arg))

# exit
shutil.rmtree(materializer.texDir)
os.chdir(cwd) 
