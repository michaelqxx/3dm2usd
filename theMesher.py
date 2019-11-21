from pxr import Vt, UsdGeom, Sdf
from rhino3dm import Mesh, Point2f
from theTransformizer import transform_point

def usd_mesh_to_rhino(u_mesh, transform):

    r_mesh = Mesh()
    pointsAttr = u_mesh.GetAttribute('points')
    points = pointsAttr.Get()
    r_mesh.Vertices.SetCount(points.__len__())

    count = 0
    for p in points:
        
        r_point = transform_point(transform, p)
        r_mesh.Vertices.__setitem__(count, r_point)

        count += 1

    faceVertexCountsAttr = u_mesh.GetAttribute('faceVertexCounts')
    faceVertexCounts = faceVertexCountsAttr.Get()
    faceVertexIndicesAttr = u_mesh.GetAttribute('faceVertexIndices')
    faceVertexIndices = faceVertexIndicesAttr.Get()
    texcoorAttr = u_mesh.GetAttribute('primvars:st')
    texcoords = texcoorAttr.Get()

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

    # tex coords 
    r_mesh.TextureCoordinates.SetCount(texcoords.__len__())
    count = 0
    for tc in texcoords:
        p2f = Point2f(tc[0], tc[1])
        r_mesh.TextureCoordinates[count] = p2f
        #r_mesh.TextureCoordinates.__setitem__(count, p2f)
        count += 1
    
    rc = r_mesh.Normals.ComputeNormals()

    return r_mesh


def rhino_mesh_to_usd(stage, r_mesh, name):
        mesh = UsdGeom.Mesh.Define(stage, name)
        verts = []
        norms = []
        faceCounts = []
        faceIndices = []
        extent = []
        texCoords = []

        # extents
        bb = r_mesh.GetBoundingBox()
        extent.append([bb.Min.X, bb.Min.Z, -bb.Min.Y])
        extent.append([bb.Max.X, bb.Max.Z, -bb.Max.Y])

        # verts
        for i in range(r_mesh.Vertices.__len__()):
            v = r_mesh.Vertices[i]
            verts.append([v.X,v.Z,-v.Y])
        
        # normals
        for i in range(r_mesh.Normals.__len__()):
            n = r_mesh.Normals[i]
            norms.append([n.X,n.Z,-n.Y])
        
        # texture coordinates
        for i in range(r_mesh.TextureCoordinates.__len__()):
            tc = r_mesh.TextureCoordinates[i]
            texCoords.append([tc.X, tc.Y])

        # faces
        for i in range(r_mesh.Faces.__len__()):
            f = r_mesh.Faces[i]

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

        normPrimvar = mesh.CreatePrimvar("normals", Sdf.ValueTypeNames.Normal3fArray, UsdGeom.Tokens.faceVarying)
        normPrimvar.Set(norms)

        texPrimvar = mesh.CreatePrimvar("Texture_uv", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        texPrimvar.Set(texCoords)

        indices = Vt.IntArray(faceIndices.__len__(), faceIndices)
        texPrimvar.SetIndices(indices)
        normPrimvar.SetIndices(indices)

        mesh.CreateFaceVertexIndicesAttr(faceIndices)
        mesh.CreateFaceVertexCountsAttr(faceCounts)
        mesh.CreateExtentAttr(extent)
        ssa = mesh.CreateSubdivisionSchemeAttr()
        ssa.Set('none')

        return mesh