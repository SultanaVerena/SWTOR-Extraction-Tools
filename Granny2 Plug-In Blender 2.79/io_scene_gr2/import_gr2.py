# <pep8 compliant>

"""
This script imports Star Wars: The Old Republic models into Blender.

Usage:
Run this script from "File->Import" menu and then load the desired GR2 model file.
"""

import array
import bpy
import math
import os

from progress_report import ProgressReport
from mathutils import Matrix
from struct import unpack


def ruint8(file):  # Function to read unsigned byte
    return unpack(b'B', file.read(1))[0]


def rfloat8(file):  # Function to read a float that's been encoded as a single byte
    return float((unpack(b'B', file.read(1))[0] - 127.5) / 127.5)


def ruint16(file):  # Function to read unsigned int16
    return unpack(b'<H', file.read(2))[0]


def rfloat16(file):  # Function to read float16
    n = unpack(b'<H', file.read(2))[0]
    assert 0 <= n < 2**16
    sign = n >> 15
    exp = (n >> 10) & 0b011111
    fraction = n & (2**10 - 1)
    if exp == 0:
        if fraction == 0:
            return -0.0 if sign else 0.0
        else:
            return (-1)**sign * fraction / 2**10 * 2**(-14)
    elif exp == 0b11111:
        if fraction == 0:
            return float('-inf') if sign else float('inf')
        else:
            return float('nan')
    return (-1)**sign * (1 + fraction / 2**10) * 2**(exp - 15)


def rint32(file):  # Function to read signed int32
    return unpack(b'<i', file.read(4))[0]


def ruint32(file):  # Function to read unsigned int32
    return unpack(b'<I', file.read(4))[0]


def rfloat32(file):  # Function to read float32
    return unpack(b'<f', file.read(4))[0]


def rstring(file):
    offset = file.tell()

    file.seek(unpack(b'<I', file.read(4))[0])

    string = ""
    byte = file.read(1)

    while byte != b'\x00':
        string += byte.decode('utf-8')
        byte = file.read(1)

    file.seek(offset + 4)

    return string


class GR2MeshPiece():
    def __init__(self, f, offset):
        f.seek(offset)

        self.start_index = ruint32(f)  # Relative offset for this piece's faces
        self.num_faces = ruint32(f)    # Number of faces used by this piece
        self.material_id = ruint32(f)  # Mesh piece material id
        self.piece_index = ruint32(f)  # Mesh piece enumerator (1 x uint32)
        f.seek(0x20, 1)                # Bounding box (8 x 4 bytes)


class GR2Vertex():
    def __init__(self, f, offset, size):
        f.seek(offset)

        self.x = rfloat32(f)  # X Coordinate
        self.y = rfloat32(f)  # Y Coordinate
        self.z = rfloat32(f)  # Z Coordinate

        if size in [32, 36]:
            self.weights = [ruint8(f), ruint8(f), ruint8(f), ruint8(f)]  # Bone Weights
            self.bones = [ruint8(f), ruint8(f), ruint8(f), ruint8(f)]    # Bone Indices

        if size in [24, 32, 36]:
            self.nx = rfloat8(f)  # Normals (X)
            self.ny = rfloat8(f)  # Normals (Y)
            self.nz = rfloat8(f)  # Normals (Z)
            f.seek(0x05, 1)
            self.u = rfloat16(f)  # Texture Map (U)
            self.v = rfloat16(f)  # Texture Map (V)

        if size == 36:
            f.seek(0x04, 1)

    def __iter__(self):
        return iter([self.x, self.y, self.z])


class GR2Face():
    def __init__(self, f, offset):
        f.seek(offset)

        self.v1 = ruint16(f)  # Vertex 1
        self.v2 = ruint16(f)  # Vertex 2
        self.v3 = ruint16(f)  # Vertex 3

    def __iter__(self):
        return iter([self.v1, self.v2, self.v3])


class GR2MeshBone():
    def __init__(self, f, offset):
        f.seek(offset)

        self.name = rstring(f)
        self.bounds = [rfloat32(f) for i in range(6)]


class GR2Mesh():
    def __init__(self, f, offset):
        f.seek(offset)

        self.name = rstring(f)             # Mesh name

        f.seek(0x04, 1)

        self.num_pieces = ruint16(f)       # Number of pieces that make up this mesh
        self.num_used_bones = ruint16(f)   # Number of bones used by this mesh

        f.seek(0x02, 1)

        self.vertex_size = ruint16(f)      # 12 = collision, 24 = static, 32/36 = dynamic
        self.num_vertices = ruint32(f)     # The total number of vertices used by this mesh
        self.num_indicies = ruint32(f)     # The total number of face indicies used by this mesh
        self.offset_vertices = ruint32(f)  # The start address (offset) of the vertices of this mesh
        self.offset_pieces = ruint32(f)    # The start address (offset) of the mesh piece headers
        self.offset_indicies = ruint32(f)  # The start address (offset) of the face indices of this mesh
        self.offset_bones = ruint32(f)     # The start address (offset) of the bone list of this mesh

        # Mesh pieces
        self.pieces = [GR2MeshPiece(f, self.offset_pieces + p * 0x30) for p in range(self.num_pieces)]

        # Vertices
        self.vertices = [GR2Vertex(f, self.offset_vertices + v * self.vertex_size, self.vertex_size) for v in
                         range(self.num_vertices)]

        # Face indicies
        self.faces = [GR2Face(f, self.offset_indicies + i * 0x06) for i in range(self.num_indicies // 3)]

        # Bones
        self.bones = [GR2MeshBone(f, self.offset_bones + b * 0x1C) for b in range(self.num_used_bones)]

    def build(self, mesh_loader):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([list(xyz) for xyz in self.vertices], [], [list(v) for v in self.faces])

        if self.vertex_size in [24, 32, 36]:
            # Link Materials
            for material in mesh_loader.materials:
                me.materials.append(bpy.data.materials[material])
            material_index = [enum for enum, piece in enumerate(self.pieces) for face in range(piece.num_faces)]

            # NOTE: We store 'temp' normals in loops, since validate() may alter final mesh,
            #       we can only set custom loop normals *after* calling it.
            me.create_normals_split()
            me.uv_textures.new()
            for i, poly in enumerate(me.polygons):
                loop_indices = list(poly.loop_indices)
                for e, loop_index in enumerate(loop_indices):
                    v = self.vertices[list(self.faces[i])[e]]
                    me.loops[loop_index].normal = [v.nx, v.ny, v.nz]    # Loop Normals
                    me.uv_layers[0].data[loop_index].uv = [v.u, 1-v.v]  # Loop UVs
                # Map Materials to Faces
                poly.material_index = material_index[i]

            me.validate(clean_customdata=False)

            # Mesh Normals
            custom_loop_normals = array.array('f', [0.0] * (len(me.loops) * 3))
            me.loops.foreach_get("normal", custom_loop_normals)
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
            me.normals_split_custom_set(tuple(zip(*(iter(custom_loop_normals),) * 3)))
            me.use_auto_smooth = True

        # Create Blender object
        obj = bpy.data.objects.new(self.name, me)

        # Create Vertex Groups
        for i, v in enumerate(self.vertices):
            if self.vertex_size in [12, 24]:
                for b in self.bones:

                    if b.name not in obj.vertex_groups:
                        obj.vertex_groups.new(name=b.name)

            elif self.vertex_size in [32, 36]:
                for w in range(4):
                    b = self.bones[v.bones[w]]

                    if b.name not in obj.vertex_groups:
                        obj.vertex_groups.new(name=b.name)

                    obj.vertex_groups[b.name].add([i], float(v.weights[w] / 255), 'ADD')

        # Link Blender object
        bpy.context.scene.objects.link(obj)

        # Adjust the orientation of the model
        obj.matrix_local = Matrix.Rotation(math.pi * 0.5, 4, [1, 0, 0])

        # Deselect all, then select imported model
        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action='DESELECT')
        obj.select = True
        bpy.context.scene.update()
        bpy.context.scene.objects.active = obj


class GR2Bone():
    def __init__(self, f, offset):

        f.seek(offset)

        self.name = rstring(f)
        self.parent_index = unpack(b'<i', f.read(4))[0]
        f.seek(0x40, 1)
        self.root_to_bone = [rfloat32(f) for floats in range(16)]


class GR2Loader():
    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self, operator):
        with open(self.filepath, 'rb') as f:

            # Cancel import if this is a non Bio-Ware Austin / SWTOR GR2 file
            if f.read(4) != b'GAWB':
                operator.report({'ERROR'}, ("\'%s\' is not a valid SWTOR gr2 file.") % self.filepath)
                return {'CANCELLED'}

            f.seek(0x14)

            self.file_type = ruint32(f)  # GR2 file type, 0 = geometry, 1 = geometry with .clo file, 2 = skeleton

            self.num_meshes = ruint16(f)              # Number of meshes in this file
            self.num_materials = ruint16(f)           # Number of materials in this file
            self.num_bones = ruint16(f)               # Number of bones in this file

            f.seek(0x54)

            self.offset_mesh_header = ruint32(f)      # Mesh header offset address
            self.offset_material_header = ruint32(f)  # Material header offset address
            self.offset_bone_structure = ruint32(f)   # Bone structure offset address

            # Check the size of the vertices
            # NOTE: I wish there was a more efficient way to do this!
            for mesh in range(self.num_meshes):
                f.seek((self.offset_mesh_header + 0x0E) + mesh * 0x28)
                vertex_size = ruint16(f)
                if vertex_size not in [12, 24, 32, 36]:
                    operator.report({'ERROR'},
                                    "This add-on supports models that have a vertex size of 12, 24, 32 or 36 bytes. \n"
                                    "\'%s\' has an unsupported vertex size of %i bytes."
                                    % (self.filepath, vertex_size))
                    return {'CANCELLED'}

            # Meshes
            self.meshes = [GR2Mesh(f, self.offset_mesh_header + mesh * 0x28) for mesh in range(self.num_meshes)]

            # Materials
            # NOTE: I wish there was a more efficient way to do this!
            self.materials = []
            if self.num_materials == 0:
                for mesh in self.meshes:
                    if mesh.vertex_size in [24, 32, 36]:
                        for enum, piece in enumerate(mesh.pieces):  # Use "mesh name".00x for name
                            self.materials.append(mesh.name + "." + "{:03d}".format(enum))
            else:
                f.seek(self.offset_material_header)
                for material in range(self.num_materials):          # Use string name for name
                    self.materials.append(rstring(f))

            # Skeleton bones
            self.bones = []
            for b in range(self.num_bones):
                self.bones.append(GR2Bone(f, self.offset_bone_structure + b * 0x88))

    def build(self, import_collision=False):
        # Create Materials
        for material in self.materials:
            new_material = bpy.data.materials.new(name=material)
            new_material.use_nodes = True

        # Create Meshes
        for mesh in self.meshes:
            if "collision" in mesh.name and not import_collision:
                continue
            mesh.build(self)

        # Create Armature
        if self.file_type == 2 and len(self.bones) > 0:
            bpy.ops.object.add(type='ARMATURE', enter_editmode=True)
            armature = bpy.context.object.data
            armature.name = os.path.splitext(os.path.split(self.filepath)[1])[0]
            armature.draw_type = 'STICK'

            for b in self.bones:
                bone = armature.edit_bones.new(b.name)
                bone.tail = [0.00001, 0, 0]

            for i, b in enumerate(self.bones):
                bone = armature.edit_bones[i]
                if b.parent_index >= 0:
                    bone.parent = armature.edit_bones[b.parent_index]

                matrix = Matrix([b.root_to_bone[u*4:u*4+4] for u in range(4)])
                matrix.transpose()
                bone.transform(matrix.inverted())

            bpy.context.object.name = armature.name
            bpy.context.object.matrix_local = Matrix.Rotation(math.pi * 0.5, 4, 'X')
            bpy.ops.object.mode_set(mode='OBJECT')

            self.armature = bpy.context.object


def load(operator, context, filepath=""):
    with ProgressReport(context.window_manager) as progress:

        progress.enter_substeps(3, "Importing \'%s\' ..." % filepath)

        main_loader = GR2Loader(filepath)

        progress.step("Parsing file ...", 1)

        main_loader.parse(operator)

        progress.step("Done, building ...", 2)

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        main_loader.build(operator.import_collision)

        progress.leave_substeps("Done, finished importing: \'%s\'" % filepath)

    return {'FINISHED'}
