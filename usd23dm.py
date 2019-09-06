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

rootlayer = Layer()
rootlayer.Name = "root"
r_model.Layers.Add(rootlayer)
currentLayerId = 0

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
        r_model.Objects.AddMesh(r_mesh)

r_model.Write(sys.argv[2], 5)
