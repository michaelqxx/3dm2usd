from rhino3dm import *
from pxr import Usd, Vt, UsdGeom, UsdShade, Sdf
import shutil
import os
import png
import uuid
import subprocess

import sys

if len(sys.argv) != 3:
    quit()


modelPath = os.path.abspath(sys.argv[1])
if not os.access(modelPath, os.F_OK):
    print(modelPath + " does not exist")
    quit()

r_model = File3dm()
r_model.Settings.ModelUnitSystem = UnitSystem.Centimeters

materialName2Index = {"Default":0}

stage = Usd.Stage.Open(sys.argv[1])

usdPaths = stage.Traverse()
for x in usdPaths:
    #print(x.GetTypeName())
    if x.GetTypeName() == 'Mesh':
        #print('Mesh')
        r_mesh = Mesh()
        pointsAttr = x.GetAttribute('points')
        points = pointsAttr.Get()
        r_mesh.Vertices.SetCount(points.__len__())

        count = 0
        for p in points:
            #print(p)
            r_mesh.Vertices.__setitem__(count, Point3f(p[0], p[1], p[2]))
            count += 1

        faceVertexCountsAttr = x.GetAttribute('faceVertexCounts')
        faceVertexCounts = faceVertexCountsAttr.Get()
        faceVertexIndicesAttr = x.GetAttribute('faceVertexIndices')
        faceVertexIndices = faceVertexIndicesAttr.Get()

        attr = ObjectAttributes()

        matBinding = x.GetRelationship('material:binding')
        matPath = matBinding.GetTargets()[0]
        matName = str(matPath)
        
        if matName not in materialName2Index:
            print(matName)

            u_mat = stage.GetPrimAtPath(matPath)
            color_map = stage.GetPrimAtPath(matPath.AppendPath('color_map'))
            inputsFile = color_map.GetAttribute('inputs:file').Get().resolvedPath

            r_mat = Material()
            r_mat.Name = matName
            r_mat.SetBitmapTexture(inputsFile)
            r_model.Materials.Add(r_mat)

            layer = Layer()
            layer.Name = matName
            layer.RenderMaterialIndex = r_model.Materials.__len__() - 1
            r_model.Layers.Add(layer)
            attr.LayerIndex = r_model.Layers.__len__() - 1
            materialName2Index[matName] = r_model.Materials.__len__() - 1
        else:
            attr.LayerIndex = materialName2Index[matName]

        count = 0
        for fvc in faceVertexCounts:
            f = []
            for i in range(count, (count + fvc)):
                f.append(faceVertexIndices[i])
                count = i + 1
            if f.__len__() == 4:
                r_mesh.Faces.AddFace(f[0], f[1], f[2], f[3])
            else:
                r_mesh.Faces.AddFace(f[0], f[1], f[2], f[2])

        rc = r_mesh.Normals.ComputeNormals()
        r_model.Objects.AddMesh(r_mesh, attr)


r_model.Write(sys.argv[2], 5)

