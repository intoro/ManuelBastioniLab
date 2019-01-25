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

import math
import array
import bpy
import os
import time
import logging
import json
from . import algorithms
lab_logger = logging.getLogger('manuelbastionilab_logger')
class MaterialEngine:

    def __init__(self, obj, data_path, details_filename):
        time1 = time.time()
        if obj:

            self.attributes_to_use = ["name","bl_idname","label","location","height","width",
                                "color_space","extension","interpolation","projection",
                                "projection_blend","turbulence_depth","musgrave_type",
                                "distribution","component","invert","color_layer","coloring",
                                "uv_layer","lamp_object","max","min","rotation","scale","translation",
                                "use_max","use_min","vector_type","operation","use_clamp","blend_type",
                                "from_dupli","convert_from","convert_to","use_pixel_size",
                                "use_alpha","space","uv_map","falloff","axis","direction_type"]

            self.obj_name = obj.name
            self.texture_data_path = os.path.join(data_path,"shared_textures")
            self.texture_dermal_exist = False
            self.texture_displace_exist = False

            character_type = obj.name.split("_")[0]
            gender_type = obj.name.split("_")[1]

            self.filename_material = character_type +".json"

            self.filename_disp = character_type +"_"+ gender_type + "_displacement.png"
            self.filename_diffuse = character_type +"_"+ gender_type + "_diffuse.png"
            self.material_data_path = os.path.join(
                data_path,
                "shared_materials",
                self.filename_material)

            self.load_materials(self.material_data_path)
            self.parameter_identifiers = ["skin_", "eyes_"]
            self.material_identifiers = ["_skin", "_eyes", "_teeth"]

            self.material_names = []
            for material in obj.data.materials:
                for material_id in self.material_identifiers:
                    if material_id in material.name:
                        lab_logger.info("Assigned shader {0} to the human".format(material.name))
                        self.material_names.append(material.name)

            if len(self.material_names) < 2:
                lab_logger.warning("Some material are missed")

            self.displace_data_path = os.path.join(
                self.texture_data_path,
                self.filename_disp)

            self.dermal_texture_path = os.path.join(
                self.texture_data_path,
                self.filename_diffuse)

            if os.path.isfile(self.dermal_texture_path):
                self.texture_dermal_exist = True

            if os.path.isfile(self.displace_data_path):
                self.texture_displace_exist = True

            self.img_paths = [self.displace_data_path,
                            self.dermal_texture_path]

            self.load_data_images()

            if hasattr(obj, 'character_ID'):
                self.material_ID = obj.character_ID
            else:
                lab_logger.error("The object has not character ID")

            self.generated_disp_image_name = self.material_ID+"_disp.png"
            self.generated_disp_modifier_ID = "mbastlab_disp_"+self.material_ID
            self.generated_disp_texture_name = "displ_tex_"+self.material_ID
            self.subdivision_modifier_name = "mbastlab_subd_"+self.material_ID

    def load_data_images(self):
        for img_path in self.img_paths:
            self.load_image(img_path)

    def load_texture(self, img_path, shader_target):
        self.load_image(img_path)
        self.update_data_filename(img_path, shader_target)
        self.update_shaders()


    def update_data_filename(self,img_path, shader_target):
        if shader_target == "body_derm":
            self.filename_diffuse = os.path.basename(img_path)
        if shader_target == "body_displ":
            self.generated_disp_image_name =  os.path.basename(img_path)

    def get_data_filename(self, shader_target):
        img_name = None
        if shader_target == "body_derm":
            img_name = self.filename_diffuse
        if shader_target == "body_displ":            
            img_name = self.generated_disp_image_name
        return img_name

    def check_file_name(self,file_name1,file_name2):
        name_wt_extension = os.path.splitext(file_name1)[0]
        if name_wt_extension in file_name2:
            return True
        else:
            return False



    def load_image(self,img_path):
        if os.path.exists(img_path):
            img_block_already_in_scene = False
            new_image_filename = os.path.basename(img_path)
            for img in bpy.data.images:
                existing_image_filename = os.path.basename(img.filepath)

                if self.check_file_name(new_image_filename,existing_image_filename):
                    img.name = new_image_filename
                    img.filepath = img_path
                    img_block_already_in_scene = True
                    lab_logger.info("Updating existing image data: {0}".format(existing_image_filename))

            if not img_block_already_in_scene:
                if bpy.app.version > (2,76,0):
                    bpy.data.images.load(img_path, check_existing=True)
                else:
                    bpy.data.images.load(img_path)
                lab_logger.info("Loading image: {0}".format(algorithms.simple_path(img_path)))
        else:

            lab_logger.warning("Loading failed. Image not found: {0}".format(algorithms.simple_path(img_path)))


    def image_to_array(self, blender_image):
        return array.array('f',blender_image.pixels[:])

    def calculate_disp_pixels(self, blender_image, age_factor,tone_factor,mass_factor):

        source_data_image = self.image_to_array(blender_image)
        result_image= array.array('f')

        if age_factor > 0:
            age_f = age_factor
        else:
            age_f = 0

        if tone_factor > 0:
            tone_f = tone_factor
        else:
            tone_f = 0

        if mass_factor > 0:
            mass_f = (1-tone_f)*mass_factor
        else:
            mass_f = 0

        for i in range(0,len(source_data_image),4):
            r = source_data_image[i]
            g = source_data_image[i+1]
            b = source_data_image[i+2]
            a = source_data_image[i+3]

            details = r
            age_disp = age_f*(g-0.5)
            tone_disp = tone_f*(b-0.5)
            mass_disp = mass_f*(a-0.5)

            add_result = details+age_disp+tone_disp+mass_disp
            if add_result > 1.0:
                add_result = 1.0

            for i2 in range(3):
                result_image.append(add_result) #R,G,B
            result_image.append(1.0)#Alpha is always 1

        return result_image.tolist()

    def multiply_images(self, blender_image1, blender_image2, result_name, blending_factor = 0.5, ):

        if blender_image1 and blender_image2:
            size1 = blender_image1.size
            size2 = blender_image2.size

            if size1[0] != size1[1]:
                return None

            if size2[0] != size2[1]:
                return None

            if size1[0]*size1[1] > size2[0]*size2[1]:
                blender_image2.scale(size1[0],size1[1])

            if size1[0]*size1[1] < size2[0]*size2[1]:
                blender_image1.scale(size2[0],size2[1])

            image1 = self.image_to_array(blender_image1)
            image2 = self.image_to_array(blender_image2)


            result_array= array.array('f')

            for i in range(len(image1)):

                px1 = image1[i]
                px2 = image2[i]
                px_result = (px1 * px2 * blending_factor) + (px1 * (1 - blending_factor))

                result_array.append(px_result)

            result_img = self.new_image(result_name, blender_image1.size)
            result_img.pixels =  result_array.tolist()


    def set_node_image(self, material_name, node_name, image_name):
        lab_logger.info("Assigning the image {0} to node {1}".format(image_name,node_name))
        mat_node = self.get_material_node(material_name, node_name)
        if mat_node:
            mat_image = self.get_image(image_name)
            if mat_image:
                mat_node.image = mat_image
            else:
                lab_logger.warning("Node assignment failed. Image not found: {0}".format(image_name))


    def get_material_parameters(self):


        material_parameters = {}

        for material_name in self.material_names:
            material = self.get_material(material_name)
            if material:
                if material.node_tree:
                    for node in material.node_tree.nodes:
                        is_parameter = False
                        for param_identifier in self.parameter_identifiers:
                            if param_identifier in node.name:
                                is_parameter = True
                        if is_parameter == True:
                            material_parameters[node.name] = node.outputs[0].default_value
        return material_parameters



    def get_material_node(self, material_name, node_name):

        material_node = None

        material = self.get_material(material_name)
        if material:
            if node_name in material.node_tree.nodes:
                material_node = material.node_tree.nodes[node_name]

        if not material_node:
            lab_logger.warning("Node not found: {0} in material {1}".format(node_name,material_name))
        return material_node





    def set_node_float(self, material_name, node_name, value):
        mat_node = self.get_material_node(material_name, node_name)
        if mat_node:
            try:
                mat_node.outputs[0].default_value = value
            except:
                lab_logger.warning("Impossible to assign the default value to node {0}".format(node_name))


    def update_shaders(self, material_parameters = [], update_textures_nodes = True):

        for material_name in self.material_names:
            material = self.get_material(material_name)
            if material:
                if material.node_tree:
                    for node in material.node_tree.nodes:
                        if node.name in  material_parameters:
                            value = material_parameters[node.name]
                            self.set_node_float(material.name, node.name, value)
                        else:
                            if update_textures_nodes == True:
                                
                                if "_skn_diffuse" in node.name:
                                    self.set_node_image(material.name, node.name, self.filename_diffuse)
                                if "_eys_diffuse" in node.name:
                                    self.set_node_image(material.name, node.name, self.filename_diffuse)
                                if "_tth_diffuse" in node.name:
                                    self.set_node_image(material.name, node.name, self.filename_diffuse)
                                if "_skn_disp" in node.name:
                                    self.set_node_image(material.name, node.name, self.generated_disp_image_name)

    def get_material(self, material_name):
        obj = self.get_object()
        if obj:
            for material in obj.data.materials:
                if material_name == material.name:
                    return material
            lab_logger.warning("Material {0} not found in {1}".format(material_name, obj.name))
        return None


    def rename_skin_shaders(self):
        obj = self.get_object()
        for shader_name in self.material_names:
            human_mat = self.get_material(shader_name)
            if human_mat:
                human_mat.name = human_mat.name+str(time.time())

    def save_all_images(self, new_images_path):
        pass


    def get_object(self):
        if self.obj_name in bpy.data.objects:
            return bpy.data.objects[self.obj_name]
        lab_logger.error("Cannot found the obj {0} for material loading".format(self.obj_name))
        return None

    def add_subdivision_modifier(self):
        obj = self.get_object()
        if self.subdivision_modifier_name not in obj.modifiers:
            obj.modifiers.new(self.subdivision_modifier_name,'SUBSURF')
        obj.modifiers[self.subdivision_modifier_name].levels = 2
        obj.modifiers[self.subdivision_modifier_name].render_levels = 2
        obj.modifiers[self.subdivision_modifier_name].show_viewport = False
        obj.modifiers[self.subdivision_modifier_name].show_in_editmode = False



    def add_displacement_modifier(self):

        disp_data_image = self.get_image(self.filename_disp)
        if disp_data_image:
            lab_logger.info("Creating the displacement image from data image {0} with size {1}x{2}".format(disp_data_image.name, disp_data_image.size[0], disp_data_image.size[1]))
            disp_img = self.new_image(self.generated_disp_image_name, disp_data_image.size)
            disp_img.generated_color = (0.5,0.5,0.5,1)
            lab_logger.info("Created new displacement image {0} with size {1}x{2}".format(disp_img.name, disp_img.size[0], disp_img.size[1]))

            obj = self.get_object()
            if self.generated_disp_modifier_ID not in obj.modifiers:
                obj.modifiers.new(self.generated_disp_modifier_ID,'DISPLACE')
            displacement_modifier = obj.modifiers[self.generated_disp_modifier_ID]
            displacement_modifier.texture_coords = 'UV'
            displacement_modifier.strength = 0.01
            displacement_modifier.show_viewport = False

            disp_tex = self.new_texture(self.generated_disp_modifier_ID)
            disp_tex.image = disp_img
            displacement_modifier.texture = disp_tex
        else:
            lab_logger.warning("Cannot create the displacement modifier: data image not found: {0}".format(algorithms.simple_path(self.displace_data_path)))


    def remove_displacement_modifier(self):
        obj = self.get_object()
        if self.generated_disp_modifier_ID in obj.modifiers:
            obj.modifiers.remove(obj.modifiers[self.generated_disp_modifier_ID])


    def get_displacement_visibility(self):
        obj = self.get_object()
        if self.generated_disp_modifier_ID in obj.modifiers:
            return obj.modifiers[self.generated_disp_modifier_ID].show_viewport

    def get_subdivision_visibility(self):
        obj = self.get_object()
        if self.subdivision_modifier_name in obj.modifiers:
            return obj.modifiers[self.subdivision_modifier_name].show_viewport

    def set_subdivision_visibility(self, value):
        obj = self.get_object()
        if self.subdivision_modifier_name in obj.modifiers:
            obj.modifiers[self.subdivision_modifier_name].show_viewport = value

    def set_displacement_visibility(self, value):
        obj = self.get_object()
        if self.generated_disp_modifier_ID in obj.modifiers:
            obj.modifiers[self.generated_disp_modifier_ID].show_viewport =value


    def new_image(self, name, img_size):
        lab_logger.info("Creating new image {0} with size {1}x{2}". format(name,img_size[0],img_size[1]))
        if name in bpy.data.images:
            if bpy.app.version > (2,77,0):
                bpy.data.images.remove(bpy.data.images[name], do_unlink=True)
            else:
                bpy.data.images.remove(bpy.data.images[name])
            lab_logger.info("Previous existing image {0} replaced with the new one". format(name))
        bpy.data.images.new(name,img_size[0],img_size[1])
        return bpy.data.images[name]

    def get_image(self, name):
        lab_logger.info("Getting image {0}".format(name))
        if name:
            if name in bpy.data.images:

                #Some check for log
                if bpy.data.images[name].source == "FILE":
                    if os.path.basename(bpy.data.images[name].filepath) != name:
                        lab_logger.warning("Image named {0} is from file: {1}".format(name,os.path.basename(bpy.data.images[name].filepath)))

                return bpy.data.images[name]
            else:
                lab_logger.warning("Getting image failed. Image {0} not found in bpy.data.images".format(name))
        else:
            lab_logger.warning("Getting image failed. Image name is {0}".format(name))
        return None

    def new_texture(self, name):
        if name not in bpy.data.textures:
            bpy.data.textures.new(name, type = 'IMAGE')
        return bpy.data.textures[name]

    def save_image(self, name, filepath):
        lab_logger.info("Saving image {0} in {1}".format(name,algorithms.simple_path(filepath)))        
        img = self.get_image(name)
        scn = bpy.context.scene
        if img:
            current_format = scn.render.image_settings.file_format
            scn.render.image_settings.file_format = "PNG"
            img.save_render(filepath)
            scn.render.image_settings.file_format = current_format

            #if img.source == "GENERATED":
                #img.filepath_raw = filepath
                #img.file_format = scn.render.image_settings.file_format
                #img.save()
            #else:
                #img.save_render(filepath)
        else:
            lab_logger.warning("The image {0} cannot be saved because it's not present in bpy.data.images.". format(name))


    def has_displace_modifier(self):
        obj = self.get_object()
        return self.generated_disp_modifier_ID in obj.modifiers

    def calculate_displacement_texture(self,age_factor,tone_factor,mass_factor):
        time1 = time.time()

        if self.generated_disp_image_name in bpy.data.images:
            disp_img = bpy.data.images[self.generated_disp_image_name]
        else:
            lab_logger.warning("Displace image not found: {0}".format(self.generated_disp_image_name))
            return

        if self.generated_disp_modifier_ID in bpy.data.textures:
            disp_tex  = bpy.data.textures[self.generated_disp_modifier_ID]
        else:
            lab_logger.warning("Displace texture not found: {0}".format(self.generated_disp_modifier))
            return

        disp_data_image = self.get_image(self.filename_disp)
        if disp_data_image:
            disp_img.pixels =  self.calculate_disp_pixels(disp_data_image,age_factor,tone_factor,mass_factor)
            disp_tex.image = disp_img
            lab_logger.info("Displacement calculated in {0} seconds".format(time.time()-time1))
        else:
            lab_logger.error("Displace data image not found: {0}".format(algorithms.simple_path(self.displace_data_path)))


    def save_texture(self, filepath, shader_target):

        img_name = self.get_data_filename(shader_target)        
        self.save_image(img_name, filepath)
        self.load_image(filepath) #Load the just saved image to replace the current one
        self.update_data_filename(filepath, shader_target)
        self.update_shaders()


    def load_materials(self,filepath):

        obj = self.get_object()
        lab_logger.info("Loading materials from {0}".format(algorithms.simple_path(filepath)))

        if not obj:
            lab_logger.warning("Cannot load materials without a valid obj in the scene")
            return None
                        
        m_data = algorithms.load_json_data(filepath, "Materials data")        
        if m_data:
            for group in m_data["groups"]:
                lab_logger.info("Importing material group...{0}".format(group["name"]))
                if group:
                    group_name = group["name"]
                    group_type = group["type"]
                    group_nodes = group["nodes"]
                    links_data = group["links"]

                    if bpy.data.node_groups.get(group_name):
                        new_group = bpy.data.node_groups.get(group_name)
                    else:
                        new_group = bpy.data.node_groups.new(group_name,group_type)

                        new_nodes = new_group.nodes
                        new_nodes.clear()
                        self.create_nodes(group_nodes,new_nodes)

                        for inpt in group["inputs"]:
                            n_inpt = new_group.inputs.new(inpt["type"],inpt["name"] )
                            if "max_value" in inpt:
                                n_inpt.max_value = inpt["max_value"]
                            if "min_value" in inpt:
                                n_inpt.min_value = inpt["min_value"]


                        for outp in group["outputs"]:
                            n_outp = new_group.outputs.new(outp["type"],outp["name"] )
                            if "max_value" in outp:
                                n_outp.max_value = outp["max_value"]
                            if "min_value" in outp:
                                n_outp.min_value = outp["min_value"]

                        self.set_input_and_output(group_nodes,new_nodes)
                        self.create_links(links_data, new_group)


            for mat in m_data["materials"]:
                mat_name = mat["name"]

                mat_assigned = False
                for i in range(len(obj.data.materials)):
                    if mat_name in obj.data.materials[i].name:
                        new_mat = obj.data.materials[i]
                        mat_assigned = True

                if not mat_assigned:

                    lab_logger.warning("Material {0} not assigned".format(mat_name))
                    #new_mat = bpy.data.materials.new(mat_name)
                    #new_mat.diffuse_color = self.json_to_blender_type(mat,new_mat,"diffuse_color")

                if mat_assigned:
                    new_mat.use_nodes = True
                    new_nodes = new_mat.node_tree.nodes
                    new_nodes.clear()

                    nodes_data = mat['nodes']
                    links_data = mat["links"]

                    self.create_nodes(nodes_data, new_nodes)
                    self.set_input_and_output(nodes_data, new_nodes)
                    self.create_links(links_data, new_mat.node_tree)


    def set_input_and_output(self,nodes_data, new_nodes):
        for node_data in nodes_data:
            if node_data:
                new_node = new_nodes.get(node_data['name'])
                if new_node:
                    self.set_sockets_attributes(node_data["inputs"],new_node.inputs,new_node.name)
                    self.set_sockets_attributes(node_data["outputs"],new_node.outputs,new_node.name)


    def set_sockets_attributes(self,sockets_data,new_sockets,node_name):
        for idx1,sockt_data in enumerate(sockets_data):
            if 'default_value' in sockt_data:
                for idx2,new_sockt in enumerate(new_sockets):
                    if idx1 == idx2:
                        default_v = self.json_to_blender_type(sockt_data,new_sockt,'default_value')
                        if default_v != None:
                            setattr(new_sockt,'default_value',default_v)

    def set_node_attributes(self,node_data,new_node):
        for attr in self.attributes_to_use:
            if attr in node_data:
                default_v = self.json_to_blender_type(node_data,new_node,attr)
                if default_v:
                    setattr(new_node,attr,default_v)


    def create_nodes(self,nodes_data, new_nodes):
        for node_data in nodes_data:
            if node_data:
                new_node = new_nodes.new(node_data['bl_idname'])
                self.set_node_attributes(node_data,new_node)

            if node_data['bl_idname'] == "ShaderNodeGroup":
                if "node_tree" in node_data:
                    if bpy.data.node_groups.get(node_data['node_tree']):
                        new_node.node_tree = bpy.data.node_groups.get(node_data['node_tree'])

    def json_to_blender_type(self,json_data,blender_data,attrkey):

        default_val = None
        if hasattr(blender_data,attrkey):
            default_val = json_data[attrkey]
            if type(default_val) == list:
                native_val = getattr(blender_data,attrkey)
                for i,v in enumerate(default_val):
                    native_val[i] = v #to convert in blender type
                default_val = native_val
        return default_val

    def create_links(self,links_data,node_tree):
        for link_data in links_data:

            to_socket = link_data["to_socket"]
            to_node = link_data["to_node"]
            from_node = link_data["from_node"]
            from_socket = link_data["from_socket"]

            node1 = node_tree.nodes.get(from_node)
            node2 = node_tree.nodes.get(to_node)
            socket1 = None
            socket2 = None

            if node1:
                if len(node1.outputs) > from_socket:
                    socket1 = node1.outputs[from_socket]
                else:
                    lab_logger.warning("The number of output sockets in {0} is {1}. Cannot find socket with index {2} ".format(node1.name,len(node1.outputs),from_socket))
            else:
                lab_logger.warning("Cannot connet node {0}, because the node is not found".format(from_node))

            if node2:
                if len(node2.inputs) > to_socket:
                    socket2 = node2.inputs[to_socket]
                else:
                    lab_logger.warning("The number of input sockets in {0} is {1}. Cannot find socket with index {2} ".format(node2.name,len(node2.inputs),to_socket))
            else:
                lab_logger.warning("Cannot connet node {0}, because the node is not found".format(to_node))


            if socket1:
                if socket2:
                    node_tree.links.new(socket1, socket2)
                else:
                    lab_logger.warning("Socket2 {0} not found in Node {1}".format(to_socket,node2.name))
            else:
                lab_logger.warning("Socket1 {0} not found in Node {1}".format(from_socket,node1.name))



    def load_lamps(self,filepath):

        scene = bpy.context.scene
        l_data = algorithms.load_json_data(filepath,"Lamps data")

        for lampada in l_data["lamps"]:
            lamp_name = lampada["name"]
            lamp_type = lampada["type"]

            if lamp_name not in bpy.data.lamps:

                new_lamp_data = bpy.data.lamps.new(lamp_name, lamp_type)


                if "use_multiple_importance_sampling" in lampada:
                    new_lamp_data.cycles.use_multiple_importance_sampling = self.json_to_blender_type(lampada, new_lamp_data.cycles,'use_multiple_importance_sampling')

                if "cast_shadow" in lampada:
                    new_lamp_data.cycles.shadow_soft_size = self.json_to_blender_type(lampada, new_lamp_data.cycles,'cast_shadow')

                if "spot_size" in lampada:
                    new_lamp_data.spot_size = self.json_to_blender_type(lampada, new_lamp_data,'spot_size')

                if "spot_blend" in lampada:
                    new_lamp_data.spot_blend = self.json_to_blender_type(lampada, new_lamp_data,'spot_blend')


                new_lamp_obj = bpy.data.objects.new(name=lamp_name, object_data=new_lamp_data)
                scene.objects.link(new_lamp_obj)

                new_lamp_obj.location = self.json_to_blender_type(lampada, new_lamp_obj,'location')
                new_lamp_obj.rotation_mode = self.json_to_blender_type(lampada, new_lamp_obj,'rotation_mode')
                new_lamp_obj.rotation_euler = self.json_to_blender_type(lampada, new_lamp_obj,'rotation_euler')
                new_lamp_obj.scale = self.json_to_blender_type(lampada, new_lamp_obj,'scale')

                new_lamp_data.use_nodes = True
                new_nodes = new_lamp_data.node_tree.nodes
                new_nodes.clear()

                nodes_data = lampada['nodes']
                links_data = lampada["links"]

                self.create_nodes(nodes_data, new_nodes)
                self.set_input_and_output(nodes_data, new_nodes)
                self.create_links(links_data, new_lamp_data.node_tree)









