from pxr import UsdGeom, UsdShade, Sdf
import png
import os
import shutil

class Materializer:

    texDir = '0'
    materialScope = '/materials'
    count = 0

    def __init__(self, stage):
        self.stage = stage
        os.mkdir(self.texDir)
        matScope = UsdGeom.Scope.Define(stage, self.materialScope)

    def getTexture(self, r_mat):
        tex = r_mat.GetBitmapTexture()
        if tex:
            texBase = os.path.basename(tex.FileName)
            #print(texBase)
            dst = os.path.join(self.texDir, texBase)
            if os.access(tex.FileName, os.F_OK):
                shutil.copyfile(tex.FileName, dst)
            elif os.access(os.path.join(modelDir, texBase), os.F_OK):
                shutil.copyfile(path.join(modelDir, texBase), dst)

            return dst
        else: # doing the vectary thing, creating a 2x2 image of the color value
            d = r_mat.DiffuseColor

            alpha = int((1 - r_mat.Transparency) * 255)

            img = [(d[0],d[1],d[2],alpha, d[0],d[1],d[2],alpha),
                (d[0],d[1],d[2],alpha, d[0],d[1],d[2],alpha)]      

            dst = os.path.join(self.texDir, r_mat.Name+'_diffuse.png')
            f = open(dst, 'wb')
            w = png.Writer(width=2, height=2, alpha='RGBA')
            w.write(f,img)
            f.close()
            return dst

    def convertMaterial(self, r_mat):

        if not r_mat.Name:
            nodeName = self.materialScope + '/material_' + str(r_mat.Index)
        else:
            nodeName = self.materialScope + '/' + r_mat.Name.replace(' ', '_').replace('-', '_').replace('(', '_').replace(')', '_') + '_' + str(r_mat.Index)

        #print(nodeName)

        u_mat = UsdShade.Material.Define(self.stage, nodeName)
        stinput = u_mat.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
        stinput.Set('Texture_uv')

        pbrShader = UsdShade.Shader.Define(self.stage, nodeName + '/pbr')
        pbrShader.CreateIdAttr("UsdPreviewSurface")

        #print('Shine on ...'+str(r_mat.Shine))

        # Shine to roughness?
        roughness = 1.0 - (r_mat.Shine / 255.0) # MaxShine
        pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
        # ?
        pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(r_mat.Shine / 255.0) # ?

        pbrShader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set( 1 - r_mat.Transparency)

        u_mat.CreateSurfaceOutput().ConnectToSource(pbrShader, "surface")

        primvarReader = UsdShade.Shader.Define(self.stage, nodeName + '/Primvar')
        primvarReader.CreateIdAttr('UsdPrimvarReader_float2')
        primvarReader.CreateInput('varname', Sdf.ValueTypeNames.Token).ConnectToSource(stinput)

        diffuseTextureSampler = UsdShade.Shader.Define(self.stage, nodeName + '/color_map')
        diffuseTextureSampler.CreateIdAttr('UsdUVTexture')

        diffuse = self.getTexture(r_mat)
        diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(diffuse)

        diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primvarReader, 'result')
        pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Float3).ConnectToSource(diffuseTextureSampler, 'rbg')

        self.count += 1

        return u_mat
