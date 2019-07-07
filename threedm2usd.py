from rhino3dm import *
from pxr import Usd, Vt, UsdGeom, UsdShade, Sdf
import shutil
from os import path, mkdir

import sys

if len(sys.argv) != 3:
    quit()

# open 3dm
model = File3dm.Read(sys.argv[1])

bn = path.basename(sys.argv[1])
texDir = path.splitext(bn)[0]

if path.exists(texDir):
    shutil.rmtree(texDir)

mkdir(texDir)

# create usd
stage = Usd.Stage.CreateNew(sys.argv[2])
xformPrim = UsdGeom.Xform.Define(stage, '/root')

### Materials
matScope = UsdGeom.Scope.Define(stage, '/materials')
u_mats = []
for mat in model.Materials:

    nodeName = '/materials/' + mat.Name

    u_mat = UsdShade.Material.Define(stage, nodeName)
    stinput = u_mat.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
    stinput.Set('Texture_uv')

    pbrShader = UsdShade.Shader.Define(stage, nodeName + '/pbr')
    pbrShader.CreateIdAttr("UsdPreviewSurface")
    pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

    u_mat.CreateSurfaceOutput().ConnectToSource(pbrShader, "surface")

    primvarReader = UsdShade.Shader.Define(stage, nodeName + '/Primvar')
    primvarReader.CreateIdAttr('UsdPrimvarReader_float2')
    primvarReader.CreateInput('varname', Sdf.ValueTypeNames.Token).ConnectToSource(stinput)

    diffuseTextureSampler = UsdShade.Shader.Define(stage, nodeName + '/color_map')
    diffuseTextureSampler.CreateIdAttr('UsdUVTexture')

    tex = mat.GetBitmapTexture()
    if tex:
        print(tex.FileName)
        dst = path.join(texDir, path.basename(tex.FileName))
        print(dst)
        shutil.copyfile(tex.FileName, dst)
        diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(dst)
    else:
        diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set('white.jpg')

    diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primvarReader, 'result')
    pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Float3).ConnectToSource(diffuseTextureSampler, 'rbg')

    u_mats.append(u_mat)


count = 0

for obj in model.Objects:
    geo = obj.Geometry

    if isinstance(geo, Mesh):
        
        attr = obj.Attributes
        name = attr.Name
        if not name:
            name = 'object_' + str(count)

        # only by layer
        matIndex = model.Layers[attr.LayerIndex].RenderMaterialIndex

        mesh = UsdGeom.Mesh.Define(stage, '/root/' + name)
        verts = []
        norms = []
        faceCounts = []
        faceIndices = []
        extent = []
        texCoords = []

        # extents
        bb = geo.GetBoundingBox()
        extent.append([bb.Min.X, bb.Min.Y, bb.Min.Z])
        extent.append([bb.Max.X, bb.Max.Y, bb.Max.Z])
        
        # verts
        for v in geo.Vertices:
            verts.append([v.X,v.Y,v.Z])
        
        # normals
        for n in geo.Normals:
            norms.append([n.X,n.Y,n.Z]) 

        # faces
        for i in range(geo.Faces.__len__()):
            f = geo.Faces[i]

            faceIndices.append(f[0])
            faceIndices.append(f[1])
            faceIndices.append(f[2])

            if f[2] == f[3]:
                faceCounts.append(3)
            else:
                faceCounts.append(4)
                faceIndices.append(f[3])
        
        # texture coordinates
        for tc in geo.TextureCoordinates:
            texCoords.append([tc.X, tc.Y])

        tcs = mesh.CreatePrimvar("Texture_uv", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.uniform)
        tcs.Set(texCoords)

        # attributes
        mesh.CreateNormalsAttr(norms)
        mesh.CreatePointsAttr(verts)
        #mesh.SetNormalsInterpolation("faceVarying")
        mesh.CreateFaceVertexIndicesAttr(faceIndices)
        mesh.CreateFaceVertexCountsAttr(faceCounts)
        mesh.CreateExtentAttr(extent)

        UsdShade.MaterialBindingAPI(mesh).Bind(u_mats[matIndex])

    count += 1


stage.GetRootLayer().Save()
