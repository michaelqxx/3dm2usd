from rhino3dm import *
from pxr import Usd, Vt, UsdGeom, UsdShade, Sdf
import shutil
from os import path, mkdir
import png
import uuid
import subprocess

import sys

if len(sys.argv) != 3:
    quit()

texDir = '0'

def getTexture(material):
    tex = material.GetBitmapTexture()
    if tex:
        dst = path.join(texDir, path.basename(tex.FileName))
        shutil.copyfile(tex.FileName, dst)
        return dst
    else: # doing the vectary thing, creating a 2x2 image of the color value
        d = material.DiffuseColor

        img = [(d[0],d[1],d[2], d[0],d[1],d[2]),
             (d[0],d[1],d[2], d[0],d[1],d[2])]       

        dst = path.join(texDir, 'diffuse.png')
        f = open(dst, 'wb')
        w = png.Writer(2,2)
        w.write(f,img)
        f.close()
        return dst


# open 3dm
model = File3dm.Read(sys.argv[1])

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

    # Shine to roughness?
    roughness = 1.0 - (mat.Shine / 255.0) # MaxShine
    pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    # ?
    pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

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


count = 0

for obj in model.Objects:
    geo = obj.Geometry

    if isinstance(geo, Mesh):

        #geo.CombineIdenticalVertices(False,False)
        #geo.ConvertQuadsToTriangles()

        attr = obj.Attributes
        name = attr.Name
        if not name:
            name = 'object_' + str(count)

        matIndex = -1
        if attr.MaterialSource == ObjectMaterialSource.MaterialFromLayer:
            matIndex = model.Layers[attr.LayerIndex].RenderMaterialIndex
        else:
            matIndex = attr.MaterialIndex
            print('byobject')

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
        for i in range(geo.Vertices.__len__()):
            v = geo.Vertices[i]
            verts.append([v.X,v.Y,v.Z])
        
        # normals
        for i in range(geo.Normals.__len__()):
            n = geo.Normals[i]
            norms.append([n.X,n.Y,n.Z])
        
        # texture coordinates
        for i in range(geo.TextureCoordinates.__len__()):
            tc = geo.TextureCoordinates[i]
            texCoords.append([tc.X, tc.Y])

        # faces
        for i in range(geo.Faces.__len__()):
            f = geo.Faces[i]

            faceIndices.append(f[0])
            faceIndices.append(f[1])
            faceIndices.append(f[2])

            if f[2] == f[3]:
                faceCounts.append(3) # triangle
            else:
                faceCounts.append(4) # quad
                faceIndices.append(f[3])

        # attributes
        mesh.CreatePointsAttr(verts)
        mesh.CreateNormalsAttr(norms)
        mesh.SetNormalsInterpolation('faceVarying')
        tcs = mesh.CreatePrimvar("Texture_uv", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        tcs.Set(texCoords)
        mesh.CreateFaceVertexIndicesAttr(faceIndices)
        mesh.CreateFaceVertexCountsAttr(faceCounts)
        mesh.CreateExtentAttr(extent)
        ssa = mesh.CreateSubdivisionSchemeAttr()
        ssa.Set('none')

        UsdShade.MaterialBindingAPI(mesh).Bind(u_mats[matIndex])

    count += 1


stage.GetRootLayer().Save()

#subprocess.call(["usdcat", sys.argv[2], "-o", "out.usdc"])