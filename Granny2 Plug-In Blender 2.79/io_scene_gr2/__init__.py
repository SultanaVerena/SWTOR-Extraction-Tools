# <pep8 compliant>

import bpy

from bpy.props import (
    BoolProperty,
    StringProperty
)
from bpy_extras.io_utils import ImportHelper


bl_info = {
    "name": "Star Wars: The Old Republic (.gr2)",
    "author": "Darth Atroxa",
    "version": (2, 79, 0),
    "blender": (2, 79, 0),
    "location": "File > Import-Export",
    "description": "Import-Export SWTOR model with bone weights, UV's and materials",
    "support": 'COMMUNITY',
    "category": "Import-Export"}


class ImportGR2(bpy.types.Operator, ImportHelper):
    """Import from SWTOR GR2 file format (.gr2)"""
    bl_idname = "import_scene.gr2"
    bl_label = "Import SWTOR (.gr2)"
    bl_options = {'UNDO'}

    filename_ext = ".gr2"
    filter_glob = StringProperty(default="*.gr2", options={'HIDDEN'})

    import_collision = BoolProperty(name="Import Collision Mesh", default=False)

    def execute(self, context):
        from . import import_gr2
        return import_gr2.load(self, context, self.filepath)


def menu_func_import(self, context):
    self.layout.operator(ImportGR2.bl_idname, text="SW:TOR (.gr2)")


def register():
    bpy.utils.register_class(ImportGR2)

    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.INFO_MT_file_import.remove(menu_func_import)

    bpy.utils.unregister_class(ImportGR2)


if __name__ == "__main__":
    register()
