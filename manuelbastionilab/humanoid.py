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

import bpy
from . import morphengine, skeletonengine, algorithms, proxyengine, materialengine
import os
import time
import json
import logging
import operator


lab_logger = logging.getLogger('manuelbastionilab_logger')


class HumanModifier:
    """
    A modifier is a group of related properties.
    """

    def __init__(self, name, obj_name):
        self.name = name
        self.obj_name = obj_name
        self.properties = []

    def get_object(self):
        """
        Get the blender object. It can't be stored because
        Blender's undo and redo change the memory locations
        """
        if self.obj_name in bpy.data.objects:
            return bpy.data.objects[self.obj_name]
        return None

    def add(self, prop):
        self.properties.append(prop)

    def __contains__(self, prop):
        for propx in self.properties:
            if propx == prop:
                return True
        return False

    def get_properties(self):
        """
        Return the properties contained in the
        modifier. Important: keep unsorted!
        """
        return self.properties

    def get_property(self, prop):
        """
        Return the property by name.
        """
        for propx in self.properties:
            if propx == prop:
                return propx
        return None

    def is_changed(self, char_data):
        """
        If a prop is changed, the whole modifier is considered changed
        """
        obj = self.get_object()
        for prop in self.properties:
            current_val = getattr(obj, prop, 0.5)
            if char_data[prop] != current_val:
                return True
        return False

    def sync_modifier_data_to_obj_prop(self, char_data):
        obj = self.get_object()
        for prop in self.properties:
            if hasattr(obj, prop):
                current_val = getattr(obj, prop, 0.5)
                char_data[prop] = current_val


    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return "Modifier <{0}> with {1} properties: {2}".format(
            self.name,
            len(self.properties),
            self.properties)

class HumanCategory:
    """
    A category is a group of related modifiers
    """

    def __init__(self, name):
        self.name = name
        self.modifiers = []

    def add(self, modifier):
        self.modifiers.append(modifier)

    def get_modifiers(self):
        return self.modifiers

    def get_modifier(self, name):
        for modifier in self.modifiers:
            if modifier.name == name:
                return modifier
        return None

    def get_all_properties(self):
        """
        Return all properties involved in the category,
        sorted and without double entries.
        """
        properties = []
        for modifier in self.modifiers:
            for prop in modifier.properties:
                if prop not in properties:
                    properties.append(prop)
        properties.sort()
        return properties

    def __contains__(self, mdf):
        for modifier in self.modifiers:
            if mdf.name == modifier.name:
                return True
        return False

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return "Category {0} with {1} modfiers".format(
            self.name,
            len(self.modifiers))


class Humanoid:
    """
    The humanoid is a container for categories of modifiers.
    """

    def __init__(self, lab_version):

        self.lab_vers = list(lab_version)
        self.has_data = False
        self.name = ""
        addon_directory = os.path.dirname(os.path.realpath(__file__))
        data_dir = os.path.join(addon_directory, "data")
        lab_logger.info("Looking for the database in the folder {0}...".format(algorithms.simple_path(data_dir)))
        if os.path.isdir(data_dir):
            self.data_path = data_dir
        else:
            lab_logger.critical("Database not found. Please check your Blender addons directory.")
        self.characters_definition = self.load_characters_definitions(os.path.join(self.data_path,"characters.json"))


    def load_characters_definitions(self, filepath):
        char_def = algorithms.load_json_data(filepath,"Characters definition")
        return char_def


    def build_character_item_list(self):
        item_list = []
        if self.characters_definition:
            for char_id in self.characters_definition["character_list"]:
                lbl = self.characters_definition[char_id]["label"]
                dsc = self.characters_definition[char_id]["description"]
                item_list.append((char_id,lbl,dsc))
        return item_list




    def exists_database(self, lib_path):
        result = False
        if os.path.isdir(lib_path):
            if len(os.listdir(lib_path)) > 0:
                for database_file in os.listdir(lib_path):
                    p_item, extension = os.path.splitext(database_file)
                    if "json" in extension:
                        result = True
                    else:
                        lab_logger.warning("Unknow file extension in {0}".format(algorithms.simple_path(lib_path)))

        else:
            lab_logger.warning("data path {0} not found".format(algorithms.simple_path(lib_path)))
        return result



    def init_database(self):

        is_obj = algorithms.looking_for_humanoid_obj()
        self.has_data = False
        if is_obj[0] == "FOUND":
            obj = algorithms.get_object_by_name(is_obj[1])

            self.name = obj.name
            lab_logger.info("Found the humanoid object: {0}".format(obj.name))

            self.character_ID = "0001"
            self.assign_ID()
            lab_logger.info("Init the database...")

            self.filepath = bpy.data.filepath
            if obj.data.shape_keys:
                lab_logger.error("The human object can't have shapekeys")

            self.no_categories = "BasisAsymTest"
            self.categories = {}
            self.bodydata_realtime_activated = True
            self.armat = skeletonengine.SkeletonEngine(
                obj,
                self.data_path)

            self.character_label = obj.name[:len(obj.name)-2]
            character_type = obj.name.split("_")[0]
            gender_type = obj.name.split("_")[1]

            self.shared_transformation_filename = self.character_label+"_transf.json"
            self.ethnic_path = os.path.join(self.data_path, self.name, "phenotypes")

            self.light_data_path = os.path.join(
                self.data_path,
                "lamps",
                "lamps.json")

            self.expression_path = os.path.join(
                self.data_path,
                "shared_expressions",
                character_type+"_"+gender_type)
            self.preset_path = os.path.join(
                self.data_path,
                "shared_presets",
                self.character_label)

            self.pose_path = os.path.join(
                self.data_path,
                "shared_poses",
                gender_type)

            self.restposes_path = os.path.join(
                self.data_path,
                "shared_poses",
                "rest")

            self.shared_transform_data_path = os.path.join(
                                self.data_path,
                                "shared_transformations",
                                self.shared_transformation_filename)

            self.corrective_modifier_name = "mbastlab_corrective_modifier"

            self.exists_expression_data = self.exists_database(self.expression_path)
            self.exists_poses_data = self.exists_database(self.pose_path)
            self.exists_preset_data = self.exists_database(self.preset_path)
            self.exists_phenotype_data = self.exists_database(self.ethnic_path)
            self.exists_transform_data = os.path.isfile(self.shared_transform_data_path)
            self.m_engine = morphengine.MorphingEngine(obj, self.data_path)
            detail_tex = self.characters_definition[self.name]["texture_details"]
            self.mat_engine = materialengine.MaterialEngine(obj, self.data_path, detail_tex)
            self.character_data = {}
            self.character_metaproperties = {"last_character_age":0.0,
                                            "character_age":0.0,
                                            "last_character_mass":0.0,
                                            "character_mass":0.0,
                                            "last_character_tone":0.0,
                                            "character_tone":0.0}
            self.character_material_properties = self.mat_engine.get_material_parameters()

            self.metadata_realtime_activated = True
            self.material_realtime_activated = True
            self.transformations_data = {}

            for morph in self.m_engine.morph_data.keys():
                self.init_character_data(morph)

            lab_logger.info("Loaded {0} categories from morph database".format(
                len(self.categories)))
            bpy.context.scene.objects.active = obj
            self.measures = self.m_engine.measures
            self.delta_measures = {}
            self.init_delta_measures()
            self.load_transformation_database()
            self.add_corrective_smooth_modifier()
            self.mat_engine.add_subdivision_modifier()
            self.mat_engine.add_displacement_modifier()
            self.has_data = True

        else:
            lab_logger.error("No humanoid for ManuelbastioniLAB found: {0}".format(is_obj[1]))


    def assign_ID(self):

        bpy.types.Object.character_ID = bpy.props.StringProperty(
            name="human_ID",
            maxlen = 25,
            default= "-")

        obj = self.get_object()
        if "character_ID" in obj.keys():
            lab_logger.info("Character_ID recovered from existing ID property")
            self.character_ID = obj['character_ID']
        else:
            lab_logger.info("Character_ID assigned from scratch")
            self.character_ID = str(time.time())

        obj.character_ID = self.character_ID


    def load_lights(self):
        self.mat_engine.load_lamps(self.light_data_path)


    def rename_obj(self):
        obj = self.get_object()
        obj.name = str(time.time())

    def rename_materials(self):
        self.mat_engine.rename_skin_shaders()


    def get_object_by_name(self,name):
        return algorithms.get_object_by_name(name)

    def get_object(self):
        if self.name in bpy.data.objects:
            return bpy.data.objects[self.name]
        return None

    def load_transformation_database(self):
        self.transformations_data = algorithms.load_json_data(self.shared_transform_data_path, "Transformations database")

    def get_categories(self):
        categories = self.categories.values()
        return sorted(categories)

    def get_category(self, name):
        if name in self.categories:
            return self.categories[name]

    def get_properties_in_category(self, name):
        return self.categories[name].get_all_properties()

    def init_character_data(self, morph_name):
        """
        Creates categories and properties from shapekey name
        """
        components = morph_name.split("_")
        if components[0][:4] not in self.no_categories:
            if len(components) == 3:
                category_name = components[0]
                if category_name not in self.categories:
                    category = HumanCategory(category_name)
                    self.categories[category_name] = category
                else:
                    category = self.categories[category_name]

                modifier_name = components[0]+"_"+components[1]
                modifier = category.get_modifier(modifier_name)
                if not modifier:
                    modifier = HumanModifier(modifier_name, self.name)
                    category.add(modifier)

                for element in components[1].split("-"):
                    prop = components[0]+"_" + element
                    if prop not in modifier:
                        modifier.add(prop)
                    self.character_data[prop] = 0.5
            else:
                lab_logger.warning("Wrong name for morph: {0}".format(morph_name))

    def reset_category(self, categ):
        time1 = time.time()
        obj = self.get_object()
        category = self.get_category(categ)
        for prop in category.get_all_properties():
            self.character_data[prop] = 0.5
        self.update_character(category_name=category.name, mode = "update_all")
        lab_logger.info("Category resetted in {0} secs".format(time.time()-time1))


    def exists_measure_database(self):
        return self.m_engine.measures_database_exist

    def exists_dermal_texture(self):
        return self.mat_engine.texture_dermal_exist

    def exists_displace_texture(self):
        return self.mat_engine.texture_displace_exist

    def exists_poses_database(self):
        return self.exists_poses_data

    def exists_expression_database(self):
        return self.exists_expression_data

    def exists_preset_database(self):
        return self.exists_preset_data

    def exists_phenotype_database(self):
        return self.exists_phenotype_data

    def exists_transform_database(self):
        return self.exists_transform_data




    def automodelling(self,use_measures_from_GUI=False, use_measures_from_dict=None, use_measures_from_current_obj=False, mix=False):

        if self.m_engine.measures_database_exist:
            time2 = time.time()
            obj = self.get_object()
            n_samples = 3

            if use_measures_from_GUI:
                convert_to_inch = getattr(obj, "use_inch",False)
                if convert_to_inch:
                    conversion_factor = 39.37001
                else:
                    conversion_factor = 100

                wished_measures = {}
                for measure_name in self.m_engine.measures.keys():
                    if measure_name != "body_height_Z":
                        wished_measures[measure_name] = getattr(obj, measure_name, 0.5)/conversion_factor


                total_height_Z = 0
                for measure_name in self.m_engine.body_height_Z_parts:
                    total_height_Z += wished_measures[measure_name]

                wished_measures["body_height_Z"] = total_height_Z

            if use_measures_from_current_obj:
                current_shape_verts = []
                for vert in obj.data.vertices:
                    current_shape_verts.append(vert.co.copy())
                wished_measures = self.m_engine.calculate_measures(vert_coords=current_shape_verts)

            if use_measures_from_dict:
                wished_measures = use_measures_from_dict

            self.m_engine.calculate_proportions(wished_measures)
            similar_characters_data  = self.m_engine.compare_data_proportions()

            best_character = similar_characters_data[0]
            filepath = best_character[1]
            self.load_character(filepath)

            for char_data in similar_characters_data[1:n_samples]:
                filepath = char_data[1]
                self.load_character(filepath, mix = True)


            self.measure_fitting(wished_measures, mix)
            self.update_character(mode = "update_directly_verts")

            lab_logger.info("Human fitting in {0} secs".format(time.time()-time2))

    def clean_verts_to_process(self):
        self.m_engine.verts_to_update.clear()

    def update_displacement(self):
        obj = self.get_object()
        age_factor = obj.character_age
        tone_factor = obj.character_tone
        mass_factor = obj.character_mass
        self.mat_engine.calculate_displacement_texture(age_factor,tone_factor,mass_factor)

    def remove_skin_displacement(self):
        self.mat_engine.remove_displacement_modifier()

    def remove_modifiers(self):
        obj = self.get_object()
        for modf in obj.modifiers:
            if "mbastlab" in modf.name:
                if "armature" not in modf.name:
                    obj.modifiers.remove(modf)

    def save_body_displacement_texture(self, filepath):
        self.mat_engine.save_texture(filepath,"body_displ")

    def save_body_dermal_texture(self, filepath):
        self.mat_engine.save_texture(filepath,"body_derm")

    def save_all_textures(self, filepath):
        targets = ["body_displ","body_derm"]
        for target in targets:
            dir_path = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            filename_root = os.path.splitext(filename)[0]
            filename_ext = os.path.splitext(filename)[1]
            new_filename = filename_root + target+ filename_ext
            new_filepath = os.path.join(dir_path,new_filename)
            self.mat_engine.save_texture(new_filepath,target)

    def save_backup_character(self, filepath):

        dir_path = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        filename_root = os.path.splitext(filename)[0]
        new_filename = filename_root + 'backup.json'
        new_filepath = os.path.join(dir_path,new_filename)
        lab_logger.info("Saving backup character {0}".format(algorithms.simple_path(new_filepath)))
        self.save_character(new_filepath, export_proportions=False, export_materials=True, export_metadata = True)


    def get_subd_visibility(self):
        return self.mat_engine.get_subdivision_visibility()

    def set_subd_visibility(self,value):
        self.mat_engine.set_subdivision_visibility(value)

    def set_smooth_visibility(self,value):
        #TODO: standard class to handle all the modifiers.
        obj = self.get_object()
        if self.corrective_modifier_name in obj.modifiers:
            obj.modifiers[self.corrective_modifier_name].show_viewport = value

    def get_smooth_visibility(self):
        obj = self.get_object()
        if self.corrective_modifier_name in obj.modifiers:
            return obj.modifiers[self.corrective_modifier_name].show_viewport

    def get_disp_visibility(self):
        return self.mat_engine.get_displacement_visibility()

    def set_disp_visibility(self,value):
        self.mat_engine.set_displacement_visibility(value)


    def sync_obj_props_to_character_materials(self):

        self.material_realtime_activated = False
        obj = self.get_object()
        for material_data_prop, value in self.character_material_properties.items():
            if hasattr(obj, material_data_prop):
                setattr(obj, material_data_prop, value)
            else:
                lab_logger.warning("material {0}  not found".format(material_data_prop))
        self.material_realtime_activated = True


    def update_materials(self, update_textures_nodes = True):
        obj = self.get_object()
        for prop in self.character_material_properties.keys():
            if hasattr(obj, prop):
                self.character_material_properties[prop] = getattr(obj, prop)
        self.mat_engine.update_shaders(self.character_material_properties, update_textures_nodes)

    def correct_expressions(self, correct_all=False):
        """
        Correct all the expression morphing that are different from 0
        """
        time1 = time.time()
        expressions_to_correct = []
        for prop in self.categories["Expressions"].get_all_properties():
            if not correct_all:
                if self.character_data[prop] != 0.5:
                    expressions_to_correct.append(prop)
            else:
                expressions_to_correct.append(prop)
        self.m_engine.correct_morphs(expressions_to_correct)

        #if finish_it:
            #self.m_engine.apply_finishing_morph()

        lab_logger.info("Expression corrected in {0} secs".format(time.time()-time1))


    def reset_character(self):
        time1 = time.time()
        obj = self.get_object()
        self.reset_metadata()
        for category in self.get_categories():
            for modifier in category.get_modifiers():
                for prop in modifier.get_properties():
                    self.character_data[prop] = 0.5
        self.update_character(mode = "update_all")


        lab_logger.info("Character reset in {0} secs".format(time.time()-time1))


    def reset_metadata(self):
        obj = self.get_object()
        for meta_data_prop in self.character_metaproperties.keys():
            self.character_metaproperties[meta_data_prop]=0.0


    def reset_mesh(self):
        self.m_engine.reset()

    def store_mesh_in_cache(self):
        self.m_engine.copy_in_cache()

    def restore_mesh_from_cache(self):
        self.m_engine.copy_from_cache()
        self.m_engine.update(update_all_verts=True)
        self.m_engine.clean_the_cache()


    def sync_obj_props_to_character_metadata(self):

        self.metadata_realtime_activated = False
        obj = self.get_object()
        for meta_data_prop, value in self.character_metaproperties.items():
            if hasattr(obj, meta_data_prop):
                setattr(obj, meta_data_prop, value)
            else:
                if "last" not in meta_data_prop:
                    lab_logger.warning("metadata {0}.{1} not found".format(obj.name,meta_data_prop))
        self.metadata_realtime_activated = True


    def delete_all_properties(self):
        time1 = time.time() #TODO: usare obj.keys per lavorare solo sui valory applicati
        lab_logger.info("Deleting custom properties")
        obj = self.get_object()
        props_to_delete = set(["manuellab_vers", "character_ID", "use_inch"])
        for category in self.get_categories():
            for modifier in category.get_modifiers():
                for prop in modifier.get_properties():
                    if hasattr(obj, prop):
                        props_to_delete.add(prop)
                for measure in self.m_engine.measures.keys():
                    if hasattr(obj, measure):
                        props_to_delete.add(measure)
                for metaproperty in self.character_metaproperties.keys():
                    if hasattr(obj, metaproperty):
                        props_to_delete.add(metaproperty)

        obj = self.get_object()
        for material_prop in self.character_material_properties.keys():
            if hasattr(obj, material_prop):
                props_to_delete.add(material_prop)

        for prop in props_to_delete:
            try:
                del obj[prop]
            except:
                lab_logger.info("Property {0} was not used by this character".format(prop))

        armat = self.armat.get_armature()
        if armat:
            if 'animation_source' in armat.keys():
                try:
                    del armat['animation_source']
                except:
                    lab_logger.info('Cannot delete the armature property for animation source')

        lab_logger.info("Properties deleted in {0} secs".format(time.time()-time1))




    def recover_prop_values_from_obj_attr(self):
        obj = self.get_object()
        char_data = {"structural":{}, "metaproperties":{}, "materialproperties":{}}

        for prop in self.character_data.keys():
            if prop in obj.keys():
                char_data["structural"][prop] = obj[prop]

        for prop in self.character_metaproperties.keys():
            if prop in obj.keys():
                char_data["metaproperties"][prop] = obj[prop]
                char_data["metaproperties"]["last_"+prop] = obj[prop]

        for prop in self.character_material_properties.keys():
            if prop in obj.keys():
                char_data["materialproperties"][prop] = obj[prop]
        self.load_character(char_data)



    def sync_obj_props_to_character_data(self):
        obj = self.get_object()
        self.bodydata_realtime_activated = False
        for prop,value in self.character_data.items():
            setattr(obj, prop, value)

    def sync_character_data_to_obj_props(self):
        obj = self.get_object()
        self.bodydata_realtime_activated = False
        for prop in obj.keys():
            if prop in self.character_data:
                self.character_data[prop] = getattr(obj,prop)


    def sync_internal_data_with_mesh(self):
        self.m_engine.init_final_form()


    def sync_gui_according_measures(self):

        obj = self.get_object()
        measures = self.m_engine.calculate_measures()
        convert_to_inch = getattr(obj, "use_inch", False)
        if convert_to_inch:
            conversion_factor = 39.37001
        else:
            conversion_factor = 100
        for measure_name,measure_val in measures.items():
            if hasattr(obj, measure_name):
                setattr(obj, measure_name, measure_val*conversion_factor)

    def update_character(self, category_name = None, mode = "update_all"):
        time1 = time.time()
        obj = self.get_object()
        self.clean_verts_to_process()

        if mode == "update_all":
            update_directly_verts = False
            update_geometry_all = True
            update_geometry_selective = False
            update_armature = True
            update_normals = True
            update_proxy = False
            update_measures = True
            sync_morphdata = False
            sync_GUI = True
            sync_GUI_metadata = True
            sync_GUI_materials = True

        if mode == "update_metadata":
            update_directly_verts = False
            update_geometry_all = True
            update_geometry_selective = False
            update_armature = True
            update_normals = True
            update_proxy = False
            update_measures = True
            sync_morphdata = False
            sync_GUI = True
            sync_GUI_metadata = False
            sync_GUI_materials = False

        if mode == "update_directly_verts":
            update_directly_verts = True
            update_geometry_all = False
            update_geometry_selective = False
            update_armature = True
            update_normals = True
            update_proxy = False
            update_measures = True
            sync_morphdata = False
            sync_GUI = True
            sync_GUI_metadata = False
            sync_GUI_materials = False

        if mode == "update_only_morphdata":
            update_directly_verts = False
            update_geometry_all = False
            update_geometry_selective = False
            update_armature = False
            update_normals = False
            update_proxy = False
            update_measures = False
            sync_morphdata = False
            sync_GUI = False
            sync_GUI_metadata = False
            sync_GUI_materials = False

        if mode == "update_realtime":
            update_directly_verts = False
            update_geometry_all = False
            update_geometry_selective = True
            update_armature = True
            update_normals = False
            update_proxy = False
            update_measures = False
            sync_morphdata = True
            sync_GUI = False
            sync_GUI_metadata = False
            sync_GUI_materials = False


        if update_directly_verts:
            self.m_engine.update(update_all_verts=True)
        else:
            if category_name:
                category = self.categories[category_name]
                modified_modifiers = []
                for modifier in category.get_modifiers():
                    if modifier.is_changed(self.character_data):
                        modified_modifiers.append(modifier)
                for modifier in modified_modifiers:
                    if sync_morphdata:
                        modifier.sync_modifier_data_to_obj_prop(self.character_data)
                    self.combine_morphings(modifier)
            else:
                for category in self.get_categories():
                    for modifier in category.get_modifiers():
                        self.combine_morphings(modifier, add_vertices_to_update=True)

        if update_geometry_all:
            self.m_engine.update(update_all_verts=True)
        if update_geometry_selective:
            self.m_engine.update(update_all_verts=False)
        if sync_GUI:
            self.sync_obj_props_to_character_data()
        if sync_GUI_materials:
            self.sync_obj_props_to_character_materials()
            self.update_materials()

        if sync_GUI_metadata:
            self.sync_obj_props_to_character_metadata()
        if update_measures:
            self.sync_gui_according_measures()
        if update_armature:
            self.armat.fit_joints()
        if update_normals:
            obj.data.calc_normals()
        if update_proxy:
            self.fit_proxy()

        animation_source = self.armat.get_source_armature()
        if animation_source:
            animation_source.hide = True

        #lab_logger.debug("Character updated in {0} secs".format(time.time()-time1))

    def generate_character(self,random_value,prv_face,prv_body,prv_mass,prv_tone,prv_height,prv_phenotype,set_tone_and_mass,body_mass,body_tone):
        lab_logger.info("Generating character...")

        all_props = [x for x in self.character_data.keys()]
        props_to_process = all_props.copy()

        face_keys = ["Eye", "Eyelid", "Nose", "Mouth", "Ear", "Head", "Forehead", "Cheek", "Jaw"]
        body_keys = ["Armpit", "Elbows", "Chest", "Body", "Arms", "Feet", "Wrists", "Waist", "Torso","Stomach","Shoulders","Pelvis","Neck","Legs","Hands"]
        height_keys = ["Length", "Body_Size"]
        mass_keys = ["Mass"]
        tone_keys = ["Tone"]
        expression_keys = ["Expressions"]

        for prop in all_props:
            remove_it = False
            for k in expression_keys:
                if k in prop:
                    remove_it = True
                    break
            if prv_face:
                for k in face_keys:
                    if k in prop:
                        remove_it = True
                        break
            if prv_body:
                for k in body_keys:
                    if k in prop:
                        remove_it = True
                        break
            if prv_mass:
                for k in mass_keys:
                    if k in prop:
                        remove_it = True
                        break
            if prv_tone:
                for k in tone_keys:
                    if k in prop:
                        remove_it = True
                        break
            if prv_height:
                for k in height_keys:
                    if k in prop:
                        remove_it = True
                        break
            if remove_it:
                if prop in props_to_process:
                    props_to_process.remove(prop)

        for prop in props_to_process:
            new_val = algorithms.generate_parameter(
                self.character_data[prop],
                random_value,
                prv_phenotype)
            if set_tone_and_mass:
                if "Mass" in prop:
                    new_val = body_mass
                if "Tone" in prop:
                    new_val = body_tone
            self.character_data[prop] = new_val
        self.update_character(mode = "update_all")




    def calculate_transformation(self, tr_type):


        obj = self.get_object()
        #TODO automatizzare con getattr direttamente dal dizionario

        if tr_type == "AGE":
            current_tr_factor = obj.character_age
            previous_tr_factor = self.character_metaproperties["last_character_age"]
            transformation_id = "age_data"
        if tr_type == "FAT":
            current_tr_factor = obj.character_mass
            previous_tr_factor = self.character_metaproperties["last_character_mass"]
            transformation_id = "fat_data"
        if tr_type == "MUSCLE":
            current_tr_factor = obj.character_tone
            previous_tr_factor = self.character_metaproperties["last_character_tone"]
            transformation_id = "muscle_data"

        if current_tr_factor >= 0:
            transformation_2 = current_tr_factor
            transformation_1 = 0
        else:
            transformation_2 = 0
            transformation_1 = -current_tr_factor

        if previous_tr_factor >= 0:
            last_transformation_2 = previous_tr_factor
            last_transformation_1 = 0
        else:
            last_transformation_2 = 0
            last_transformation_1 = -previous_tr_factor


        if transformation_id in self.transformations_data:
            tr_data = self.transformations_data[transformation_id]

            for prop in self.character_data:
                for tr_parameter in tr_data:
                    if tr_parameter[0] in prop:
                        linear_factor = tr_parameter[1]*transformation_1 + tr_parameter[2]*transformation_2 - tr_parameter[1]*last_transformation_1 - tr_parameter[2]*last_transformation_2

                        self.character_data[prop] = self.character_data[prop] + linear_factor

            if tr_type == "AGE":
                self.character_metaproperties['character_age'] = current_tr_factor
                self.character_metaproperties['last_character_age'] = current_tr_factor
            if tr_type == "FAT":
                self.character_metaproperties['character_mass'] = current_tr_factor
                self.character_metaproperties['last_character_mass'] = current_tr_factor
            if tr_type == "MUSCLE":
                self.character_metaproperties['character_tone'] = current_tr_factor
                self.character_metaproperties['last_character_tone'] = current_tr_factor

            self.update_character(mode = "update_metadata")

        else:
            lab_logger.warning("{0} data not present".format(transformation_id))


    def init_delta_measures(self):

        obj = self.get_object()
        time1 = time.time()
        for relation in self.m_engine.measures_relat_data:
            m_name = relation[0]
            modifier_name = relation[1]
            for category in self.get_categories():
                for modifier in category.get_modifiers():
                    if modifier.name == modifier_name:
                        for prop in modifier.get_properties():

                            self.character_data[prop] = 0.0
                            self.combine_morphings(modifier)
                            measure1 = self.m_engine.calculate_measures(measure_name=m_name)

                            self.character_data[prop] = 1.0
                            self.combine_morphings(modifier)
                            measure3 = self.m_engine.calculate_measures(measure_name=m_name)

                            #Last measure also restores the value to 0.5
                            self.character_data[prop] = 0.5
                            self.combine_morphings(modifier)
                            measure2 = self.m_engine.calculate_measures(measure_name=m_name)

                            delta_name = modifier_name+prop

                            delta1 = measure1-measure2
                            delta3 = measure3-measure2

                            self.delta_measures[delta_name] = [delta1,delta3]


        lab_logger.info("Delta init in {0} secs".format(time.time()-time1))


    def search_best_value(self,m_name,wished_measure,human_modifier,prop):

        self.character_data[prop] = 0.5
        self.combine_morphings(human_modifier)
        measure2 = self.m_engine.calculate_measures(measure_name=m_name)
        delta_name = human_modifier.name+prop

        delta1 = self.delta_measures[delta_name][0]
        delta3 = self.delta_measures[delta_name][1]

        measure1 = measure2 + delta1
        measure3 = measure2 + delta3

        if wished_measure < measure2:
            xa = 0
            xb = 0.5
            ya = measure1
            yb = measure2
        else:
            xa = 0.5
            xb = 1
            ya = measure2
            yb = measure3

        if ya-yb != 0:
            value = algorithms.linear_interpolation_y(xa,xb,ya,yb,wished_measure)

            if value < 0:
                value = 0
            if value > 1:
                value = 1
        else:
            value = 0.5
        return value


    def measure_fitting(self, wished_measures,mix = False):

        if self.m_engine.measures_database_exist:
            obj = self.get_object()
            time1 = time.time()
            for relation in self.m_engine.measures_relat_data:
                measure_name = relation[0]
                modifier_name = relation[1]
                if measure_name in wished_measures:
                    wish_measure = wished_measures[measure_name]

                    for category in self.get_categories():
                        for modifier in category.get_modifiers():
                            if modifier.name == modifier_name:
                                for prop in modifier.get_properties():

                                    if mix:
                                        best_val = self.search_best_value(measure_name,wish_measure,modifier,prop)
                                        value = (self.character_data[prop]+best_val)/2
                                        self.character_data[prop] = value
                                    else:
                                        self.character_data[prop] = self.search_best_value(measure_name,wish_measure,modifier,prop)
                                self.combine_morphings(modifier)

            lab_logger.info("Measures fitting in {0} secs".format(time.time()-time1))


    def save_character(self, filepath, export_proportions=True, export_materials=True, export_metadata = True):
        lab_logger.info("Exporting character to {0}".format(algorithms.simple_path(filepath)))
        obj = self.get_object()
        char_data = {"manuellab_vers": self.lab_vers, "structural":dict(), "proportions":dict(), "metaproperties":dict(), "materialproperties":dict()}

        if obj:

            for prop in self.character_data.keys():
                if self.character_data[prop] != 0.5:
                    char_data["structural"][prop] = round(self.character_data[prop], 4)

            if export_metadata:
                for meta_data_prop, value in self.character_metaproperties.items():
                    char_data["metaproperties"][meta_data_prop] = round(value, 4) #getattr(obj, meta_data_prop, 0.0)

            if export_materials:
                for prop in self.character_material_properties.keys():
                    char_data["materialproperties"][prop] = round(self.character_material_properties[prop],4)

            if export_proportions:
                self.m_engine.calculate_proportions(self.m_engine.calculate_measures())
                for proportion, value in self.m_engine.proportions.items():
                    char_data["proportions"][proportion] = round(value, 4)

            output_file = open(filepath, 'w')
            json.dump(char_data, output_file)
            output_file.close()

    def export_measures(self, filepath):
        lab_logger.info("Exporting measures to {0}".format(algorithms.simple_path(filepath)))
        obj = self.get_object()
        char_data = {"manuellab_vers": self.lab_vers, "measures":dict()}
        if obj:
            measures = self.m_engine.calculate_measures()
            for measure, measure_val in measures.items():
                measures[measure] = round(measure_val, 3)
            char_data["measures"]=measures
            output_file = open(filepath, 'w')
            json.dump(char_data, output_file)
            output_file.close()


    def load_character(self, data_source, reset_string = "nothing", reset_unassigned=True, mix=False, update_mode = "update_all"):

        obj = self.get_object()
        log_msg_type = "character data"

        if type(data_source) == str:  #TODO: better check of types
            log_msg_type = algorithms.simple_path(data_source)
            charac_data = algorithms.load_json_data(data_source,"Character data")
        else:
            charac_data = data_source

        lab_logger.info("Loading character from {0}".format(log_msg_type))

        if "manuellab_vers" in charac_data:
            if not algorithms.check_version(charac_data["manuellab_vers"]):
                lab_logger.warning("{0} created with vers. {1}. Current vers is {2}".format(log_msg_type,charac_data["manuellab_vers"],self.lab_vers))
        else:
            lab_logger.warning("No lab version specified in {0}".format(log_msg_type))

        if "structural" in charac_data:
            char_data = charac_data["structural"]
        else:
            lab_logger.warning("No structural data in  {0}".format(log_msg_type))
            char_data = {}

        if "materialproperties" in charac_data:
            material_data = charac_data["materialproperties"]
        else:
            lab_logger.info("No material data in  {0}".format(log_msg_type))
            material_data = {}

        if "metaproperties" in charac_data:
            meta_data = charac_data["metaproperties"]
        else:
            lab_logger.warning("No metaproperties data in  {0}".format(log_msg_type))
            meta_data = {}

        if char_data != None:
            for name in self.character_data.keys():
                if reset_string in name:
                    self.character_data[name] = 0.5
                if name in char_data:
                    if mix:
                        self.character_data[name] = (self.character_data[name]+char_data[name])/2
                    else:
                        self.character_data[name] = char_data[name]
                else:
                    if reset_unassigned:
                        if mix:
                            self.character_data[name] = (self.character_data[name]+0.5)/2
                        else:
                            self.character_data[name] = 0.5


        for name in self.character_metaproperties.keys():
            if name in meta_data:
                self.character_metaproperties[name] = meta_data[name]


        for name in self.character_material_properties.keys():
            if name in material_data:
                self.character_material_properties[name] = material_data[name]

        self.update_character(mode = update_mode)

    def load_measures(self, filepath):
        char_data = algorithms.load_json_data(filepath, "Measures data")
        if not ("measures" in char_data):
            lab_logger.error("This json has not the measures info, {0}".format(algorithms.simple_path(filepath)))
            return None
        c_data = char_data["measures"]
        return c_data

    def import_measures(self, filepath):
        char_data = self.load_measures(filepath)
        if char_data:
            self.automodelling(use_measures_from_dict=char_data)

    def load_pose(self, filepath):
        lab_logger.info("Loading pose from {0}".format(algorithms.simple_path(filepath)))
        self.armat.load_pose(filepath)
        obj = self.get_object()
        algorithms.select_and_change_mode(obj,"OBJECT")
        self.update_character()


    def load_body_dermal_texture(self, filepath):
        self.mat_engine.load_texture(filepath, "body_derm")

    def load_body_complexion_texture(self, filepath):
        self.mat_engine.load_texture(filepath, "body_complexion")

    def load_body_details_texture(self, filepath):
        self.mat_engine.load_texture(filepath, "body_details")

    def load_body_displacement_texture(self, filepath):
        self.mat_engine.load_texture(filepath, "body_displ")


    def save_pose(self, filepath):
        lab_logger.info("Saving pose to {0}".format(algorithms.simple_path(filepath)))
        self.armat.save_pose(filepath)

    def reset_pose(self):
        self.armat.reset_pose()
        bpy.ops.screen.animation_cancel(restore_frame=True)
        self.update_character()


    def validate_proxy_for_calibration(self):
        obj = self.get_object()

        for category in self.get_categories():
            for modifier in category.get_modifiers():
                for prop in modifier.get_properties():
                    if hasattr(obj, prop):
                        if self.character_data[prop] != 0.5:
                            return "Please reset the character before calibration"

        if self.armat.is_in_rest_pose():
            return "OK"
        else:
            return "Please reset the pose of character before calibration of proxy"


    def validate_proxy_for_selection(self):
        obj = self.get_object()
        proxy_obj = bpy.context.active_object
        return proxyengine.validate_proxy_select(obj, proxy_obj, self.character_label)


    def calibrate_proxy(self):
        obj = self.get_object()
        proxy_obj = bpy.context.active_object
        proxy_ID = self.character_label
        setattr(proxy_obj, 'proxy_ID', proxy_ID)
        proxyengine.prepare_proxy_for_calibration(obj)
        proxyengine.calibrate_proxy_object(proxy_obj)

    def reset_proxy(self):
        obj = self.get_object()
        proxy_obj = bpy.context.active_object
        setattr(proxy_obj, 'proxy_ID', "")
        proxyengine.reset_proxy_object(proxy_obj)



    def fit_proxy(self, fix_intersection = False, corr_factor = 1):

        obj = self.get_object()
        obj_armature = self.armat.get_armature()

        for blender_obj in bpy.data.objects:
            proxy_status = proxyengine.validate_proxy_select(obj, blender_obj, self.character_label)
            if proxy_status == 'IS_PROXY':

                proxy_obj = blender_obj
                proxy_obj.matrix_world = obj_armature.matrix_world
                lab_logger.info("Found proxy {0}".format(proxy_obj.name))

                proxyengine.fit_proxy_object(obj, proxy_obj, self.m_engine.base_form)
                proxyengine.calculate_finishing_morph(proxy_obj)

                if fix_intersection:
                    proxyengine.proxy_collision(obj, proxy_obj, self.m_engine.base_form, correction_factor = corr_factor)

    def combine_morphings(self, modifier, refresh_only=False, add_vertices_to_update=True):
        """
        Mix shapekeys using smart combo algorithm.
        """

        values = []
        for prop in modifier.properties:
            val = self.character_data[prop]
            if val > 1.0:
                val = 1.0
            if val < 0:
                val = 0
            val1 = algorithms.function_modifier_a(val)
            val2 = algorithms.function_modifier_b(val)
            values.append([val1, val2])
        names, weights = algorithms.smart_combo(modifier.name, values)
        for i in range(len(names)):
            if refresh_only:
                self.m_engine.morph_values[names[i]] = weights[i]
            else:
                self.m_engine.calculate_morph(
                    names[i],
                    weights[i],
                    add_vertices_to_update)

    def exists_source_armature(self):
        if self.armat.get_source_armature() != None:
            return True
        else:
            return False

    def add_id_to_name(self,obj):
        if "mbastlab" not in obj.name:
            obj.name = "mbastlab_"+obj.name

    def load_bvh(self,bvh_path):
        bpy.context.scene.frame_end = 0
        bpy.ops.import_anim.bvh(
            filepath = bvh_path,
            use_fps_scale = True,
            update_scene_duration = True
            )

    def load_obj_prototype(self,obj_name):

        obj_path = os.path.join(self.data_path,"shared_objs",obj_name+".obj")

        bpy.ops.import_scene.obj(
            use_split_objects = False,
            use_split_groups = False,
            split_mode = "OFF",
            axis_forward = "Y",
            axis_up = "Z",
            filepath=obj_path
            )
    def remove_source_armature(self, source_armature = None):
        self.armat.remove_source_armature(source_armature)

    def retarget(self, source_armature, bake_animation = False):

        target_armature = self.armat.get_armature()

        lab_logger.info("retarget with {0}".format(source_armature.name))
        if source_armature:
            self.armat.init_skeleton_map(source_armature)
            self.armat.clear_action()
            self.armat.align_skeleton(target_armature,source_armature)
            self.armat.scale_armat(target_armature,source_armature)
            self.armat.reset_bones_rotations(target_armature)
            self.armat.use_animation_pelvis(target_armature,source_armature)
            self.armat.align_bones_z_axis()
            self.armat.remove_copy_rotations()
            self.armat.add_bone_modifiers(target_armature,source_armature)
            source_armature.hide = True

            if bake_animation:
                self.armat.bake_animation(target_armature,source_armature)

            obj = self.get_object()
            algorithms.select_and_change_mode(obj,"OBJECT")

    def change_rest_pose(self):
        rest_pose_path = os.path.join(self.restposes_path,bpy.context.scene.restpose+".json")
        source_armature = self.armat.get_source_armature()

        if not source_armature:
            posed_armat = self.armat.get_armature()
            algorithms.select_and_change_mode(posed_armat,"OBJECT")
            existing_obj_names = algorithms.collect_existing_objects()
            bpy.ops.object.duplicate_move()
            source_armature = algorithms.get_newest_object(existing_obj_names)

        self.armat.load_bones_position()
        self.load_pose(rest_pose_path)
        self.armat.apply_armature_modifier()
        self.armat.apply_pose_as_rest_pose()
        self.armat.add_armature_modifier()
        self.armat.move_up_armature_modifier()        

        self.retarget(source_armature, bake_animation = True)
        self.remove_source_armature(source_armature)




    def reinit_retarget(self):
        source_armature = self.armat.get_source_armature()
        self.armat.remove_animation()
        self.reset_pose()

        if self.exists_source_armature():
            self.retarget(source_armature, False)




    def retarget_bvh(self,bvh_path):

        self.armat.remove_source_armature()
        source_armature = None
        existing_obj_names = algorithms.collect_existing_objects()
        self.load_bvh(bvh_path)
        
        source_armature = algorithms.get_newest_object(existing_obj_names)
        if source_armature:
            self.add_id_to_name(source_armature)
            self.armat.set_source_armature(source_armature)
            self.retarget(source_armature, False)

        if not bpy.context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()


    def add_corrective_smooth_modifier(self):
        obj = self.get_object()
        if self.corrective_modifier_name not in obj.modifiers:
            smooth_mod = obj.modifiers.new(self.corrective_modifier_name,'CORRECTIVE_SMOOTH')
            smooth_mod.show_viewport = True















