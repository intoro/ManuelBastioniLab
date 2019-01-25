#ManuelbastioniLAB - Copyright (C) 2015-2017 Manuel Bastioni
#Official site: www.manuelbastioni.com
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.


bl_info = {
    "name": "ManuelbastioniLAB",
    "author": "Manuel Bastioni",
    "version": (1, 5, 0),
    "blender": (2, 7, 8),
    "location": "View3D > Tools > ManuelbastioniLAB",
    "description": "A complete lab for characters creation",
    "warning": "",
    'wiki_url': "http://www.manuelbastioni.com",
    "category": "Characters"}

import bpy
import os
import json
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.app.handlers import persistent
from . import humanoid
import time
import logging

#import cProfile, pstats, io
#import faulthandler
#faulthandler.enable()

log_path = os.path.join(bpy.context.user_preferences.filepaths.temporary_directory, "manuellab_log.txt")
log_is_writeable = True

try:
    test_writing = open(log_path, 'w')
    test_writing.close()
except:
    print("WARNING: Writing permission error for {0}".format(log_path))
    print("The log will be redirected to the console (here)")
    log_is_writeable = False

lab_logger = logging.getLogger('manuelbastionilab_logger')
lab_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

if log_is_writeable:

    fhandler = logging.FileHandler(log_path, mode ='w')
    fhandler.setLevel(logging.INFO)
    chandler = logging.StreamHandler()
    chandler.setLevel(logging.WARNING)
    fhandler.setFormatter(formatter)
    chandler.setFormatter(formatter)
    lab_logger.addHandler(fhandler)
    lab_logger.addHandler(chandler)

else:

    chandler = logging.StreamHandler()
    chandler.setLevel(logging.INFO)
    chandler.setFormatter(formatter)
    lab_logger.addHandler(chandler)

the_humanoid = humanoid.Humanoid(bl_info["version"])
HUMANOID_TYPES = the_humanoid.build_character_item_list()

gui_status = "NEW_SESSION"
gui_err_msg = ""
gui_active_panel = None

def get_current_blend_name_without_ext():
    current_blend_name = bpy.path.basename(bpy.data.filepath)
    name_without_extension = os.path.splitext(current_blend_name)[0]
    return name_without_extension


def start_lab_session():

    global the_humanoid
    global gui_status,gui_err_msg


    lab_logger.info("Start_the lab session...")
    scn = bpy.context.scene

    obj = None
    is_obj = algorithms.looking_for_humanoid_obj()

    if is_obj[0] == "ERROR":
        gui_status = "ERROR_SESSION"
        gui_err_msg = is_obj[1]
        return

    if is_obj[0] == "NO_OBJ":
        hum_model = the_humanoid.characters_definition[scn.character_name]["reference_model"]

        the_humanoid.load_obj_prototype(hum_model)
        obj = bpy.context.selected_objects[0]
        obj.name = scn.character_name
        obj["manuellab_vers"] = bl_info["version"]

    if is_obj[0] == "FOUND":
        obj = the_humanoid.get_object_by_name(is_obj[1])

    if not obj:
        lab_logger.critical("Init failed. Check the log file: {0}".format(log_path))
        gui_status = "ERROR_SESSION"
        gui_err_msg = "Init failed. Check the log file"
    else:



        the_humanoid.init_database()
        if the_humanoid.has_data:

            if scn.use_cycles:
                scn.render.engine = 'CYCLES'
                if scn.use_lamps:
                    the_humanoid.load_lights()
            else:
                scn.render.engine = 'BLENDER_RENDER'

            lab_logger.info("Rendering engine now is {0}".format(scn.render.engine))

            init_morphing_props(the_humanoid)
            init_categories_props(the_humanoid)
            init_measures_props(the_humanoid)
            init_expression_props(the_humanoid)
            init_restposes_props(the_humanoid)
            init_presets_props(the_humanoid)
            init_pose_props(the_humanoid)
            #init_rnd_generator_props(the_humanoid)
            init_ethnic_props(the_humanoid)
            init_metaparameters_props(the_humanoid)
            init_material_parameters_props(the_humanoid)
            the_humanoid.update_materials()            
            

            if gui_status == "RECOVERY_SESSION":
                lab_logger.info("Re-init the character {0}".format(obj.name))
                if hasattr(obj, "character_ID"):
                    if scn.clean_loading == False:
                        the_humanoid.store_mesh_in_cache()                    
                    the_humanoid.reset_mesh()                    
                    the_humanoid.recover_prop_values_from_obj_attr()                    
                    if scn.clean_loading == False:
                        the_humanoid.restore_mesh_from_cache()                    
                    the_humanoid.reinit_retarget()                    
                else:
                    lab_logger.warning("Recovery failed. Character_ID not present")
            else:
                the_humanoid.reset_mesh()
                pose_type = the_humanoid.characters_definition[scn.character_name]["starting_pose"]
                pose_filepath = os.path.join(the_humanoid.pose_path,pose_type)
                
                the_humanoid.load_pose(pose_filepath)                
                the_humanoid.update_character(mode = "update_all")                
                

            gui_status = "ACTIVE_SESSION"

@persistent
def check_manuelbastionilab_session(dummy):
    global the_humanoid
    global gui_status, gui_err_msg
    scn = bpy.context.scene
    if the_humanoid:
        gui_status = "NEW_SESSION"
        is_obj = algorithms.looking_for_humanoid_obj()
        if is_obj[0] == "FOUND":
            gui_status = "RECOVERY_SESSION"
            if scn.do_not_ask_again:
                start_lab_session()
        if is_obj[0] == "ERROR":
            gui_status = "ERROR_SESSION"
            gui_err_msg = is_obj[1]
            return

bpy.app.handlers.load_post.append(check_manuelbastionilab_session)

def link_to_scene(obj):
    scn = bpy.context.scene
    if obj.name not in scn.object_bases:
        scn.objects.link(obj)
    else:
        lab_logger.warning("The object {0} is already linked to the scene".format(obj.name))


def sync_character_to_props():
    #It's important to avoid problems with Blender undo system
    global the_humanoid
    the_humanoid.sync_character_data_to_obj_props()
    the_humanoid.update_character()

def realtime_update(self, context):
    """
    Update the character while the prop slider moves.
    """
    global the_humanoid
    if the_humanoid.bodydata_realtime_activated:
        #time1 = time.time()
        scn = bpy.context.scene
        the_humanoid.update_character(category_name = scn.morphingCategory, mode="update_realtime")
        the_humanoid.sync_gui_according_measures()
        #print("realtime_update: {0}".format(time.time()-time1))

def age_update(self, context):
    global the_humanoid
    if the_humanoid.metadata_realtime_activated:
        time1 = time.time()
        the_humanoid.calculate_transformation("AGE")

def mass_update(self, context):
    global the_humanoid
    if the_humanoid.metadata_realtime_activated:
        the_humanoid.calculate_transformation("FAT")

def tone_update(self, context):
    global the_humanoid
    if the_humanoid.metadata_realtime_activated:
        the_humanoid.calculate_transformation("MUSCLE")

def modifiers_update(self, context):
    sync_character_to_props()


def preset_update(self, context):
    """
    Update the character while prop slider moves
    """
    scn = bpy.context.scene
    global the_humanoid
    obj = the_humanoid.get_object()
    filepath = os.path.join(
        the_humanoid.preset_path,
        "".join([obj.preset, ".json"]))
    the_humanoid.load_character(filepath, mix=scn.mix_characters)

def ethnic_update(self, context):
    scn = bpy.context.scene
    global the_humanoid
    obj = the_humanoid.get_object()
    filepath = os.path.join(
        the_humanoid.ethnic_path,
        "".join([obj.ethnic, ".json"]))
    the_humanoid.load_character(filepath, mix=scn.mix_characters)

def pose_update(self, context):
    """
    Load pose quaternions
    """
    global the_humanoid
    obj = the_humanoid.get_object()
    filepath = os.path.join(
        the_humanoid.pose_path,
        "".join([obj.static_pose, ".json"])) 
    the_humanoid.remove_source_armature()
    the_humanoid.load_pose(filepath)
    

def material_update(self, context):
    global the_humanoid
    if the_humanoid.material_realtime_activated:
        the_humanoid.update_materials(update_textures_nodes = False)

def measure_units_update(self, context):
    global the_humanoid
    the_humanoid.sync_gui_according_measures()

def expression_update(self, context):
    global the_humanoid
    scn = bpy.context.scene
    obj = the_humanoid.get_object()
    filepath = os.path.join(
        the_humanoid.expression_path,
        "".join([obj.expressions, ".json"]))

    the_humanoid.load_character(filepath, reset_string = "Expression", reset_unassigned=False)
    if scn.realtime_expression_fitting:
        the_humanoid.correct_expressions()
        
def restpose_update(self, context):
    global the_humanoid    
    scn = bpy.context.scene
    the_humanoid.final_restpose = scn.restpose    
    

def init_morphing_props(humanoid_instance):
    for prop in humanoid_instance.character_data:
        setattr(
            bpy.types.Object,
            prop,
            bpy.props.FloatProperty(
                name=prop,
                min = -5.0,
                max = 5.0,
                soft_min = 0.0,
                soft_max = 1.0,
                precision=3,
                default=0.5,
                update=realtime_update))

def init_measures_props(humanoid_instance):
    for measure_name,measure_val in humanoid_instance.m_engine.measures.items():
        setattr(
            bpy.types.Object,
            measure_name,
            bpy.props.FloatProperty(
                name=measure_name, min=0.0, max=500.0,
                default=measure_val))
    humanoid_instance.sync_gui_according_measures()


def init_categories_props(humanoid_instance):
    categories_enum = []
    for category in the_humanoid.get_categories()  :
        categories_enum.append(
            (category.name, category.name, category.name))

    bpy.types.Scene.morphingCategory = bpy.props.EnumProperty(
        items=categories_enum,
        update = modifiers_update,
        name="Morphing categories")
        
def init_restposes_props(humanoid_instance):
    
        restposes_items = []
        for database_file in os.listdir(humanoid_instance.restposes_path):
            e_item, extension = os.path.splitext(database_file)
            if "json" in extension:
                restposes_items.append((e_item, e_item, e_item))
        restposes_items.sort()
        bpy.types.Scene.restpose = bpy.props.EnumProperty(
            items=restposes_items,
            name="Rest poses",
            default="a-pose",
            update=restpose_update)


def init_expression_props(humanoid_instance):
    if humanoid_instance.exists_expression_database():
        expression_items = []
        for database_file in os.listdir(humanoid_instance.expression_path):
            e_item, extension = os.path.splitext(database_file)
            if "json" in extension:
                expression_items.append((e_item, e_item, e_item))
        expression_items.sort()
        bpy.types.Object.expressions = bpy.props.EnumProperty(
            items=expression_items,
            name="Expressions",
            update=expression_update)

def init_presets_props(humanoid_instance):
    if humanoid_instance.exists_preset_database():
        preset_items = []
        for database_file in os.listdir(humanoid_instance.preset_path):
            p_item, extension = os.path.splitext(database_file)
            if "json" in extension:
                preset_items.append((p_item, p_item, p_item))
        preset_items.sort()
        bpy.types.Object.preset = bpy.props.EnumProperty(
            items=preset_items,
            name="Types",
            update=preset_update)

def init_pose_props(humanoid_instance):
    if humanoid_instance.exists_poses_database():
        pose_items = []
        for database_file in os.listdir(humanoid_instance.pose_path):
            po_item, extension = os.path.splitext(database_file)
            if "json" in extension:
                pose_items.append((po_item, po_item, po_item))
        pose_items.sort()
        bpy.types.Object.static_pose = bpy.props.EnumProperty(
            items=pose_items,
            name="Pose",
            update=pose_update)

def init_ethnic_props(humanoid_instance):
    if humanoid_instance.exists_phenotype_database():
        ethnic_items = []
        for database_file in os.listdir(humanoid_instance.ethnic_path):
            et_item, extension = os.path.splitext(database_file)
            if "json" in extension:
                ethnic_items.append((et_item, et_item, et_item))
        ethnic_items.sort()
        bpy.types.Object.ethnic = bpy.props.EnumProperty(
            items=ethnic_items,
            name="Phenotype",
            update=ethnic_update)


def init_metaparameters_props(humanoid_instance):
    for meta_data_prop in humanoid_instance.character_metaproperties.keys():
        upd_function = None

        if "age" in meta_data_prop:
            upd_function = age_update
        if "mass" in meta_data_prop:
            upd_function = mass_update
        if "tone" in meta_data_prop:
            upd_function = tone_update
        if "last" in meta_data_prop:
            upd_function = None

        if "last_" not in meta_data_prop:
            setattr(
                bpy.types.Object,
                meta_data_prop,
                bpy.props.FloatProperty(
                    name=meta_data_prop, min=-1.0, max=1.0,
                    precision=3,
                    default=0.0,
                    update=upd_function))


def init_material_parameters_props(humanoid_instance):

    for material_data_prop, value in humanoid_instance.character_material_properties.items():        
        setattr(
            bpy.types.Object,
            material_data_prop,
            bpy.props.FloatProperty(
                name=material_data_prop,
                min = 0.0,
                max = 1.0,
                precision=2,
                update = material_update,
                default=value))


bpy.types.Object.proxy_ID = bpy.props.StringProperty(
    name="human_ID",
    maxlen = 1024,
    default= "-")

bpy.types.Scene.do_not_ask_again = bpy.props.BoolProperty(
    name="Do not ask me again for this scene",
    default = False,
    description="If checked, next time the the file is loaded the init will start automatically")
    
bpy.types.Scene.remove_all_modifiers = bpy.props.BoolProperty(
    name="Remove modifiers",
    default = False,
    description="If checked, all the modifiers will be removed, except the armature one (displacement, subdivision, corrective smooth, etc) will be removed from the finalized character)")

bpy.types.Scene.clean_loading = bpy.props.BoolProperty(
    name="Regenerate the character",
    default = False,
    description="Clean the manual edits and approximation errors")

bpy.types.Scene.use_cycles = bpy.props.BoolProperty(
    name="Use Cycles materials (needed for skin shaders)",
    default = True,
    description="This is needed in order to use the skin editor and shaders (highly recommended)")

bpy.types.Scene.use_lamps = bpy.props.BoolProperty(
    name="Use portrait studio lights (recommended)",
    default = True,
    description="Add a set of lights optimized for portrait. Useful during the design of skin (recommended)")

bpy.types.Scene.show_measures = bpy.props.BoolProperty(
    name="Body measures",
    description="Show measures controls",
    update = modifiers_update)

bpy.types.Scene.measure_filter = bpy.props.StringProperty(
    name="Filter",
    default = "",
    description="Filter the measures to show")


bpy.types.Scene.mix_characters = bpy.props.BoolProperty(
    name="Mix with current",
    description="Mix templates")

bpy.types.Scene.realtime_expression_fitting = bpy.props.BoolProperty(
    name="Fit expressions",
    description="Fit the expression to character face (slower)")

bpy.types.Scene.character_name = bpy.props.EnumProperty(
    items=HUMANOID_TYPES,
    name="Select",
    default="human_female_base01")

bpy.types.Scene.save_images_and_backup = bpy.props.BoolProperty(
    name="Save images and backup character",
    description="Save all images from the skin shader and backup the character in json format",
    default = True)

bpy.types.Object.use_inch = bpy.props.BoolProperty(
    name="Inch",
    update = measure_units_update,
    description="Use inch instead of cm")

bpy.types.Scene.export_proportions = bpy.props.BoolProperty(
    name="Include proportions",
    description="Include proportions in the exported character file")

bpy.types.Scene.export_materials = bpy.props.BoolProperty(
    name="Include materials",
    default = True,
    description="Include materials in the exported character file")

bpy.types.Scene.show_texture_load_save = bpy.props.BoolProperty(
    name="Import-export images",
    description="Show controls to import and export texture images")

bpy.types.Scene.fix_proxy_intersection = bpy.props.BoolProperty(
    name="Try to correct intersections",
    description="Try to fix the intersections between skin and proxy")



bpy.types.Scene.preserve_mass = bpy.props.BoolProperty(
    name="Mass",
    description="Preserve the current relative mass percentage")

bpy.types.Scene.preserve_height = bpy.props.BoolProperty(
    name="Height",
    description="Preserve the current character height")

bpy.types.Scene.preserve_tone = bpy.props.BoolProperty(
    name="Tone",
    description="Preserve the current relative tone percentage")

bpy.types.Scene.preserve_body = bpy.props.BoolProperty(
    name="Body",
    description="Preserve the body features")

bpy.types.Scene.preserve_face = bpy.props.BoolProperty(
    name="Face",
    description="Preserve the face features, but not the head shape")

bpy.types.Scene.preserve_phenotype = bpy.props.BoolProperty(
    name="Phenotype",
    description="Preserve characteristic traits, like people that are members of the same family")

bpy.types.Scene.set_tone_and_mass = bpy.props.BoolProperty(
    name="Use fixed tone and mass values",
    description="Enable the setting of fixed values for mass and tone using a slider UI")

bpy.types.Scene.body_mass = bpy.props.FloatProperty(
    name="Body mass",
    min=0.0,
    max=1.0,
    default = 0.5,
    description="Preserve the current character body mass")

bpy.types.Scene.body_tone = bpy.props.FloatProperty(
    name="Body tone",
    min=0.0,
    max=1.0,
    default = 0.5,
    description="Preserve the current character body mass")

bpy.types.Scene.random_engine = bpy.props.EnumProperty(
                items = [("LI", "Light", "Little variations from the standard"),
                        ("RE", "Realistic", "Realistic characters"),
                        ("NO", "Noticeable", "Very characterized people"),
                        ("CA", "Caricature", "Engine for caricatures"),
                        ("EX", "Extreme", "Extreme characters")],
                name = "Engine",
                default = "LI")


class ButtonParametersOff(bpy.types.Operator):

    bl_label = 'Body, face and measure parameters'
    bl_idname = 'mbast_button.parameters_off'
    bl_description = 'Close details panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonParametersOn(bpy.types.Operator):
    bl_label = 'Body. face and measure parameters'
    bl_idname = 'mbast_button.parameters_on'
    bl_description = 'Open details panel (head,nose,hands, measures etc...)'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = "parameters"
        sync_character_to_props()
        return {'FINISHED'}

class ButtonExpressionsOff(bpy.types.Operator):
    bl_label = 'Face expressions'
    bl_idname = 'mbast_button.expressions_off'
    bl_description = 'Close expressions panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonExpressionOn(bpy.types.Operator):
    bl_label = 'Face expressions'
    bl_idname = 'mbast_button.expressions_on'
    bl_description = 'Open expressions panel (head,nose,hands etc...)'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = "expressions"
        sync_character_to_props()
        return {'FINISHED'}

class ButtonRandomOff(bpy.types.Operator):
    bl_label = 'Random generator'
    bl_idname = 'mbast_button.random_off'
    bl_description = 'Close random generator panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonRandomOn(bpy.types.Operator):
    bl_label = 'Random generator'
    bl_idname = 'mbast_button.random_on'
    bl_description = 'Open random generator panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'random'
        sync_character_to_props()
        return {'FINISHED'}


class ButtonAutomodellingOff(bpy.types.Operator):

    bl_label = 'Automodelling tools'
    bl_idname = 'mbast_button.automodelling_off'
    bl_description = 'Close automodelling panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonAutomodellingOn(bpy.types.Operator):
    bl_label = 'Automodelling tools'
    bl_idname = 'mbast_button.automodelling_on'
    bl_description = 'Open automodelling panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'automodelling'
        return {'FINISHED'}

class ButtoPoseOff(bpy.types.Operator):
    bl_label = 'Pose and animation'
    bl_idname = 'mbast_button.pose_off'
    bl_description = 'Close pose panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonPoseOn(bpy.types.Operator):
    bl_label = 'Pose and animation'
    bl_idname = 'mbast_button.pose_on'
    bl_description = 'Open pose panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'pose'
        return {'FINISHED'}


class ButtonSkinOff(bpy.types.Operator):
    bl_label = 'Skin editor'
    bl_idname = 'mbast_button.skin_off'
    bl_description = 'Close skin editor panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonSkinOn(bpy.types.Operator):
    bl_label = 'Skin editor'
    bl_idname = 'mbast_button.skin_on'
    bl_description = 'Open skin editor panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'skin'
        return {'FINISHED'}

class ButtonViewOptOff(bpy.types.Operator):
    bl_label = 'Display options'
    bl_idname = 'mbast_button.display_off'
    bl_description = 'Close skin editor panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonViewOptOn(bpy.types.Operator):
    bl_label = 'Display options'
    bl_idname = 'mbast_button.display_on'
    bl_description = 'Open skin editor panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'display_opt'
        return {'FINISHED'}




class ButtonProxyOff(bpy.types.Operator):
    bl_label = 'Proxy tools'
    bl_idname = 'mbast_button.proxy_off'
    bl_description = 'Close proxy panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonProxyOn(bpy.types.Operator):
    bl_label = 'Proxy tools'
    bl_idname = 'mbast_button.proxy_on'
    bl_description = 'Open proxy panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'proxy'
        return {'FINISHED'}


class ButtonFilesOff(bpy.types.Operator):
    bl_label = 'File tools'
    bl_idname = 'mbast_button.file_off'
    bl_description = 'Close file panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """

        """
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonFilesOn(bpy.types.Operator):
    bl_label = 'File tools'
    bl_idname = 'mbast_button.file_on'
    bl_description = 'Open file panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'file'
        return {'FINISHED'}


class ButtonFinalizeOff(bpy.types.Operator):
    bl_label = 'Finalize tools'
    bl_idname = 'mbast_button.finalize_off'
    bl_description = 'Close finalize panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonFinalizeOn(bpy.types.Operator):
    bl_label = 'Finalize tools'
    bl_idname = 'mbast_button.finalize_on'
    bl_description = 'Open finalize panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'finalize'
        return {'FINISHED'}

class ButtonLibraryOff(bpy.types.Operator):
    bl_label = 'Character library'
    bl_idname = 'mbast_button.library_off'
    bl_description = 'Close character library panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}

class ButtonLibraryOn(bpy.types.Operator):
    bl_label = 'Character library'
    bl_idname = 'mbast_button.library_on'
    bl_description = 'Open character library panel'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'library'
        return {'FINISHED'}


class UpdateSkinDisplacement(bpy.types.Operator):
    """
    Calculate and apply the skin displacement
    """
    bl_label = 'Update displacement'
    bl_idname = 'mbast_skindisplace.calculate'
    bl_description = 'Calculate and apply the skin details using displace modifier'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """
        Calculate and apply the skin displacement
        """
        global the_humanoid
        scn = bpy.context.scene
        the_humanoid.update_displacement()
        the_humanoid.update_materials()
        return {'FINISHED'}


class DisableSubdivision(bpy.types.Operator):
    """
    Disable subdivision surface
    """
    bl_label = 'Disable subdivision preview'
    bl_idname = 'mbast_subdivision.disable'
    bl_description = 'Disable subdivision modifier'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global the_humanoid
        scn = bpy.context.scene

        if the_humanoid.get_subd_visibility() == True:
            the_humanoid.set_subd_visibility(False)
        return {'FINISHED'}

class EnableSubdivision(bpy.types.Operator):
    """
    Enable subdivision surface
    """
    bl_label = 'Enable subdivision preview'
    bl_idname = 'mbast_subdivision.enable'
    bl_description = 'Enable subdivision preview (Warning: it will slow down the morphing)'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global the_humanoid
        scn = bpy.context.scene

        if the_humanoid.get_subd_visibility() == False:
            the_humanoid.set_subd_visibility(True)
        return {'FINISHED'}

class DisableSmooth(bpy.types.Operator):

    bl_label = 'Disable corrective smooth'
    bl_idname = 'mbast_corrective.disable'
    bl_description = 'Disable corrective smooth modifier in viewport'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global the_humanoid
        scn = bpy.context.scene

        if the_humanoid.get_smooth_visibility() == True:
            the_humanoid.set_smooth_visibility(False)
        return {'FINISHED'}

class EnableSmooth(bpy.types.Operator):

    bl_label = 'Enable corrective smooth'
    bl_idname = 'mbast_corrective.enable'
    bl_description = 'Enable corrective smooth modifier in viewport'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global the_humanoid
        scn = bpy.context.scene

        if the_humanoid.get_smooth_visibility() == False:
            the_humanoid.set_smooth_visibility(True)
        return {'FINISHED'}

class DisableDisplacement(bpy.types.Operator):
    """
    Disable displacement modifier
    """
    bl_label = 'Disable displacement preview'
    bl_idname = 'mbast_displacement.disable'
    bl_description = 'Disable displacement modifier'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global the_humanoid
        scn = bpy.context.scene

        if the_humanoid.get_disp_visibility() == True:
            the_humanoid.set_disp_visibility(False)
        return {'FINISHED'}

class EnableDisplacement(bpy.types.Operator):
    """
    Enable displacement modifier
    """
    bl_label = 'Enable displacement preview'
    bl_idname = 'mbast_displacement.enable'
    bl_description = 'Enable displacement preview (Warning: it will slow down the morphing)'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global the_humanoid
        scn = bpy.context.scene

        if the_humanoid.get_disp_visibility() == False:
            the_humanoid.set_disp_visibility(True)
        return {'FINISHED'}


class FinalizeCharacterAndImages(bpy.types.Operator,ExportHelper):
    """
    Convert the expression morphings to Blender standard shape keys
    """
    bl_label = 'Finalize with textures and backup'
    bl_idname = 'mbast_mbast_finalize.character_and_images'
    filename_ext = ".png"
    filter_glob = bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
        )
    bl_description = 'Finalize, saving all the textures and converting the parameters in shapekeys. Warning: after the conversion the character will be no longer modifiable using ManuelbastioniLAB tools'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """
        Convert the character in a standard Blender model
        """
        global the_humanoid
        global gui_status
        scn = bpy.context.scene

        the_humanoid.change_rest_pose()
        if scn.remove_all_modifiers:            
            the_humanoid.remove_modifiers()
        the_humanoid.save_backup_character(self.filepath)
        the_humanoid.save_all_textures(self.filepath)
        the_humanoid.correct_expressions(correct_all=True)
        the_humanoid.m_engine.convert_all_to_blshapekeys()
        the_humanoid.delete_all_properties()
        the_humanoid.rename_materials()
        the_humanoid.rename_obj()
        gui_status = "NEW_SESSION"
        return {'FINISHED'}

class FinalizeCharacter(bpy.types.Operator):
    """
    Convert the expression morphings to Blender standard shape keys
    """
    bl_label = 'Finalize'
    bl_idname = 'mbast_finalize.character'
    bl_description = 'Finalize converting the parameters in shapekeys. Warning: after the conversion the character will be no longer modifiable using ManuelbastioniLAB tools'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """
        Convert the character in a standard Blender model
        """
        global the_humanoid
        global gui_status
        scn = bpy.context.scene
        the_humanoid.change_rest_pose()
        if scn.remove_all_modifiers:            
            the_humanoid.remove_modifiers()
        the_humanoid.correct_expressions(correct_all=True)
        the_humanoid.m_engine.convert_all_to_blshapekeys()
        the_humanoid.delete_all_properties()
        the_humanoid.rename_materials()
        the_humanoid.rename_obj()
        gui_status = "NEW_SESSION"
        return {'FINISHED'}




class ResetParameters(bpy.types.Operator):
    """
    Reset all morphings.
    """
    bl_label = 'Reset character'
    bl_idname = 'mbast_reset.allproperties'
    bl_description = 'Reset all character parameters'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def execute(self, context):
        global the_humanoid
        the_humanoid.reset_character()
        return {'FINISHED'}

class ResetExpressions(bpy.types.Operator):
    """
    Reset all morphings.
    """
    bl_label = 'Reset Expression'
    bl_idname = 'mbast_reset.expression'
    bl_description = 'Reset the expression'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def reset_expression(self):
        global the_humanoid
        scn = bpy.context.scene        
        filepath = os.path.join(
            the_humanoid.expression_path,
            "neutral.json")

        the_humanoid.load_character(filepath, reset_string = "Expression", reset_unassigned=False)

    def execute(self, context):
        self.reset_expression()
        return {'FINISHED'}


class Reset_category(bpy.types.Operator):
    """
    Reset the parameters for the currently selected category
    """
    bl_label = 'Reset category'
    bl_idname = 'mbast_reset.categoryonly'
    bl_description = 'Reset the parameters for the current category'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def execute(self, context):
        global the_humanoid
        scn = bpy.context.scene
        the_humanoid.reset_category(scn.morphingCategory)
        return {'FINISHED'}


class CharacterGenerator(bpy.types.Operator):
    """
    Generate a new character using the specified parameters.
    """
    bl_label = 'Generate'
    bl_idname = 'mbast_character.generator'
    bl_description = 'Generate a new character according the parameters.'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def execute(self, context):
        global the_humanoid
        scn = bpy.context.scene
        rnd_values = {"LI": 0.05, "RE": 0.1, "NO": 0.2, "CA":0.3, "EX": 0.5}
        rnd_val = rnd_values[scn.random_engine]
        p_face = scn.preserve_face
        p_body = scn.preserve_body
        p_mass = scn.preserve_mass
        p_tone = scn.preserve_tone
        p_height = scn.preserve_height
        p_phenotype = scn.preserve_phenotype
        set_tone_mass = scn.set_tone_and_mass
        b_tone = scn.body_tone
        b_mass = scn.body_mass

        the_humanoid.generate_character(rnd_val,p_face,p_body,p_mass,p_tone,p_height,p_phenotype,set_tone_mass,b_mass,b_tone)
        return {'FINISHED'}

class ExpDisplacementImage(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast_export.dispimage"
    bl_label = "Save displacement image"
    filename_ext = ".png"
    filter_glob = bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.save_body_displacement_texture(self.filepath)
        return {'FINISHED'}

class ExpDermalImage(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast_export.dermimage"
    bl_label = "Save dermal image"
    filename_ext = ".png"
    filter_glob = bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.save_body_dermal_texture(self.filepath)
        return {'FINISHED'}


class ExpAllImages(bpy.types.Operator, ExportHelper):
    """
    """
    bl_idname = "mbast_export.allimages"
    bl_label = "Export all images"
    filename_ext = ".png"
    filter_glob = bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.save_all_textures(self.filepath)
        return {'FINISHED'}



class ExpCharacter(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast_export.character"
    bl_label = "Export character"
    filename_ext = ".json"
    filter_glob = bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        scn = bpy.context.scene
        the_humanoid.save_character(self.filepath, scn.export_proportions, scn.export_materials)
        return {'FINISHED'}

class ExpMeasures(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast_export.measures"
    bl_label = "Export measures"
    filename_ext = ".json"
    filter_glob = bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.export_measures(self.filepath)
        return {'FINISHED'}


class ImpCharacter(bpy.types.Operator, ImportHelper):
    """
    Import parameters for the character
    """
    bl_idname = "mbast_import.character"
    bl_label = "Import character"
    filename_ext = ".json"
    filter_glob = bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid

        char_data = the_humanoid.load_character(self.filepath)
        return {'FINISHED'}

class ImpMeasures(bpy.types.Operator, ImportHelper):
    """
    Import parameters for the character
    """
    bl_idname = "mbast_import.measures"
    bl_label = "Import measures"
    filename_ext = ".json"
    filter_glob = bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.import_measures(self.filepath)
        return {'FINISHED'}


class LoadDermImage(bpy.types.Operator, ImportHelper):
    """

    """
    bl_idname = "mbast_import.dermal"
    bl_label = "Load dermal image"
    filename_ext = ".png"
    filter_glob = bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.load_body_dermal_texture(self.filepath)
        return {'FINISHED'}


class LoadDispImage(bpy.types.Operator, ImportHelper):
    """

    """
    bl_idname = "mbast_import.displacement"
    bl_label = "Load displacement image"
    filename_ext = ".png"
    filter_glob = bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.load_body_displacement_texture(self.filepath)
        return {'FINISHED'}


class SaveProxy(bpy.types.Operator):
    """
    Calibrate the proxy object in order to be automatically adapted to body variation
    of the current humanoid. The data is calculated and stored the user temp directory.
    """

    bl_label = 'Calibrate Proxy'
    bl_idname = 'mbast_proxy.calibrate'
    bl_description = 'Register proxy for auto fitting'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global the_humanoid
        proxy_status = the_humanoid.validate_proxy_for_calibration()

        if proxy_status == "OK":
            the_humanoid.calibrate_proxy()
            self.report({'INFO'}, "Proxy calibrated.")
        else:
            self.report({'ERROR'}, proxy_status)
        return {'FINISHED'}

class ResetProxy(bpy.types.Operator):
    """
    Reset the proxy
    """

    bl_label = 'Reset Proxy'
    bl_idname = 'mbast_proxy.reset'
    bl_description = 'Reset the proxy in order to modify it and recalibrate it'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global the_humanoid
        proxy_status = the_humanoid.validate_proxy_for_selection()

        if proxy_status == "IS_PROXY":
            the_humanoid.reset_proxy()
            self.report({'INFO'}, "Proxy resetted.")
        else:
            self.report({'ERROR'}, proxy_status)
        return {'FINISHED'}



class FitProxy(bpy.types.Operator):
    """
    For each proxy in the scene, load the data and then fit it.
    """

    bl_label = 'Fit Proxiy'
    bl_idname = 'mbast_proxy.fit'
    bl_description = 'Fit the selected proxy to the character'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}


    def execute(self, context):
        global the_humanoid
        scn = bpy.context.scene
        #the_humanoid.disable_human_modifiers()
        the_humanoid.fit_proxy(fix_intersection = scn.fix_proxy_intersection)

        return {'FINISHED'}


class ApplyMeasures(bpy.types.Operator):
    """
    Fit the character to the measures
    """

    bl_label = 'Update character'
    bl_idname = 'mbast_measures.apply'
    bl_description = 'Fit the character to the measures'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global the_humanoid
        the_humanoid.automodelling(use_measures_from_GUI=True)
        return {'FINISHED'}


class AutoModelling(bpy.types.Operator):
    """
    Fit the character to the measures
    """

    bl_label = 'Auto modelling'
    bl_idname = 'mbast_auto.modelling'
    bl_description = 'Analyze the mesh form and return a verisimilar human'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def execute(self, context):
        global the_humanoid
        the_humanoid.automodelling(use_measures_from_current_obj=True)
        return {'FINISHED'}

class AutoModellingMix(bpy.types.Operator):
    """
    Fit the character to the measures
    """

    bl_label = 'Averaged auto modelling'
    bl_idname = 'mbast_auto.modellingmix'
    bl_description = 'Return a verisimilar human with multiple interpolations that make it nearest to average'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def execute(self, context):
        global the_humanoid
        the_humanoid.automodelling(use_measures_from_current_obj=True, mix = True)
        return {'FINISHED'}

class ResetPose(bpy.types.Operator):
    """
    For each proxy in the scene, load the data and then fit it.
    """

    bl_label = 'Reset pose and animation'
    bl_idname = 'mbast_pose.reset'
    bl_description = 'Reset the character pose and delete the current animation'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def execute(self, context):
        global the_humanoid
        the_humanoid.remove_source_armature()
        the_humanoid.reset_pose()
        return {'FINISHED'}


class SavePose(bpy.types.Operator, ExportHelper):
    """Export pose"""
    bl_idname = "mbast_pose.save"
    bl_label = "Save pose"
    filename_ext = ".json"
    filter_glob = bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.save_pose(self.filepath)
        return {'FINISHED'}

class LoadPose(bpy.types.Operator, ImportHelper):
    """
    Import parameters for the character
    """
    bl_idname = "mbast_pose.load"
    bl_label = "Load pose"
    filename_ext = ".json"
    filter_glob = bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid
        the_humanoid.remove_source_armature()
        the_humanoid.load_pose(self.filepath)
        
        return {'FINISHED'}

class RetargetBvh(bpy.types.Operator, ImportHelper):
    """
    Import parameters for the character
    """
    bl_idname = "mbast_retarget.bvh"
    bl_label = "Import animation (bvh)"
    filename_ext = ".json"
    bl_description = 'Import the animation from a bvh motion capture file'
    filter_glob = bpy.props.StringProperty(
        default="*.bvh",
        options={'HIDDEN'},
        )
    bl_context = 'objectmode'

    def execute(self, context):
        global the_humanoid

        char_data = the_humanoid.retarget_bvh(self.filepath)
        return {'FINISHED'}

class StartSession(bpy.types.Operator):
    bl_idname = "mbast_init.character"
    bl_label = "Init character"
    bl_description = 'Create the character selected above'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    def execute(self, context):
        start_lab_session()
        return {'FINISHED'}





class ManuelLabPanel(bpy.types.Panel):

    bl_label = "ManuelbastioniLAB {0}.{1}.{2}".format(bl_info["version"][0],bl_info["version"][1],bl_info["version"][2])
    bl_idname = "OBJECT_PT_characters01"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'
    bl_category = "ManuelBastioniLAB"


    def draw(self, context):

        global the_humanoid,gui_status,gui_err_msg,gui_active_panel
        scn = bpy.context.scene
        icon_expand = "DISCLOSURE_TRI_RIGHT"
        icon_collapse = "DISCLOSURE_TRI_DOWN"

        if gui_status == "ERROR_SESSION":
            box = self.layout.box()
            box.alert = True
            box.label(gui_err_msg, icon="ERROR")

        if gui_status == "RECOVERY_SESSION":
            box = self.layout.box()
            box.label("I detected an existent lab session")
            box.label("To try a recover, press init button")
            box.prop(scn,'use_cycles')
            if scn.use_cycles:
                box.prop(scn,'use_lamps')
            box.prop(scn,'clean_loading')
            box.operator('mbast_init.character')
            box.prop(scn,'do_not_ask_again')

        if gui_status == "NEW_SESSION":
            box = self.layout.box()
            box.prop(scn, 'character_name')
            box.prop(scn,'use_cycles')
            if scn.use_cycles:
                box.prop(scn,'use_lamps')
            box.operator('mbast_init.character')

        if gui_status == "ACTIVE_SESSION":
            obj = the_humanoid.get_object()

            if obj:
                box = self.layout.box()

                if the_humanoid.exists_transform_database():
                    box.label("Meta parameters")
                    x_age = getattr(obj,'character_age',0)
                    x_mass = getattr(obj,'character_mass',0)
                    x_tone = getattr(obj,'character_tone',0)

                    age_lbl = round((15.5*x_age**2)+31*x_age+33)
                    mass_lbl = round(50*(x_mass+1))
                    tone_lbl = round(50*(x_tone+1))
                    lbl_text = "Age: {0}y  Mass: {1}%  Tone: {2}% ".format(age_lbl,mass_lbl,tone_lbl)
                    box.label(lbl_text,icon="RNA")

                    for meta_data_prop in sorted(the_humanoid.character_metaproperties.keys()):
                        if "last" not in meta_data_prop:
                            box.prop(obj, meta_data_prop)
                    box.operator("mbast_reset.allproperties", icon="LOAD_FACTORY")

                if gui_active_panel != "library":
                    self.layout.operator('mbast_button.library_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.library_off', icon=icon_collapse)
                    box = self.layout.box()

                    box.label("Characters library")
                    if the_humanoid.exists_preset_database():
                        box.prop(obj, "preset")
                    if the_humanoid.exists_phenotype_database():
                        box.prop(obj, "ethnic")
                    box.prop(scn, 'mix_characters')

                if gui_active_panel != "expressions":
                    self.layout.operator('mbast_button.expressions_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.expressions_off', icon=icon_collapse)

                    box = self.layout.box()
                    box.prop(obj, "expressions")
                    box.prop(scn, 'realtime_expression_fitting')
                    box.operator("mbast_reset.expression", icon="RECOVER_AUTO")

                if gui_active_panel != "random":
                    self.layout.operator('mbast_button.random_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.random_off', icon=icon_collapse)

                    box = self.layout.box()
                    box.prop(scn, "random_engine")
                    box.prop(scn, "set_tone_and_mass")
                    if scn.set_tone_and_mass:
                        box.prop(scn, "body_mass")
                        box.prop(scn, "body_tone")

                    box.label("Preserve:")
                    box.prop(scn, "preserve_mass")
                    box.prop(scn, "preserve_height")
                    box.prop(scn, "preserve_tone")
                    box.prop(scn, "preserve_body")
                    box.prop(scn, "preserve_face")
                    box.prop(scn, "preserve_phenotype")

                    box.operator('mbast_character.generator', icon="FILE_REFRESH")

                if gui_active_panel != "parameters":
                    self.layout.operator('mbast_button.parameters_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.parameters_off', icon=icon_collapse)

                    box = self.layout.box()
                    the_humanoid.bodydata_realtime_activated = True
                    if the_humanoid.exists_measure_database():
                        box.prop(scn, 'show_measures')
                    split = box.split()

                    col = split.column()
                    col.label("PARAMETERS")
                    col.prop(scn, "morphingCategory")

                    for prop in the_humanoid.get_properties_in_category(scn.morphingCategory):
                        if hasattr(obj, prop):
                            col.prop(obj, prop)

                    if the_humanoid.exists_measure_database() and scn.show_measures:
                        col = split.column()
                        col.label("DIMENSIONS")
                        col.prop(obj, 'use_inch')
                        col.prop(scn, 'measure_filter')
                        col.operator("mbast_measures.apply")

                        m_unit = "cm"
                        if obj.use_inch:
                            m_unit = "Inches"
                        col.label("Height: {0} {1}".format(round(getattr(obj, "body_height_Z", 0),3),m_unit))
                        for measure in sorted(the_humanoid.measures.keys()):
                            if measure != "body_height_Z":
                                if hasattr(obj, measure):
                                    if scn.measure_filter in measure:
                                        col.prop(obj, measure)

                        col.operator("mbast_export.measures", icon='EXPORT')
                        col.operator("mbast_import.measures", icon='IMPORT')

                    sub = box.box()
                    sub.label("RESET")
                    sub.operator("mbast_reset.categoryonly")


                if the_humanoid.exists_measure_database():
                    if gui_active_panel != "automodelling":
                        self.layout.operator('mbast_button.automodelling_on', icon=icon_expand)
                    else:
                        self.layout.operator('mbast_button.automodelling_off', icon=icon_collapse)
                        box = self.layout.box()
                        box.operator("mbast_auto.modelling")
                        box.operator("mbast_auto.modellingmix")
                else:
                    box = self.layout.box()
                    box.enabled = False
                    box.label("Automodelling not available for this character", icon='INFO')

                if the_humanoid.exists_poses_database():
                    if gui_active_panel != "pose":
                        self.layout.operator('mbast_button.pose_on', icon=icon_expand)
                    else:
                        self.layout.operator('mbast_button.pose_off', icon=icon_collapse)
                        box = self.layout.box()

                        if the_humanoid.exists_source_armature():
                            box.enabled = False
                        else:
                            box.enabled = True
                        box.prop(obj, "static_pose")

                        box.operator("mbast_pose.load", icon='IMPORT')
                        box.operator("mbast_pose.save", icon='EXPORT')                       


                        box = self.layout.box()
                        box.operator("mbast_retarget.bvh", icon='IMPORT')

                        box = self.layout.box()
                        box.operator("mbast_pose.reset", icon='ARMATURE_DATA')
                        if the_humanoid.exists_source_armature():
                            box.label("Reset will delete the current animation", icon='ERROR')



                        #box.operator("mbast_retarget.skeleton")

                if gui_active_panel != "skin":
                    self.layout.operator('mbast_button.skin_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.skin_off', icon=icon_collapse)

                    box = self.layout.box()
                    box.enabled = True
                    if scn.render.engine != 'CYCLES':
                        box.enabled = False
                        box.label("Skin editor requires Cycles", icon='INFO')

                    if the_humanoid.exists_displace_texture():
                        box.operator("mbast_skindisplace.calculate")
                        box.label("You need to enable subdiv and displ to see the displ in viewport", icon='INFO')

                    for material_data_prop in sorted(the_humanoid.character_material_properties.keys()):
                        box.prop(obj, material_data_prop)

                    box.prop(scn, 'show_texture_load_save')
                    if scn.show_texture_load_save:

                        if the_humanoid.exists_dermal_texture():
                            sub = box.box()
                            sub.label("Dermal texture")
                            sub.operator("mbast_export.dermimage", icon='EXPORT')
                            sub.operator("mbast_import.dermal", icon='IMPORT')
                        
                        if the_humanoid.exists_displace_texture():
                            sub = box.box()
                            sub.label("Displacement texture")
                            sub.operator("mbast_export.dispimage", icon='EXPORT')
                            sub.operator("mbast_import.displacement", icon='IMPORT')                        

                        sub = box.box()
                        sub.label("Export all images used in skin shader")
                        sub.operator("mbast_export.allimages", icon='EXPORT')


                if gui_active_panel != "proxy":
                    self.layout.operator('mbast_button.proxy_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.proxy_off', icon=icon_collapse)
                    box = self.layout.box()
                    proxy_status = the_humanoid.validate_proxy_for_selection()

                    if proxy_status == 'IS_PROXY':
                        box.label("The proxy is ready for fitting")
                        box.operator("mbast_proxy.fit", icon="MOD_CLOTH")
                        #box.prop(scn, 'fix_proxy_intersection')
                        box.operator("mbast_proxy.reset")
                    elif "Proxy not calibrated yet" in proxy_status:
                        box.label(proxy_status, icon='INFO')
                        box.label("The proxy need to be calibrated")
                        box.operator("mbast_proxy.calibrate", icon="MOD_CLOTH")
                    elif "Proxy calibrated for" in proxy_status:
                        box.label(proxy_status, icon='INFO')
                        box.label("The proxy need to be recalibrated")
                        box.operator("mbast_proxy.calibrate", icon="MOD_CLOTH")
                    else:
                        box.label(proxy_status, icon='ERROR')


                if gui_active_panel != "file":
                    self.layout.operator('mbast_button.file_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.file_off', icon=icon_collapse)
                    box = self.layout.box()
                    box.prop(scn, 'export_proportions')
                    box.prop(scn, 'export_materials')
                    box.operator("mbast_export.character", icon='EXPORT')
                    box.operator("mbast_import.character", icon='IMPORT')                   


                if gui_active_panel != "finalize":
                    self.layout.operator('mbast_button.finalize_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.finalize_off', icon=icon_collapse)

                    box = self.layout.box()
                    box.prop(scn,"restpose")
                    box.prop(scn, 'save_images_and_backup')
                    box.prop(scn,'remove_all_modifiers')
                    if scn.save_images_and_backup:
                        box.operator("mbast_mbast_finalize.character_and_images", icon='FREEZE')
                    else:
                        box.operator("mbast_finalize.character", icon='FREEZE')
                        
                if gui_active_panel != "display_opt":
                    self.layout.operator('mbast_button.display_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast_button.display_off', icon=icon_collapse)
                    box = self.layout.box()                    
                    if the_humanoid.exists_displace_texture():                        
                        if the_humanoid.get_disp_visibility() == False:
                            box.operator("mbast_displacement.enable", icon='MOD_DISPLACE')
                        else:
                            box.operator("mbast_displacement.disable", icon='X')
                    if the_humanoid.get_subd_visibility() == False:
                        box.operator("mbast_subdivision.enable", icon='MOD_SUBSURF')  
                        box.label("Subd. preview is very CPU intensive", icon='INFO')                      
                    else:
                        box.operator("mbast_subdivision.disable", icon='X')
                        box.label("Disable subdivision to increase the performance", icon='ERROR')
                    if the_humanoid.get_smooth_visibility() == False:
                        box.operator("mbast_corrective.enable", icon='MOD_SMOOTH')                        
                    else:
                        box.operator("mbast_corrective.disable", icon='X')


            else:
                gui_status = "NEW_SESSION"

def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()





