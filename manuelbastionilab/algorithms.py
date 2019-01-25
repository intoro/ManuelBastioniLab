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

import mathutils
import itertools
import random
import time
import logging
import os
import bpy
import json
lab_logger = logging.getLogger('manuelbastionilab_logger')

def simple_path(input_path, use_basename = True, max_len=50):
    """
    Return the last part of long paths
    """
    if use_basename == True:
        return os.path.basename(input_path)
    else:
        if len(input_path) > max_len:
            return("[Trunked].."+input_path[len(input_path)-max_len:])
        else:
            return input_path

def quick_dist(p_1, p_2):
    return ((p_1[0]-p_2[0])**2) + ((p_1[1]-p_2[1])**2) + ((p_1[2]-p_2[2])**2)

def full_dist(vert1, vert2, axis="ALL"):
    v1 = mathutils.Vector(vert1)
    v2 = mathutils.Vector(vert2)

    if axis not in ["X","Y","Z"]:
        v3 = v1-v2
        return v3.length
    if axis == "X":
        return abs(v1[0]-v2[0])
    if axis == "Y":
        return abs(v1[1]-v2[1])
    if axis == "Z":
        return abs(v1[2]-v2[2])


def length_of_strip(vertices_coords, indices, axis="ALL"):
    strip_length = 0
    for x in range(len(indices)-1):
        v1 = vertices_coords[indices[x]]
        v2 = vertices_coords[indices[x+1]]
        strip_length += full_dist(v1,v2, axis)
    return(strip_length)

def function_modifier_a(val_x):
    val_y = 0.0
    if val_x > 0.5:
        val_y = 2*val_x-1
    return val_y

def function_modifier_b(val_x):
    val_y = 0.0
    if val_x < 0.5:
        val_y = 1-2*val_x
    return val_y

def bounding_box(verts_coo, indices, roundness=4):

    val_x, val_y, val_z = [], [], []
    for idx in indices:
        if len(verts_coo) > idx:
            val_x.append(verts_coo[idx][0])
            val_y.append(verts_coo[idx][1])
            val_z.append(verts_coo[idx][2])
        else:
            lab_logger.warning("Error in calculating bounding box: index {0} not in verts_coo (len(verts_coo) = {1})".format(idx,len(verts_coo)))            
            return None

    box_x = round(max(val_x)-min(val_x), roundness)
    box_y = round(max(val_y)-min(val_y), roundness)
    box_z = round(max(val_z)-min(val_z), roundness)

    return (box_x, box_y, box_z)

def load_bbox_data(filepath):
    bboxes = []
    database_file = open(filepath, "r")
    for line in database_file:
        bboxes.append(line.split())
    database_file.close()

    bbox_data_dict = {}
    for x_data in bboxes:
        idx = x_data[0]
        idx_x_max = int(x_data[1])
        idx_y_max = int(x_data[2])
        idx_z_max = int(x_data[3])
        idx_x_min = int(x_data[4])
        idx_y_min = int(x_data[5])
        idx_z_min = int(x_data[6])

        bbox_data_dict[idx] = [
            idx_x_max, idx_y_max,
            idx_z_max, idx_x_min,
            idx_y_min, idx_z_min]
    return bbox_data_dict

def smart_combo(prefix, morph_values):

    debug1 = False
    debug2 = False
    tags = []
    names = []
    weights = []
    max_morph_values = []

    #Compute the combinations and get the max values
    for v_data in morph_values:
        tags.append(["max", "min"])
        max_morph_values.append(max(v_data))
    for n_data in itertools.product(*tags):
        names.append(prefix+"_"+'-'.join(n_data))

    #Compute the weight of each combination
    for n_data in itertools.product(*morph_values):
        weights.append(sum(n_data))

    factor = max(max_morph_values)
    best_val = max(weights)
    toll = 1.5

    #Filter on bestval and calculate the normalize factor
    summ = 0.0
    for i in range(len(weights)):
        weights[i] = max(0, weights[i]-best_val/toll)
        summ += weights[i]

    #Normalize using summ
    if summ != 0:
        for i in range(len(weights)):
            weights[i] = factor*(weights[i]/summ)

    if debug1:
        print("BESTVAL = {0}".format(best_val))
        print("SUM = {0}".format(summ))
        print("AVERAGE = {0}".format(factor))
    if debug2:
        print("MORPHINGS:")
        for i in range(len(names)):
            if weights[i] != 0:
                print(names[i], weights[i])
    return (names, weights)

def is_excluded(property_name, excluded_properties):
    for excluded_property in excluded_properties:
        if excluded_property in property_name:
            return True
    return False


def generate_parameter(val, random_value, preserve_phenotype=False):

    if preserve_phenotype:
        if val > 0.5:
            if val > 0.8:
                new_value = 0.8 + 0.2*random.random()
            else:
                new_value = 0.5+random.random()*random_value
        else:
            if val < 0.2:
                new_value = 0.2*random.random()
            else:
                new_value = 0.5-random.random()*random_value
    else:
        if random.random() > 0.5:
            new_value = min(1.0, 0.5+random.random()*random_value)
        else:
            new_value = max(0.0, 0.5-random.random()*random_value)
    return new_value


def polygon_forma(list_of_verts):

    form_factors = []
    for idx in range(len(list_of_verts)):
        index_a = idx
        index_b = idx-1
        index_c = idx+1
        if index_c > len(list_of_verts)-1:
            index_c = 0

        p_a = list_of_verts[index_a]
        p_b = list_of_verts[index_b]
        p_c = list_of_verts[index_c]

        v_1 = p_b-p_a
        v_2 = p_c-p_a

        v_1.normalize()
        v_2.normalize()

        factor = v_1.dot(v_2)
        form_factors.append(factor)
    return form_factors

def average_center(verts_coords):

    n_verts = len(verts_coords)
    bcenter = mathutils.Vector((0.0, 0.0, 0.0))
    if n_verts != 0:
        for v_coord in verts_coords:
            bcenter += v_coord
        bcenter = bcenter/n_verts
    return bcenter


def linear_interpolation_y(xa,xb,ya,yb,y):
    return (((xa-xb)*y)+(xb*ya)-(xa*yb))/(ya-yb)


def correct_morph(base_form, current_form, morph_deltas, bboxes):
    time1 = time.time()
    new_morph_deltas = []
    for d_data in morph_deltas:

        idx = d_data[0]        

        if str(idx) in bboxes:
            indices = bboxes[str(idx)]
            current_bounding_box = bounding_box(current_form, indices)
            if current_bounding_box:
                base_bounding_box = bounding_box(base_form, indices)
                if base_bounding_box:

                    if base_bounding_box[0] != 0:
                        scale_x = current_bounding_box[0]/base_bounding_box[0]
                    else:
                        scale_x = 1

                    if base_bounding_box[1] != 0:
                        scale_y = current_bounding_box[1]/base_bounding_box[1]
                    else:
                        scale_y = 1

                    if base_bounding_box[2] != 0:
                        scale_z = current_bounding_box[2]/base_bounding_box[2]
                    else:
                        scale_z = 1

                    delta_x = d_data[1][0] * scale_x
                    delta_y = d_data[1][1] * scale_y
                    delta_z = d_data[1][2] * scale_z

                    newd = mathutils.Vector((delta_x, delta_y, delta_z))
                    new_morph_deltas.append([idx, newd])
        else:
            new_morph_deltas.append(d_data)            
            lab_logger.warning("Index {0} not in bounding box database".format(idx))
    lab_logger.info("Morphing corrected in {0} secs".format(time.time()-time1))
    return new_morph_deltas


def check_name_structure(obj_name):
    name_parts = obj_name.split('_')
    valid_names_roots = ["human","anime"]
    if name_parts[0] in valid_names_roots:
        if '.' not in name_parts[1]:
            return True
    return False


def looking_for_humanoid_obj():
        """
        Looking for a mesh that is OK for the lab
        """
        lab_logger.info("Looking for an humanoid object...")
        if bpy.app.version >= (2,78,0):
            lab_logger.info("Blender version check passed...")
            for obj in bpy.data.objects:
                if obj.type == "MESH":
                    lab_logger.info("Object type passed...")
                    if "manuellab_vers" in obj.keys():
                        lab_logger.info("Manuellab presence passed...")
                        if check_version(obj["manuellab_vers"]):
                            lab_logger.info("Manuellab version passed...")
                            if not obj.data.shape_keys:
                                lab_logger.info("Shapekeys presence passed...")
                                if check_name_structure(obj.name):
                                    lab_logger.info("Name structure passed...")
                                    return ("FOUND", obj.name)
                                else:
                                    msg = "{0} has wrong name. Please fix it.".format(obj.name)
                                    return("ERROR",msg)
                            else:
                                msg = "{0} has some shapekeys and can't be used in the lab".format(obj.name)
                                lab_logger.warning(msg)
                                return("ERROR",msg)
                        else:
                            msg = "{0} is created with a different version of the lab.".format(obj.name)
                            lab_logger.warning(msg)
                            return("ERROR",msg)
        else:
            msg = "Sorry, the lab requires Blender 2.78 or higher."
            lab_logger.warning(msg)
            return("ERROR",msg)

        msg = "No existing valid human objects found in the scene"
        lab_logger.info(msg)
        return("NO_OBJ", msg )

def check_version(m_vers):

    version_check = False

    #m_vers can be a list, tuple, IDfloatarray or str
    #so it must be converted in a list.
    if type(m_vers) is not str:
        m_vers = list(m_vers)

    mesh_version = str(m_vers)
    mesh_version = mesh_version.replace(' ','')
    mesh_version = mesh_version.strip("[]()")
    if len (mesh_version) < 5:
        lab_logger.warning("The current humanoid has wrong format for version")
        return False

    mesh_version = (float(mesh_version[0]), float(mesh_version[2]), float(mesh_version[4]))
    lab_logger.info("Humanoid version property: {0}".format(mesh_version))

    if mesh_version > (1,3,0):
        version_check = True

    lab_logger.info("Version_check: {0}".format(version_check))
    return version_check

def is_string_in_string(b_string, b_name):
    if b_string and b_name:
        if b_string.lower() in b_name.lower():
            return True
    return False

def is_too_much_similar(string1,string2,val=2):
    s1 = set(string1)
    s2 = set(string2)

    if len(s1) > len(s2):
        threshold = len(s1)- val
    else:
        threshold = len(s2)- val

    if len(s1.intersection(s2)) > threshold:
        return True
    return False

def is_in_list(list1,list2,position="ANY"):

    for element1 in list1:
        for element2 in list2:
            if position == "ANY":
                if element1.lower() in element2.lower():
                    return True
            if position == "START":
                if element1.lower() in element2[:len(element1)].lower():
                    return True
            if position == "END":
                if element1.lower() in element2[len(element1):].lower():
                    return True
    return False

def load_json_data(json_path, data_info=None):
    if os.path.isfile(json_path):
        time1 = time.time()
        j_file = open(json_path, "r")
        j_database = None
        try:
            j_database = json.load(j_file)
        except:
            lab_logger.warning("Errors in json file: {0}".format(simple_path(json_path)))
        j_file.close()
        if not data_info:
            lab_logger.info("Json database {0} loaded in {1} secs".format(simple_path(json_path),time.time()-time1))
        else:
            lab_logger.info("{0} loaded from {1} in {2} secs".format(data_info,simple_path(json_path),time.time()-time1))
        return j_database
    else:
        lab_logger.warning("File not found: {0}".format(simple_path(json_path)))
        return None
        
        
def unselect_all():
    for obj in bpy.data.objects:
        obj.select = False
    

def select_and_change_mode(obj,obj_mode,hidden=False):  
    
    
    unselect_all()
    if obj:
        obj.select = True
        bpy.context.scene.objects.active = obj
        force_visible_object(obj)
        try:
            bpy.ops.object.mode_set(mode=obj_mode)
            lab_logger.debug("Select and change mode of {0} = {1}".format(obj.name,obj_mode))
        except:
            lab_logger.error("Can't change the mode of {0} to {1}.".format(obj.name,obj_mode))        
        obj.hide = hidden

def force_visible_object(obj):
    """
    Blender requires the armature is visible in order
    to handle it.
    """
    if obj:
        lab_logger.debug("Turn the visibility of {0} ON".format(obj.name))
        if obj.hide == True:
            obj.hide = False
        for n in range(len(obj.layers)):
            obj.layers[n] = False
        current_layer_index = bpy.context.scene.active_layer
        obj.layers[current_layer_index] = True
        
def collect_existing_objects():    
    scene = bpy.context.scene
    existing_obj_names = []
    for obj in scene.objects:
        if hasattr(obj, "name"):
            existing_obj_names.append(obj.name)
    return existing_obj_names
    
def get_newest_object(existing_obj_names):
    scene = bpy.context.scene
    for obj in scene.objects:
        if hasattr(obj, "name"):
            if obj.name not in existing_obj_names:
                return get_object_by_name(obj.name)
    return None
    
def get_object_by_name(name):
    if name in bpy.data.objects:
        return bpy.data.objects[name]
    return None
                
            

    
