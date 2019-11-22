import os

from rhino3dm import *
from pxr import Usd, Vt, UsdGeom, UsdShade, Sdf, Gf

from theTransformizer import getTransformMatrix, transform_point
from theMesher import usd_mesh_to_rhino

import sys


if len(sys.argv) != 3:
    quit()

# Dictionary to store materials as they are found
materialName2Index = {"Default":0}

# Setup models
modelPath = os.path.abspath(sys.argv[1])
if not os.access(modelPath, os.F_OK):
    print(modelPath + " does not exist")
    quit()

# 3dm
r_model = File3dm()
r_model.Settings.ModelUnitSystem = UnitSystem.Meters
# Usd
stage = Usd.Stage.Open(sys.argv[1])

# Recursive function to iterate through children and apply parent transforms
def process_child(prim, parentTransform):

    transform = getTransformMatrix(prim) * parentTransform
    
    if prim.GetTypeName() == 'Mesh':

        r_mesh = usd_mesh_to_rhino(prim, transform)
        attr = ObjectAttributes()

        #print(prim.GetName())
        attr.Name = prim.GetName()

        matBinding = prim.GetRelationship('material:binding')
        matPath = matBinding.GetTargets()[0]
        matName = str(matPath).replace('/','_')
        
        # Set material to layer, object to layer based on material
        if matName not in materialName2Index:
            
            u_mat = stage.GetPrimAtPath(matPath)
            r_mat = Material()
            r_mat.Name = matName

            # TODO: deal with all material props
            color_map = stage.GetPrimAtPath(matPath.AppendPath('diffuseColor_texture'))
            if not color_map:
                color_map = stage.GetPrimAtPath(matPath.AppendPath('diffuseColor_opacity_texture'))

            if color_map:
                inputsFile = color_map.GetAttribute('inputs:file').Get().resolvedPath
                r_mat.SetBitmapTexture(inputsFile)
            else:
                surfaceShader = stage.GetPrimAtPath(matPath.AppendPath('surfaceShader'))
                if surfaceShader:
                    diffuseColor = surfaceShader.GetAttribute('inputs:diffuseColor').Get()
                    r_mat.DiffuseColor = ( int( 255 * diffuseColor[0] ), int( 255 * diffuseColor[1] ), int( 255 * diffuseColor[2] ), 0)

            r_model.Materials.Add(r_mat)

            layer = Layer()
            layer.Name = matName
            layer.RenderMaterialIndex = r_model.Materials.__len__() - 1
            r_model.Layers.Add(layer)
            attr.LayerIndex = r_model.Layers.__len__() - 1
            materialName2Index[matName] = r_model.Materials.__len__() - 1
        else:
            attr.LayerIndex = materialName2Index[matName]

        r_model.Objects.AddMesh(r_mesh, attr)
    
    for child in prim.GetChildren():
        process_child(child, transform)
#

# the 'root'
pseudoRoot = stage.GetPseudoRoot()
rootPrims = pseudoRoot.GetChildren()

initialTransform = Gf.Transform() # an Identity

# Check for Y up
upAxis = UsdGeom.GetStageUpAxis(stage)
if upAxis == 'Y':
    ninetyAroundX = Gf.Rotation((1,0,0), 90)
    initialTransform.SetRotation( ninetyAroundX )

# Begin iteration
for prim in rootPrims:
    process_child(prim, initialTransform)

# done
r_model.Write(sys.argv[2], 5)

