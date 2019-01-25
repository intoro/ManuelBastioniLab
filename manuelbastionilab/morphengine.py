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

import os
import bpy
import mathutils
from . import algorithms, proxyengine
import time, json
import logging
import operator

lab_logger = logging.getLogger('manuelbastionilab_logger')

class MorphingEngine:

    def __init__(self, obj, data_path):
        time1 = time.time()
        if obj:
            self.base_form = []
            self.final_form = []
            self.cache_form = []
            self.obj_name = obj.name

            character_type = obj.name.split("_")[0]
            gender_type = obj.name.split("_")[1]

            self.shared_morphs_filename = character_type+"_"+gender_type+"_morphs.json"
            self.shared_morphs_filename_extra = character_type+"_"+gender_type+"_morphs_extra.json"
            self.shared_bodies_path = obj.name[:len(obj.name)-2]+"_bodies"
            self.shared_measures_filename = character_type+"_"+gender_type+"_measures.json"
            self.shared_bbox_filename = character_type+"_"+gender_type+"_bbox.json"
            self.measures_database_exist = False            

            self.measures_data_path = os.path.join(
                data_path,
                "shared_measures",
                self.shared_measures_filename)
            self.bodies_data_path = os.path.join(
                data_path,
                "shared_bodies",
                self.shared_bodies_path)
            self.shared_morph_data_path = os.path.join(
                data_path,
                "shared_morphs",
                self.shared_morphs_filename)
            self.shared_morph_extra_data_path = os.path.join(
                data_path,
                "shared_morphs",
                self.shared_morphs_filename_extra)
            self.morph_data_path = os.path.join(
                data_path,
                self.obj_name,
                "morphs.json")
            self.extra_morph_data_path = os.path.join(
                data_path,
                self.obj_name,
                "extra_morphs.json")
            self.morph_forma_path = os.path.join(
                data_path,
                self.obj_name,
                "forma.json")
            self.bounding_box_path = os.path.join(
                data_path,
                "shared_bboxes",
                self.shared_bbox_filename)
            self.expressions_path = os.path.join(
                data_path,
                self.obj_name,
                "expressions.json")
            self.vertices_path = os.path.join(
                data_path,
                self.obj_name,
                "vertices.json")


            if os.path.isdir(self.bodies_data_path):
                if os.path.isfile(self.measures_data_path):
                    self.measures_database_exist = True

            self.verts_to_update = set()
            self.morph_data = {}
            self.morph_data_cache = {}
            self.forma_data = None
            self.bbox_data = {}
            self.morph_values = {}
            self.morph_modified_verts = {}
            self.boundary_verts = None
            self.measures_data = {}
            self.measures_relat_data = []
            self.measures_score_weights = {}
            self.body_height_Z_parts = {}

            self.proportions = {}

            self.init_final_form()
            self.load_vertices_database(self.vertices_path)

            self.load_morphs_database(self.shared_morph_data_path)
            self.load_morphs_database(self.morph_data_path)
            self.load_morphs_database(self.extra_morph_data_path) #Call this after the loading of shared morph is important for overwrite data.
            self.load_morphs_database(self.shared_morph_extra_data_path)
            self.load_morphs_database(self.expressions_path)
            self.load_bboxes_database(self.bounding_box_path)
            self.load_measures_database(self.measures_data_path)

            self.measures = self.calculate_measures()

            #Checks:
            if len(self.final_form) != len(self.base_form):
                lab_logger.critical("Vertices database not coherent with the vertices in the obj {0}".format(obj.name))
            #TODO: add more checks

        lab_logger.info("Databases loaded in {0} secs".format(time.time()-time1))

    def init_final_form(self):
        obj = self.get_object()
        self.final_form = []
        for vert in obj.data.vertices:
                self.final_form.append(vert.co.copy())

    def __repr__(self):
        return "MorphEngine {0} with {1} morphings".format(self.obj_name, len(self.morph_data))

    def get_object(self):
        if self.obj_name in bpy.data.objects:
            return bpy.data.objects[self.obj_name]
        return None

    def error_msg(self, path):
        lab_logger.warning("Database file not found: {0}".format(algorithms.simple_path(path)))

    def reset(self, update=True):
        for i in range(len(self.base_form)):
            self.final_form[i] = self.base_form[i]
        for morph_name in self.morph_values.keys():
            self.morph_values[morph_name] = 0.0
        if update:
            self.update(update_all_verts=True)

    def load_measures_database(self, measures_path):        
        m_database = algorithms.load_json_data(measures_path,"Measures data")
        if m_database:
            self.measures_data = m_database["measures"]
            self.measures_relat_data = m_database["relations"]
            self.measures_score_weights = m_database["score_weights"]
            self.body_height_Z_parts = m_database["body_height_Z_parts"]

    def load_bboxes_database(self, bounding_box_path):            
        self.bbox_data = algorithms.load_json_data(bounding_box_path,"Bounding box data")
            

    def load_vertices_database(self, vertices_path):
        verts = algorithms.load_json_data(vertices_path,"Vertices data")
        if verts:
            for vert_co in verts:
                self.base_form.append(mathutils.Vector(vert_co))


    def load_morphs_database(self, morph_data_path):
        time1 = time.time()
        m_data = algorithms.load_json_data(morph_data_path,"Morph data")
        if m_data:
            for morph_name, deltas in m_data.items():
                morph_deltas = []
                modified_verts = set()
                for d_data in deltas:
                    t_delta = mathutils.Vector(d_data[1:])
                    morph_deltas.append([d_data[0], t_delta])
                    modified_verts.add(d_data[0])
                if morph_name in self.morph_data:
                    lab_logger.warning("Morph {0} duplicated while loading morphs from file".format(morph_name))

                self.morph_data[morph_name] = morph_deltas
                self.morph_values[morph_name] = 0.0
                self.morph_modified_verts[morph_name] = modified_verts
            lab_logger.info("Morph database {0} loaded in {1} secs".format(algorithms.simple_path(morph_data_path),time.time()-time1))
            lab_logger.info("Now local morph data contains {0} elements".format(len(self.morph_data)))


    #def apply_finishing_morph(self):
        #"""
        #Modify the Blender object in order to finish the surface.
        #"""
        #time1 = time.time()
        #obj = self.get_object()
        #if not self.boundary_verts:
            #self.boundary_verts = proxyengine.get_boundary_verts(obj)
        #if not self.forma_data:
            #self.forma_data = proxyengine.load_forma_database(self.morph_forma_path)
        #proxyengine.calculate_finishing_morph(obj, self.boundary_verts, self.forma_data, threshold=0.25)
        #lab_logger.info("Finishing applied in {0} secs".format(time.time()-time1))

    def calculate_measures(self,measure_name = None,vert_coords=None):

        if not vert_coords:
            vert_coords = self.final_form
        measures = {}
        time1 = time.time()
        if measure_name:
            if measure_name in self.measures_data:
                indices =  self.measures_data[measure_name]
                axis = measure_name[-1]
                return algorithms.length_of_strip(vert_coords, indices, axis)
        else:
            for measure_name in self.measures_data.keys():
                measures[measure_name] = self.calculate_measures(measure_name, vert_coords)
            lab_logger.debug("Measures calculated in {0} secs".format(time.time()-time1))
            return measures


    def calculate_proportions(self, measures):

        if measures == None:
            measures = self.measures
        if "body_height_Z" in measures:
            for measure, value in measures.items():
                proportion = value/measures["body_height_Z"]
                if measure in self.measures:
                    self.proportions[measure] = proportion
                else:
                    lab_logger.warning("The measure {0} not present in the proportion database".format(measure))
        else:
            lab_logger.error("The base measure not present in the analyzed database")

    def compare_file_proportions(self,filepath):
        char_data = algorithms.load_json_data(filepath,"Proportions data")
        if "proportions" in char_data:
            return (self.calculate_matching_score(char_data["proportions"]),filepath)
        else:
            lab_logger.info("File {0} does not contain proportions".format(algorithms.simple_path(filepath)))


    def compare_data_proportions(self):
        scores = []
        time1 = time.time()
        if os.path.isdir(self.bodies_data_path):
            for database_file in os.listdir(self.bodies_data_path):
                body_data, extension = os.path.splitext(database_file)
                if "json" in extension:
                    scores.append(self.compare_file_proportions(os.path.join(self.bodies_data_path,database_file)))
            scores.sort(key=operator.itemgetter(0), reverse=True)
            lab_logger.info("Measures compared with database in {0} seconds".format(time.time()-time1))
        else:
            lab_logger.warning("Bodies database not found")
        
        return scores

    def calculate_matching_score(self, proportions):
        data_score = 0
        soglia = 0.025
        for p,v in proportions.items():

            if p in self.proportions:
                if p != "body_height_Z":
                    proportion_score =1
                    difference_of_proportion = abs(self.proportions[p]-v)
                    if difference_of_proportion > soglia:
                        proportion_score = 0
                    data_score += proportion_score*self.measures_score_weights[p]
            else:
                lab_logger.warning("Measure {0} not present in inner proportions database".format(p))
        return data_score


    def correct_morphs(self, names):
        morph_values_cache = {}
        for morph_name in self.morph_data.keys():
            for name in names:
                if name in morph_name:
                    morph_values_cache[morph_name] = self.morph_values[morph_name]#Store the values before the correction
                    self.calculate_morph(morph_name, 0.0) #Reset the morphs to correct

        for morph_name, morph_deltas in self.morph_data.items():
            for name in names:
                if name in morph_name: #If the morph is in the list of morph to correct
                    if morph_name in self.morph_data_cache:
                        morph_deltas_to_recalculate = self.morph_data_cache[morph_name]
                    else:
                        self.morph_data_cache[morph_name] = morph_deltas
                        morph_deltas_to_recalculate = self.morph_data_cache[morph_name]
                    
                    self.morph_data[morph_name] = algorithms.correct_morph(
                        self.base_form,
                        self.final_form,
                        morph_deltas_to_recalculate,
                        self.bbox_data)
        for morph_name in self.morph_data.keys():
            for name in names:
                if name in morph_name:
                    self.calculate_morph(
                        morph_name,
                        morph_values_cache[morph_name])

        self.update()

    def convert_to_blshapekey(self, shape_key_name):
        obj = self.get_object()
        sk_new = obj.shape_key_add(name=shape_key_name, from_mix=False)
        sk_new.slider_min = 0
        sk_new.slider_max = 1.0
        sk_new.value = 0.0
        obj.use_shape_key_edit_mode = True

        for i in range(len(self.final_form)):
            sk_new.data[i].co = obj.data.vertices[i].co

    def convert_all_to_blshapekeys(self):

        #TODO: re-enable the finishing (finish = True) after some improvements

        #Reset all values (for expressions only) and create the basis key
        for morph_name in self.morph_data.keys():
            if "Expression" in morph_name:
                self.calculate_morph(morph_name, 0.0)
                self.update()
        self.convert_to_blshapekey("basis")

        #Store the character in neutral expression
        obj = self.get_object()
        stored_vertices = []
        for vert in obj.data.vertices:
            stored_vertices.append(mathutils.Vector(vert.co))

        lab_logger.info("Storing neutral character...OK")
        counter = 0
        for morph_name in sorted(self.morph_data.keys()):
            if "Expression" in morph_name:
                counter += 1
                self.calculate_morph(morph_name, 1.0)
                lab_logger.info("Converting {} to shapekey".format(morph_name))
                self.update()
                self.convert_to_blshapekey(morph_name)

                #Restore the neutral expression
                for i in range(len(self.final_form)):
                    self.final_form[i] = stored_vertices[i]
                self.update(update_all_verts=True)
        lab_logger.info("Successfully converted {0} morphs in shapekeys".format(counter))



    def update(self, update_all_verts=False):
        obj = self.get_object()
        vertices = obj.data.vertices
        if update_all_verts == True:
            for i in range(len(self.final_form)):
                vertices[i].co = self.final_form[i]
        else:
            for i in self.verts_to_update:
                vertices[i].co = self.final_form[i]

    def copy_in_cache(self):
        obj = self.get_object()
        self.clean_the_cache()
        vertices = obj.data.vertices
        for i in range(len(self.final_form)):
            self.cache_form.append(vertices[i].co.copy())
        lab_logger.info("Mesh cached")

    def copy_from_cache(self):
        if len(self.final_form) == len(self.cache_form):
            for i in range(len(self.final_form)):
                self.final_form[i] = self.cache_form[i]
            lab_logger.info("Mesh copied from cache")
        else:
            lab_logger.warning("Cached mesh not found")

    def clean_the_cache(self):
        self.cache_form = []


    def calculate_morph(self, morph_name, val, add_vertices_to_update=True):

        if morph_name in self.morph_data:
            real_val = val - self.morph_values[morph_name]
            if real_val != 0.0:
                morph = self.morph_data[morph_name]
                for d_data in morph:
                    i = d_data[0]
                    delta = d_data[1]
                    self.final_form[i] = self.final_form[i] + delta*real_val
                if add_vertices_to_update:
                    self.verts_to_update = self.verts_to_update.union(self.morph_modified_verts[morph_name])
                self.morph_values[morph_name] = val
        else:
            lab_logger.debug("Morph data {0} not found".format(morph_name))









