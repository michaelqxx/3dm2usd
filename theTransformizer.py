import numpy as np
from pxr import Gf
from rhino3dm import Point3f

def getTransformMatrix(x):

    # Identity Transformation
    transform = Gf.Transform()

    # Look for Attributes
    transformAttr = x.GetAttribute('xformOp:transform')
    scaleAttr = x.GetAttribute('xformOp:scale')
    orientAttr = x.GetAttribute('xformOp:orient')
    translateAttr = x.GetAttribute('xformOp:translate')

    if transformAttr:
        transform = transformAttr.Get()
        #print(transform[0])
    elif scaleAttr and orientAttr and translateAttr:

        translation = translateAttr.Get()
        orientation = orientAttr.Get() 
        scale = Gf.Vec3d(scaleAttr.Get())
        
        rotation = Gf.Rotation(orientation)
        transform = Gf.Transform(scale, Gf.Rotation(), rotation, Gf.Vec3d(), translation)
        #print(transform)
    
    return transform


def transform_point(transform, point):

    matrix = transform.GetMatrix()

    coord = np.array([point[0], point[1], point[2], 1])
    tr0 = np.array([matrix[0][0], matrix[1][0], matrix[2][0], matrix[3][0]])
    tr1 = np.array([matrix[0][1], matrix[1][1], matrix[2][1], matrix[3][1]])
    tr2 = np.array([matrix[0][2], matrix[1][2], matrix[2][2], matrix[3][2]])
    px = np.dot(tr0, coord)
    py = np.dot(tr1, coord)
    pz = np.dot(tr2, coord)

    return Point3f(px, py, pz)
