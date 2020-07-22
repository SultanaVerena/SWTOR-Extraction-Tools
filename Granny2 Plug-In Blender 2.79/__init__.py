# <pep8-80 compliant>

if "bpy" in locals():
    import importlib
    if "import_gr2" in locals():
        importlib.reload(import_gr2)

import bpy

from bpy.props import (
    BoolProperty,
    # BoolVectorProperty,
    # EnumProperty,
    # FloatProperty,
    # FloatVectorProperty,
    StringProperty,
)
from bpy_extras.io_utils import (
    axis_conversion,
    ExportHelper,
    ImportHelper,
    orientation_helper_factory,
    # path_reference_mode,
)


bl_info = {
    "name": "Star Wars: The Old Republic GR2 Format (.gr2)",
    "author": "The DT Guy",
    "version": (1, 0, 0),
    "blender": (2, 78, 0),
    "location": "File > Import-Export",
    "description": "Import-Export GR2, Import mesh with bone weights, UV's and materials",
    "support": 'COMMUNITY',
    "category": "Import-Export"}


IOGR2OrientationHelper = orientation_helper_factory("IOGR2OrientationHelper", axis_forward='-Z', axis_up='Y')


class ImportGR2(bpy.types.Operator, ImportHelper, IOGR2OrientationHelper):
    """Import from SWTOR GR2 file format (.gr2)"""
    bl_idname = "import_scene.gr2"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Import GR2"         # Display name in the interface.
    bl_options = {'UNDO'}

    filename_ext = ".gr2"
    filter_glob = StringProperty(
            default="*.gr2",
            options={'HIDDEN'},
            )

    def execute(self, context):
        from . import import_gr2

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "split_mode",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix
        keywords["use_cycles"] = (context.scene.render.engine == 'CYCLES')

        if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)

        return import_gr2.load(self, context, **keywords)

    def draw(self, context):
        pass


class GR2_PT_import(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Options"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED', 'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_SCENE_OT_gr2"

    def draw(self, context):
        pass


def menu_func_import(self, context):
    self.layout.operator(ImportGR2.bl_idname, text="SWTOR (.gr2)")


classes = (
    ImportGR2,
    GR2_PT_import
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.INFO_MT_file_import.remove(menu_func_import)

    for cls in classes:
        bpy.utils.unregister_class(cls)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
