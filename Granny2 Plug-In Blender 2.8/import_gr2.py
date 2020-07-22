# <pep8 compliant>

"""
This script imports Star Wars: The Old Republic GR2 files to Blender.

Usage:
Run this script from "File->Import" menu and then load the desired GR2 file.
"""

import array
import bpy
import mathutils

from bpy_extras.io_utils import unpack_list
from bpy_extras.wm_utils.progress_report import ProgressReport
from struct import unpack


def ruint8(file):  # Function to read unsigned byte
    return unpack(b'B', file.read(1))[0]


def rfloat8(file):  # Function to read a float that's been encoded to single byte
    return float((unpack(b'B', file.read(1))[0] - 127.5) / 127.5)


def ruint16(file):  # Function to read unsigned int16
    return unpack(b'<H', file.read(2))[0]


def rfloat16(file):  # Function to read float16
    return unpack(b'<e', file.read(2))[0]


def ruint32(file):  # Function to read unsigned int32
    return unpack(b'<I', file.read(4))[0]


def rfloat32(file):  # Function to read float32
    return unpack(b'<f', file.read(4))[0]


def rstring(file):
    offset = file.seek(unpack(b'<I', file.read(4))[0])
    n = 0
    while file.read(1) != b'\x00':
        n += 1
    file.seek(offset)
    return file.read(n).decode('utf-8')


def create_materials(filepath, relpath, unique_materials):
    """
    Create all the materials in this GR2 file.
    """
    from bpy_extras import node_shader_utils

    nodal_material_wrap_map = {}

    # Create new materials
    for name in unique_materials:
        if name is None:
            pass
        else:
            mat_name = name
            mat = unique_materials[name] = bpy.data.materials.new(mat_name)
            mat_wrap = node_shader_utils.PrincipledBSDFWrapper(
                mat, is_readonly=False)
            nodal_material_wrap_map[mat] = mat_wrap
            mat_wrap.use_nodes = True


def split_mesh(verts_loc, faces, unique_materials, mesh_name):
    """
    Takes vert_loc and faces, and separates into multiple sets of
    (verts_loc, faces, unique_materials, dataname)
    """

    if (len(unique_materials) - 1) == 1 or not faces:
        return [(verts_loc, faces, unique_materials, mesh_name)]

    def key_to_name(key):
        # if the key is a tuple, join it to make a string
        if not key:
            # assume its a string. make sure this is true if the splitting code is changed
            return mesh_name

    # Return a key that makes the faces unique.
    face_split_dict = {}

    oldkey = -1  # initialize to a value that will never match the key

    for face in faces:
        (face_vert_loc_indices,
         face_vert_nor_indices,
         face_vert_tex_indices,
         context_material,
         context_object_key,
         ) = face
        key = context_object_key

        if oldkey != key:
            # Check the key has changed.
            (verts_split, faces_split, unique_materials_split, vert_remap
             ) = face_split_dict.setdefault(key, ([], [], {}, {}))
            oldkey = key

        # Remap verts to new vert list and add where needed
        for loop_idx, vert_idx in enumerate(face_vert_loc_indices):
            map_index = vert_remap.get(vert_idx)
            if map_index is None:
                map_index = len(verts_split)
                # set the new remapped index so we only add once and can reference next time.
                vert_remap[vert_idx] = map_index
                # add the vert to the local verts
                verts_split.append(verts_loc[vert_idx])

            # remap to the local index
            face_vert_loc_indices[loop_idx] = map_index

            if context_material not in unique_materials_split:
                unique_materials_split[context_material] = unique_materials[context_material]

        faces_split.append(face)

    # remove one of the items and reorder
    return [(verts_split, faces_split, unique_materials_split, key_to_name(key))
            for key, (verts_split, faces_split, unique_materials_split, _)
            in face_split_dict.items()]


def create_mesh(new_objects,
                verts_loc,
                verts_nor,
                verts_tex,
                faces,
                unique_materials,
                unique_vgroups,
                vertex_groups,
                dataname,
                ):
    """
    Takes all the data gathered and generates a mesh, adding the new object to new_objects
    deals with ngons, sharp edges and assigning materials
    """

    # Used for storing fgon keys when we need to tessellate/untessellate them (ngons with hole).
    tot_loops = 0

    context_object_key = None

    # reverse loop through face indices
    for f_idx in range(len(faces)):
        face = faces[f_idx]

        (face_vert_loc_indices,
         face_vert_nor_indices,
         face_vert_tex_indices,
         context_material,
         context_object_key,
         ) = face

        len_face_vert_loc_indices = len(face_vert_loc_indices)

        tot_loops += len_face_vert_loc_indices

    # map the material names to an index
    # enumerate over unique_materials keys()
    material_mapping = {name: i for i, name in enumerate(unique_materials)}

    materials = [None] * len(unique_materials)

    for name, index in material_mapping.items():
        materials[index] = unique_materials[name]

    me = bpy.data.meshes.new(dataname)

    # make sure the list isnt too big
    for material in materials:
        if material is not None:
            me.materials.append(material)

    me.vertices.add(len(verts_loc))
    me.loops.add(tot_loops)
    me.polygons.add(len(faces))

    # verts_loc is a list of (x, y, z) tuples
    me.vertices.foreach_set("co", unpack_list(verts_loc))

    loops_vert_idx = tuple(vidx for (face_vert_loc_indices, _,
                                     _, _, _) in faces for vidx in face_vert_loc_indices)
    faces_loop_start = []
    lidx = 0
    for f in faces:
        face_vert_loc_indices = f[0]
        nbr_vidx = len(face_vert_loc_indices)
        faces_loop_start.append(lidx)
        lidx += nbr_vidx
    faces_loop_total = tuple(len(face_vert_loc_indices)
                             for (face_vert_loc_indices, _, _, _, _) in faces)

    me.loops.foreach_set("vertex_index", loops_vert_idx)
    me.polygons.foreach_set("loop_start", faces_loop_start)
    me.polygons.foreach_set("loop_total", faces_loop_total)

    faces_ma_index = tuple(material_mapping[context_material] for (
        _, _, _, context_material, _) in faces)
    me.polygons.foreach_set("material_index", faces_ma_index)

    if verts_nor and me.loops:
        # Note: we store 'temp' normals in loops, since validate() may alter final mesh,
        #       we can only set custom lnors *after* calling it.
        me.create_normals_split()
        loops_nor = tuple(nor for (_, face_vert_nor_indices, _, _, _) in faces
                          for face_nor_idx in face_vert_nor_indices
                          for nor in verts_nor[face_nor_idx])
        me.loops.foreach_set("normal", loops_nor)

    if verts_tex and me.polygons:
        # Some files Do not explicitely write the 'v' value when it's 0.0, see T68249...
        verts_tex = [tex if len(tex) == 2 else tex + [0.0] for tex in verts_tex]
        me.uv_layers.new(do_init=False)
        loops_uv = tuple(tex for (_, _, face_vert_tex_indices, _, _) in faces
                         for face_uv_idx in face_vert_tex_indices
                         for tex in verts_tex[face_uv_idx])
        me.uv_layers[0].data.foreach_set("uv", loops_uv)

    # *Very* important to not remove lnors here!
    me.validate(clean_customdata=False)

    if verts_nor:
        clnors = array.array('f', [0.0] * (len(me.loops) * 3))
        me.loops.foreach_get("normal", clnors)

        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))

        me.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
        me.use_auto_smooth = True

    ob = bpy.data.objects.new(me.name, me)
    new_objects.append(ob)

    # Create the vertex groups. No need to have the flag passed here since we test for the
    # content of the vertex_groups. If the user selects to NOT have vertex groups saved then
    # the following test will never run
    for g_idx, g_name in unique_vgroups.items():
        group = ob.vertex_groups.new(name=g_name)
        for k, v in vertex_groups[g_idx].items():
            group.add([k], v, 'ADD')


def load(operator,
         context,
         filepath,
         *,
         use_groups_as_vgroups=True,
         relpath=None,
         global_matrix=None
         ):
    """
    Called by the user interface or another script.
    load_gr2(path) - should give acceptable results.
    This function passes the file and sends the data off
        to be split into objects and then converted into mesh objects
    """
    def unique_name(existing_names, name_orig):
        i = 0
        if name_orig is None:
            name_orig = b"GR2Object"
        name = name_orig
        while name in existing_names:
            name = b"%s.%03d" % (name_orig, i)
            i += 1
        existing_names.add(name)
        return name

    def create_face(context_material, context_object_key):
        face_vert_loc_indices = []
        face_vert_nor_indices = []
        face_vert_tex_indices = []
        return (
            face_vert_loc_indices,
            face_vert_nor_indices,
            face_vert_tex_indices,
            context_material,
            context_object_key,
        )

    with ProgressReport(context.window_manager) as progress:
        progress.enter_substeps(1, "Importing GR2 \'%s\'..." % filepath)

        if global_matrix is None:
            global_matrix = mathutils.Matrix()

        verts_loc = []
        verts_nor = []
        verts_tex = []
        faces = []  # tuples of the faces
        vertex_groups = {}  # when use_groups_as_vgroups is true

        # Context variables
        context_material = None
        context_object_key = None

        # Until we can use sets
        use_default_material = False
        unique_materials = {}
        unique_vgroups = {}

        # Per-face handling data.
        face_vert_loc_indices = None
        face_vert_nor_indices = None
        face_vert_tex_indices = None
        # verts_loc_len = verts_nor_len = verts_tex_len = 0
        face_items_usage = set()
        face = None

        progress.enter_substeps(3, "Parsing GR2 file...")
        with open(filepath, 'rb') as f:

            # Check this is a valid SWTOR gr2 file
            if f.read(4) != b'GAWB':
                operator.report({'ERROR'},
                                ("\'%s\' is not a valid SWTOR gr2 file.") % filepath)
                return {'CANCELLED'}

            # Check the type of gr2 file
            f.seek(20)
            if f.read(1) == b'2':  # 0 = geometry, 1 = has .clo file, 2 = skeleton.
                operator.report({'ERROR'},
                                ("\'%s\' contains a skeleton. \n Skeleton files are not supported by this addon.")
                                % filepath)
                return {'CANCELLED'}

            # Number of meshes
            f.seek(24)
            num_meshes = ruint16(f)

            # Number of materials
            # f.seek(26)
            # tot_num_mats = ruint16(f)

            # Mesh header offset address
            f.seek(84)
            mesh_header_off = ruint32(f)

            # Material header offset address
            f.seek(88)
            mat_header_off = ruint32(f)

            # Mesh headers
            f.seek(mesh_header_off)
            for mesh in range(0, num_meshes):
                f.seek(mesh_header_off + (40 * mesh))
                mesh_name = rstring(f)  # Mesh name
                f.seek(mesh_header_off + (40 * mesh) + 8)
                num_pieces = ruint16(f)  # Number of pieces that make up this mesh
                num_used_bones = ruint16(f)  # Number of bones used by this mesh
                f.seek(2, 1)
                vert_size = ruint16(f)  # 12 = collision, 24 = static, 32 = dynamic
                num_vert = ruint32(f)  # The total number of vertices used by this mesh
                f.seek(4, 1)
                vert_start_off = ruint32(f)  # The start address (offset) of the vertices of this mesh
                piece_header_off = ruint32(f)  # The start address (offset) of the mesh piece headers
                face_start_off = ruint32(f)  # The start address (offset) of the face indices of this mesh
                bone_start_off = ruint32(f)  # The start address (offset) of the bone list of this mesh

                if vert_size not in [12, 24, 32]:
                    operator.report({'ERROR'},
                                    "\'%s\' cannot be loaded as it uses vertices with a size of %i bytes. \n"
                                    "This addon only supports files that use vertex sizes of 12, 24 or 32 bytes."
                                    % (filepath, vert_size))
                    return {'CANCELLED'}

                if vert_size != 12:
                    # Bone Names
                    f.seek(bone_start_off)
                    for bn in range(0, num_used_bones):
                        f.seek(bone_start_off + (28 * bn))
                        vertex_groups.setdefault(bn, {})
                        unique_vgroups[bn] = rstring(f)

                    # Mesh vertices
                    f.seek(vert_start_off)
                    if num_vert > 0:
                        for v in range(0, num_vert):
                            verts_loc.append([rfloat32(f), rfloat32(f), rfloat32(f)])  # X, Y & Z
                            if vert_size == 32:
                                cur_pos = f.tell()
                                b_idx = []
                                if num_used_bones > 0:
                                    for b in range(0, 4):  # Bones
                                        w = float(ruint8(f) / 255)
                                        f.seek(3, 1)
                                        b_id = ruint8(f)
                                        if b_id not in b_idx:
                                            vertex_groups[b_id][v] = w
                                        b_idx.append(b_id)
                                        f.seek(f.tell() - 4)
                                f.seek(cur_pos + 8)
                            verts_nor.append([rfloat8(f), rfloat8(f), rfloat8(f)])  # Normals
                            f.seek(5, 1)  # Tangents
                            verts_tex.append([rfloat16(f), (1 - rfloat16(f))])  # UVs

                    # Mesh piece headers
                    f.seek(piece_header_off)
                    cur_off = None
                    for piece in range(0, num_pieces):
                        if cur_off:
                            f.seek(cur_off)
                        piece_face_off = face_start_off + (ruint32(f) * 6)  # Relative offset for this piece's faces
                        piece_num_faces = ruint32(f)  # Number of faces used by this piece
                        piece_mat_id = ruint32(f)  # Mesh piece material id
                        f.seek(36, 1)  # Mesh piece enumerator (1 x uin32) & bounding box (8 x 4 bytes)
                        cur_off = f.tell()

                        # Materials
                        if piece_mat_id == 4294967295 and piece == 0:
                            context_material = mesh_name  # Use mesh name for material name
                        elif piece_mat_id == 4294967295:
                            context_material = mesh_name + "_" + str(f'{piece:03d}')  # Use mesh name.00x for material
                        else:
                            f.seek(mat_header_off)
                            f.seek(4 * piece, 1)
                            context_material = rstring(f)  # Use material's name
                        unique_materials[context_material] = None

                        # Mesh piece faces
                        f.seek(piece_face_off)
                        for i in range(0, piece_num_faces):
                            face = create_face(context_material, context_object_key)
                            (face_vert_loc_indices, face_vert_nor_indices, face_vert_tex_indices, _1, _2) = face
                            faces.append(face)
                            face_items_usage.clear()
                            verts_loc_len = len(verts_loc)
                            verts_nor_len = len(verts_nor)
                            verts_tex_len = len(verts_tex)
                            if context_material is None:
                                use_default_material = True

                            for v in range(0, 3):
                                idx = int(ruint16(f))
                                face_vert_loc_indices.append((idx + verts_loc_len) if (idx < 0) else idx)
                                face_vert_tex_indices.append((idx + verts_tex_len) if (idx < 0) else idx)
                                face_vert_nor_indices.append((idx + verts_nor_len) if (idx < 0) else idx)

        progress.step()

        if use_default_material:
            unique_materials[None] = None
        create_materials(filepath, relpath, unique_materials)

        progress.step("Done, building geometries (vertices:%i faces:%i materials:%i) ..." %
                      (len(verts_loc), len(faces), len(unique_materials)))

        # Deselect all
        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action='DESELECT')

        new_objects = []

        for data in split_mesh(verts_loc, faces, unique_materials, mesh_name):
            verts_loc_split, faces_split, unique_materials_split, dataname = data
            create_mesh(new_objects,
                        verts_loc_split,
                        verts_nor,
                        verts_tex,
                        faces_split,
                        unique_materials_split,
                        unique_vgroups,
                        vertex_groups,
                        dataname,
                        )

        view_layer = context.view_layer
        collection = view_layer.active_layer_collection.collection

        # Create new blender object
        for obj in new_objects:
            collection.objects.link(obj)
            obj.select_set(True)

            # we could apply this anywhere before scaling.
            obj.matrix_world = global_matrix

        view_layer.update()

        progress.leave_substeps("Done.")
        progress.leave_substeps("Finished importing: \'%s\'" % filepath)

    return {'FINISHED'}
