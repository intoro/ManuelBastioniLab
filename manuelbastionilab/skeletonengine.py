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

import bpy, os, json
import mathutils
from . import algorithms

import logging
lab_logger = logging.getLogger('manuelbastionilab_logger')

class SkeletonEngine:

    def __init__(self, obj_body, data_path):
        self.has_data = False



        if obj_body:

            self.body_name = obj_body.name
            self.joints_indices = {}
            self.default_bone_names = []

            character_type = obj_body.name.split("_")[0]
            gender_type = obj_body.name.split("_")[1]

            self.knowledge_path = os.path.join(data_path,"retarget_knowledge.json")

            self.armature_modifier_name = "mbastlab_armature"
            self.joints_filename = character_type+"_"+gender_type+"_joints.json"
            self.skeleton_filename = character_type+"_"+gender_type+"_skeleton.json"
            self.groups_filename = character_type+"_"+gender_type+"_vgroups.json"

            self.bones_to_rotate_world = ["pelvis","thigh_L","thigh_R","calf_L","calf_R","foot_L","foot_R","toe_L","toe_R","lowerarm_L","lowerarm_R","upperarm_L","upperarm_R","hand_R","hand_L"]
            self.bones_to_rotate_local = []
            self.bones_to_exclude = []
            #self.bones_to_exclude = ["clavicle_R","clavicle_L"]

            self.joints_data_path = os.path.join(
                data_path,
                "shared_joints",
                self.joints_filename)

            self.skeleton_data_path = os.path.join(
                data_path,
                "shared_skeletons",
                self.skeleton_filename)

            self.vgroup_data_path = os.path.join(
                data_path,
                "shared_vgroups",
                self.groups_filename)


            self.jointsDatabase = self.load_joints_database(self.joints_data_path)
            self.knowledge_database = algorithms.load_json_data(self.knowledge_path,"Skeleton knowledge data")

            if self.check_skeleton(obj_body):
                obj_armat = obj_body.parent
            else:
                obj_armat = self.load_bones()

            if obj_armat != None:
                self.armature_visibility = [x for x in obj_armat.layers]
                self.armature_name = obj_armat.name
                self.align_bones_z_axis()
                obj_body.parent = obj_armat

                self.has_data = True

            self.load_groups(self.vgroup_data_path)
            self.add_armature_modifier()
            self.skeleton_mapped = {}





    def set_source_armature(self,source_armature):
        if source_armature:
            armat = self.get_armature()
            armat['animation_source'] = source_armature.name
            lab_logger.info("Source armat = {0}".format(armat['animation_source']))

    def check_skeleton(self, obj_body):
        if obj_body.parent:
            if obj_body.parent.type == 'ARMATURE':
                    return True
        return False



    def add_armature_modifier(self):
        obj = self.get_body()
        armat = self.get_armature()
        if self.armature_modifier_name not in obj.modifiers:
            obj.modifiers.new(self.armature_modifier_name,'ARMATURE')
        obj.modifiers[self.armature_modifier_name].object = armat
        
    def move_up_armature_modifier(self):
        obj = self.get_body()
        if self.armature_modifier_name in obj.modifiers:
            for n in range(len(obj.modifiers)):
                bpy.ops.object.modifier_move_up(modifier=self.armature_modifier_name)
        
        

    def apply_armature_modifier(self):
        obj = self.get_body()
        if self.armature_modifier_name in obj.modifiers:
            bpy.ops.object.modifier_apply(apply_as='DATA', modifier=self.armature_modifier_name)

    def apply_pose_as_rest_pose(self):
        armat = self.get_armature()
        obj = self.get_body()
        algorithms.select_and_change_mode(armat,'POSE')
        bpy.ops.pose.armature_apply()
        algorithms.select_and_change_mode(obj,'OBJECT')



    def error_msg(self, path):
        lab_logger.error("Database file not found: {0}".format(algorithms.simple_path(path)))


    def align_bones_z_axis(self):
        bones_data = algorithms.load_json_data(self.skeleton_data_path,"Z alignment data")
        armat = self.get_armature()
        source_armat = self.get_source_armature()
        armature_z_axis = {}

        if armat:

            if source_armat:
                lab_logger.info("Aligning Z axis of {0} with Z axis of {1}".format(armat.name,source_armat.name))
                algorithms.select_and_change_mode(source_armat,'EDIT')
                for b_name in self.default_bone_names:
                    source_bone_name = self.mapped_name(b_name)
                    if source_bone_name != None:
                        armature_z_axis[b_name] = source_armat.data.edit_bones[source_bone_name].z_axis.copy()
                    else:
                        lab_logger.debug("Bone {0} non mapped".format(b_name))
                algorithms.select_and_change_mode(source_armat,'POSE')
            else:
                if bones_data:
                    for nbone in bones_data:
                        armature_z_axis[nbone['name']] = mathutils.Vector(nbone['z_axis'])


            algorithms.select_and_change_mode(armat,'EDIT')
            for armat_bone in armat.data.edit_bones:
                if armat_bone.name in armature_z_axis:
                    z_axis = armature_z_axis[armat_bone.name]
                    armat_bone.align_roll(z_axis)
            algorithms.select_and_change_mode(armat,'POSE')


    def load_bones_position(self):
        bones_data = algorithms.load_json_data(self.skeleton_data_path)
        armat = self.get_armature()
        if bones_data and armat:
            algorithms.select_and_change_mode(armat,'EDIT')
            for nbone in bones_data:
                if nbone['name'] in armat.data.edit_bones:
                    armat_bone = armat.data.edit_bones[nbone['name']]
                    armat_bone.head = mathutils.Vector(nbone['head'])
                    armat_bone.tail = mathutils.Vector(nbone['tail'])
            algorithms.select_and_change_mode(armat,'POSE')


    def load_bones(self):

        bones_data = algorithms.load_json_data(self.skeleton_data_path,"Skeleton data")
        if bones_data:
            scene = bpy.context.scene
            new_armat_data = bpy.data.armatures.new("human_skeleton")
            armat_obj = bpy.data.objects.new("human_skeleton", new_armat_data)
            scene.objects.link(armat_obj)
            algorithms.select_and_change_mode(armat_obj,'EDIT')

            for nbone in bones_data:
                self.default_bone_names.append(nbone['name'])
                new_bone = new_armat_data.edit_bones.new(nbone['name'])
                new_bone.head = mathutils.Vector(nbone['head'])
                new_bone.tail = mathutils.Vector(nbone['tail'])
                new_bone.use_connect = nbone['use_connect']

            for nbone in bones_data:
                new_bone = new_armat_data.edit_bones[nbone['name']]
                if 'parent' in nbone.keys():
                    parent_name = nbone['parent']
                    if parent_name in new_armat_data.edit_bones:
                        new_bone.parent = new_armat_data.edit_bones[parent_name]

            algorithms.select_and_change_mode(armat_obj,'POSE')

            for a_bone in armat_obj.pose.bones:
                if "root" not in a_bone.name:
                    a_bone.lock_location[0] = True
                    a_bone.lock_location[1] = True
                    a_bone.lock_location[2] = True

            armat_obj.data.draw_type = "WIRE"
            return armat_obj
        return None

    def load_groups(self,filepath,use_weights = True,clear_all=True):

        obj = self.get_body()
        g_data = algorithms.load_json_data(filepath,"Vertgroups data")

        if clear_all:
            obj.vertex_groups.clear()

        group_names = sorted(g_data.keys())
        for group_name in group_names:
            new_group = obj.vertex_groups.new(name=group_name)
            for vert_data in g_data[group_name]:
                if use_weights:
                    if type(vert_data) == list:
                        new_group.add([vert_data[0]], vert_data[1], 'REPLACE')
                    else:
                        lab_logger.info("Error: wrong format for vert weight")
                else:
                    if type(vert_data) == int:
                        new_group.add([vert_data], 1.0, 'REPLACE')
                    else:
                        lab_logger.info("Error: wrong format for vert group")

        lab_logger.info("Group loaded from {0}".format(algorithms.simple_path(filepath)))


    def get_body(self):
        if self.has_data:
            lab_logger.debug("Getting character body")
            if self.body_name in bpy.data.objects:
                return bpy.data.objects[self.body_name]
            else:
                lab_logger.warning("Body {0} not found".format(self.body_name))
                return None

    def get_armature(self):
        if self.has_data:
            lab_logger.debug("Getting character armature")
            if self.armature_name in bpy.data.objects:
                if bpy.data.objects[self.armature_name].type == 'ARMATURE':
                    return bpy.data.objects[self.armature_name]
                else:
                    lab_logger.warning("Object {0} is not an armature".format(self.armature_name))
            else:
                lab_logger.warning("Armature {0} not found".format(self.armature_name))
                return None

    def __bool__(self):
        armat = self.get_armature()
        body = self.get_body()
        if body and armat:
            return True
        else:
            return False





    def load_joints_database(self, data_path):
        joint_data = algorithms.load_json_data(data_path,"Joints data")
        return joint_data


    def fit_joints(self):
        armat = self.get_armature()
        body = self.get_body()

        if armat and body:

            algorithms.force_visible_object(armat)
            lab_logger.debug("Fitting armature {0}".format(armat.name))
            if armat.data.use_mirror_x == True:
                armat.data.use_mirror_x = False

            # must be active in order to turn in edit mode.
            #if the armature is not in edit mode...
            #...armature.data.edit_bones is empty

            current_active_obj = bpy.context.scene.objects.active
            algorithms.select_and_change_mode(armat,"EDIT")

            for a_bone in armat.data.edit_bones:
                tail_name = "".join((a_bone.name, "_tail"))
                head_name = "".join((a_bone.name, "_head"))

                if tail_name in self.jointsDatabase:
                    joint_verts_coords = []
                    for v_idx in self.jointsDatabase[tail_name]:
                        joint_verts_coords.append(body.data.vertices[v_idx].co)
                    tail_position = algorithms.average_center(joint_verts_coords)
                    a_bone.tail = tail_position

                if head_name in self.jointsDatabase:
                    joint_verts_coords = []
                    for v_idx in self.jointsDatabase[head_name]:
                        joint_verts_coords.append(body.data.vertices[v_idx].co)
                    head_position = algorithms.average_center(joint_verts_coords)
                    a_bone.head = head_position

            algorithms.select_and_change_mode(armat,"OBJECT")

            source_armat = self.get_source_armature()
            if source_armat:
                self.use_animation_pelvis(armat,source_armat)
            self.align_bones_z_axis()
            bpy.context.scene.objects.active = current_active_obj


    def load_pose(self, data_path):
        self.remove_animation()
        self.reset_pose()
        armat = self.get_armature()

        if armat:
            matrix_data = algorithms.load_json_data(data_path,"Pose data")
            algorithms.force_visible_object(armat)
            algorithms.select_and_change_mode(armat,"POSE")
            for a_bone in armat.pose.bones:
                if a_bone.name in matrix_data:
                    a_bone.rotation_quaternion = mathutils.Quaternion(matrix_data[a_bone.name])


    def save_pose(self, data_path):
        armat = self.get_armature()

        if armat:
            matrix_data = {}            
            algorithms.force_visible_object(armat)
            for a_bone in armat.pose.bones:
                matrix_data[a_bone.name] = [value for value in a_bone.rotation_quaternion]            
            fp = open(data_path, 'w')
            json.dump(matrix_data,fp)
            fp.close()

    def remove_source_armature(self,source_armat=None):

        body = self.get_body()
        if not source_armat:
            source_armat = self.get_source_armature()

        if source_armat != None:
            lab_logger.info("Removing source armature: {0}".format(source_armat))
            algorithms.force_visible_object(source_armat)
            algorithms.select_and_change_mode(source_armat,"OBJECT")
            bpy.ops.object.delete()
            algorithms.select_and_change_mode(body,"OBJECT")


    def remove_animation(self):
        self.remove_copy_rotations()
        self.clear_action()





    def reset_pose(self):

        armat = self.get_armature()
        reset_quat =  mathutils.Quaternion((1.0, 0.0, 0.0, 0.0))        
        if armat:            
            self.load_bones_position()
            self.align_bones_z_axis()
            for a_bone in armat.pose.bones:
                a_bone.rotation_quaternion = reset_quat
                if a_bone.name == "pelvis":
                    a_bone.location = mathutils.Vector((0,0,0))            

        obj = self.get_body()
        if obj:
            bpy.context.scene.objects.active = obj

    def is_in_rest_pose(self):
        armat = self.get_armature()
        is_rest = False
        if armat:            
            algorithms.force_visible_object(armat)
            reset_quat =  mathutils.Quaternion((1.0, 0.0, 0.0, 0.0))
            is_rest = True
            for a_bone in armat.pose.bones:
                if a_bone.rotation_quaternion != reset_quat:
                    is_rest = False            
        return is_rest   


    def reset_skeleton_mapped(self):
        self.skeleton_mapped = {}

    def init_skeleton_map(self,source_armat):

        self.reset_skeleton_mapped()
        self.already_mapped_bones = []
        self.spine_bones_names = None
        self.rarm_bones_names = None
        self.larm_bones_names = None
        self.rleg_bones_names = None
        self.lleg_bones_names = None
        self.head_bones_names = None
        self.pelvis_bones_names = None
        self.rtoe1_bones_names = None
        self.rtoe2_bones_names = None
        self.rtoe3_bones_names = None
        self.rtoe4_bones_names = None
        self.rtoe5_bones_names = None
        self.ltoe1_bones_names = None
        self.ltoe2_bones_names = None
        self.ltoe3_bones_names = None
        self.ltoe4_bones_names = None
        self.ltoe5_bones_names = None
        self.rfinger0_bones_names = None
        self.rfinger1_bones_names = None
        self.rfinger2_bones_names = None
        self.rfinger3_bones_names = None
        self.rfinger4_bones_names = None
        self.lfinger0_bones_names = None
        self.lfinger1_bones_names = None
        self.lfinger2_bones_names = None
        self.lfinger3_bones_names = None
        self.lfinger4_bones_names = None

        self.map_main_bones(source_armat)


    def get_bone_by_exact_ID(self, bones_to_scan, bone_identifiers, side):

        if bones_to_scan:
            if side == 'RIGHT':
                side_id = ["r","right"]
                junctions = [".","_","-",""]
            elif side == 'LEFT':
                side_id = ["l","left"]
                junctions = [".","_","-",""]
            else:
                side_id = [""]
                junctions = [""]
            name_combination = []

            for b_id in bone_identifiers:
                for s_id in side_id:
                    for junct in junctions:
                        name_combination.append(b_id+junct+s_id)
                        name_combination.append(s_id+junct+b_id)

            for b_name in bones_to_scan:
                if b_name.lower() in name_combination:
                    return b_name
        return None



    def get_bone_by_childr(self, armat, bones_to_scan, childr_identifiers, debug = False):

        if len(childr_identifiers) > 0:
            for bone_name in bones_to_scan:
                x_bone = self.get_bone(armat,bone_name)
                if x_bone:
                    for ch_bone in x_bone.children:
                        for ch_ID in childr_identifiers:
                            c1 = algorithms.is_string_in_string(ch_ID,ch_bone.name)
                            c2 = ch_bone.name in bones_to_scan
                            c3 = algorithms.is_too_much_similar(x_bone.name,ch_bone.name)
                            if c1 and c2 and not c3:
                                return x_bone.name
        return None


    def get_bones_by_index(self, bones_chain,index_data):
        index = None
        if bones_chain:
            if len(index_data) == 1:
                if index_data[0] == "LAST":
                    index = len(bones_chain)-1
                else:
                    index = index_data[0]
            if len(index_data) == 3:
                if len(bones_chain) == index_data[0]:
                    index = index_data[1]
                else:
                    index = index_data[2]

            if index == "None":
                index = None

            if index != None:
                try:
                    return bones_chain[index]
                except:
                    lab_logger.warning("Index of {0} out of range".format(bones_chain))

        return None


    def get_bones_by_parent(self, armat, bones_to_scan, parent_IDs):
        found_bones = set()
        for bone_name in bones_to_scan:
            parent_name = self.bone_parent_name(armat,bone_name)
            for pr_ID in parent_IDs:
                if algorithms.is_string_in_string(pr_ID, parent_name):
                    found_bones.add(bone_name)
        return found_bones


    def get_bone_chains(self, armat, bone_names):
        found_chains = []
        for bone_name in bone_names:
            bn = armat.data.bones[bone_name]
            chain_names = [b.name for b in bn.parent_recursive]
            chain = [bone_name]+chain_names
            found_chains.append(chain)
        return found_chains


    def is_in_side(self,bone_names,side):

        bone_IDs = ["forearm","elbow","lowerarm","hand","wrist","finger","thumb","index","ring","pink",\
                    "thigh","upperleg","upper_leg","leg","knee","shin","calf","lowerleg","lower_leg",\
                    "toe","ball","foot"]

        combo_bones_start = []
        combo_bones_end = []

        score_level = 0.0

        if side == "RIGHT":
            ID_side1 = "r"
            ID_side2 = "right"
            ID_side3 = ["r.","r_"]
            ID_side4 = ["_r",".r"]

        if side == "LEFT":
            ID_side1 = "l"
            ID_side2 = "left"
            ID_side3 = ["l.","l_"]
            ID_side4 = ["_l",".l"]

        for b_ID in bone_IDs:
            combo_bones_start.append(ID_side1 + b_ID)
            combo_bones_end.append(b_ID + ID_side1)

        for bone_name in bone_names:
            bone_name = bone_name.lower()

            if len(bone_name) > 3:
                c1 = bone_name[:2] in ID_side3
                c2 = bone_name[-2:] in ID_side4
                c3 = ID_side2 in bone_name
                c4 = algorithms.is_in_list(bone_names,combo_bones_start,"START")
                c5 = algorithms.is_in_list(bone_names,combo_bones_end,"END")
                if  c1 or c2 or c3 or c4 or c5:
                    score_level += 1

        if len(bone_names) != 0:
            final_score = score_level/len(bone_names)
        else:
            return 0
        return final_score

    def order_with_list(self,bones_set,bones_list):
        ordered_bones = []
        for nm in bones_list:
            if nm in bones_set:
                ordered_bones.append(nm)
        return ordered_bones

    def chains_intersection(self,chains):

        chain_sets = []
        chain_inters = None
        result_chain = []

        for chain in chains:
            chain_sets.append(set(chain))

        for i,chain in enumerate(chain_sets):
            if chain_inters == None:
                chain_inters = chain
            else:
                chain_inters = chain_inters.intersection(chain)
            result_chain = self.order_with_list(chain_inters,chains[i])

        return result_chain

    def filter_chains_by_max_length(self,chains):
        longer_chains = []
        max_length = 0

        for chain in chains:
            max_length = max(max_length,len(chain))

        for chain in chains:
            if len(chain) == max_length:
                longer_chains.append(chain)
        return longer_chains

    def chains_difference(self,chain_list,subchain_list):
        subchain_set = set(subchain_list)
        chain_set = set(chain_list)
        d_chain = chain_set.difference(subchain_set)
        return self.order_with_list(d_chain,chain_list)

    def filter_chains_by_side(self,chains):


        left_chains = []
        right_chains = []
        center_chains = []
        for chain in chains:
            score_left = self.is_in_side(chain,"LEFT")
            score_right = self.is_in_side(chain,"RIGHT")

            if score_left > 0:
                left_chains.append(chain)
            elif score_right > 0:
                right_chains.append(chain)
            else:
                center_chains.append(chain)

        if len(center_chains) == 0:
            score_threshold = 0
            for chain in chains:
                score_left = self.is_in_side(chain,"LEFT")
                score_right = self.is_in_side(chain,"RIGHT")
                score_center = 1.0-score_left-score_right
                if score_center > score_threshold:
                    score_threshold = score_center
                    center_chain = chain

            center_chains.append(center_chain)
        return left_chains,center_chains,right_chains


    def filter_chains_by_tail(self,chains,chain_IDs):
        target_chains_lists = []
        if chains:
            for chain in chains:
                chain_tail = chain[0]
                if algorithms.is_in_list(chain_IDs,[chain_tail]):
                    target_chains_lists.append(chain)
        return target_chains_lists

    def filter_chains_by_ID(self,chains,chain_IDs):
        target_chains_lists = []
        for chain in chains:
            if algorithms.is_in_list(chain_IDs,chain):
                target_chains_lists.append(chain)
        return target_chains_lists

    def filter_chains_by_order(self, chains, n_ord):
        named_fingers = ["thu","ind","mid","ring","pink"]
        identifiers = []
        for chain in chains:
            if  len(chain) > 0:
                identifiers.append(chain[0])
        identifiers.sort()
        result_chain = []
        chain_order =None
        chain_ID = None

        if algorithms.is_in_list(named_fingers,identifiers):
            chain_order = "NAMED"
        else:
            chain_order = "NUMBERED"

        if chain_order == "NAMED":
            chain_ID = named_fingers[n_ord]

        if chain_order == "NUMBERED":
            if len(identifiers) > n_ord:
                chain_ID = identifiers[n_ord]

        if chain_ID:
            chain_ID = chain_ID.lower()

            for chain in chains:
                chain_tail = chain[0]
                chain_tail = chain_tail.lower()
                if chain_ID in chain_tail:
                    result_chain = chain
                    return result_chain
        return result_chain


    def identify_bone_chains(self,chains, debug = False):
        arm_chain_IDs = ["arm","elbow","hand","wrist","finger","thumb","index","ring","pink","mid"]
        leg_chain_IDs = ["thigh","upperleg","upper_leg","leg","knee","shin","calf","lowerleg","lower_leg","foot","ankle","toe","ball"]
        head_chain_IDs = ["head","neck","skull","face","spine"]
        finger_chain_IDs = ["finger","thumb","index","ring","pink","mid"]
        foot_chain_IDs = ["foot","ankle","toe","ball"]

        max_right_arm_chain = []
        max_left_arm_chain = []
        max_right_leg_chain = []
        max_left_leg_chain = []
        max_head_chain = []

        max_left_finger_chains = []
        max_right_finger_chains = []

        left_chains,center_chains,right_chains = self.filter_chains_by_side(chains)

        head_tail_chains = self.filter_chains_by_ID(center_chains,head_chain_IDs)
        head_tail_chains = self.filter_chains_by_max_length(head_tail_chains)

        arms_tail_chains = self.filter_chains_by_ID(chains,arm_chain_IDs)
        arms_tail_chains = self.filter_chains_by_max_length(arms_tail_chains)

        right_arm_tail_chains = self.filter_chains_by_tail(right_chains,arm_chain_IDs)
        right_arm_tail_chains = self.filter_chains_by_max_length(right_arm_tail_chains)

        left_arm_tail_chains = self.filter_chains_by_tail(left_chains,arm_chain_IDs)
        left_arm_tail_chains = self.filter_chains_by_max_length(left_arm_tail_chains)

        right_fingers_tail_chains = self.filter_chains_by_tail(right_chains,finger_chain_IDs)
        left_fingers_tail_chains = self.filter_chains_by_tail(left_chains,finger_chain_IDs)

        right_foot_tail_chains = self.filter_chains_by_tail(right_chains,foot_chain_IDs)
        right_foot_tail_chains.sort()
        self.rtoe_and_leg_names = right_foot_tail_chains[0]
        right_foot_tail_chains = self.filter_chains_by_max_length(right_foot_tail_chains)

        left_foot_tail_chains = self.filter_chains_by_tail(left_chains,foot_chain_IDs)
        left_foot_tail_chains.sort()
        self.ltoe_and_leg_names = left_foot_tail_chains[0]
        left_foot_tail_chains = self.filter_chains_by_max_length(left_foot_tail_chains)

        feet_tail_chains = self.filter_chains_by_tail(chains,foot_chain_IDs)

        spine_chain = self.chains_intersection(arms_tail_chains)

        head_and_spine_chains = self.chains_intersection(head_tail_chains)
        head_chain = self.chains_difference(head_and_spine_chains,spine_chain)

        r_finger_arm_spine_chain = self.chains_intersection(right_fingers_tail_chains)
        right_fingers_chain = [self.chains_difference(fingr,r_finger_arm_spine_chain) for fingr in right_fingers_tail_chains]

        l_finger_arm_spine_chain = self.chains_intersection(left_fingers_tail_chains)
        left_fingers_chain = [self.chains_difference(fingr,l_finger_arm_spine_chain) for fingr in left_fingers_tail_chains]

        r_arm_spine_chain = self.chains_intersection(right_arm_tail_chains)
        right_arm_chain = self.chains_difference(r_arm_spine_chain,spine_chain)

        l_arm_spine_chain = self.chains_intersection(left_arm_tail_chains)
        left_arm_chain = self.chains_difference(l_arm_spine_chain,spine_chain)

        r_leg_and_spine_chain = self.chains_intersection(right_foot_tail_chains)
        l_leg_and_spine_chain = self.chains_intersection(left_foot_tail_chains)

        right_leg_chain = self.chains_difference(r_leg_and_spine_chain,spine_chain)
        left_leg_chain = self.chains_difference(l_leg_and_spine_chain,spine_chain)

        right_toes_chain = [self.chains_difference(toe,r_leg_and_spine_chain) for toe in right_foot_tail_chains]
        right_toes_chain = self.filter_chains_by_max_length(right_toes_chain)

        left_toes_chain = [self.chains_difference(toe,l_leg_and_spine_chain) for toe in left_foot_tail_chains]
        left_toes_chain = self.filter_chains_by_max_length(left_toes_chain)

        pelvis_chain = self.chains_intersection(feet_tail_chains)

        r_finger0_chain = self.filter_chains_by_order(right_fingers_chain, 0)
        r_finger1_chain = self.filter_chains_by_order(right_fingers_chain, 1)
        r_finger2_chain = self.filter_chains_by_order(right_fingers_chain, 2)
        r_finger3_chain = self.filter_chains_by_order(right_fingers_chain, 3)
        r_finger4_chain = self.filter_chains_by_order(right_fingers_chain, 4)

        l_finger0_chain = self.filter_chains_by_order(left_fingers_chain, 0)
        l_finger1_chain = self.filter_chains_by_order(left_fingers_chain, 1)
        l_finger2_chain = self.filter_chains_by_order(left_fingers_chain, 2)
        l_finger3_chain = self.filter_chains_by_order(left_fingers_chain, 3)
        l_finger4_chain = self.filter_chains_by_order(left_fingers_chain, 4)

        self.spine_bones_names = spine_chain
        self.head_bones_names = head_chain
        self.rarm_bones_names = right_arm_chain
        self.larm_bones_names = left_arm_chain
        self.rleg_bones_names = right_leg_chain
        self.lleg_bones_names = left_leg_chain
        self.pelvis_bones_names = pelvis_chain

        self.rfinger0_bones_names = r_finger0_chain
        self.rfinger1_bones_names = r_finger1_chain
        self.rfinger2_bones_names = r_finger2_chain
        self.rfinger3_bones_names = r_finger3_chain
        self.rfinger4_bones_names = r_finger4_chain
        self.lfinger0_bones_names = l_finger0_chain
        self.lfinger1_bones_names = l_finger1_chain
        self.lfinger2_bones_names = l_finger2_chain
        self.lfinger3_bones_names = l_finger3_chain
        self.lfinger4_bones_names = l_finger4_chain

    def get_ending_bones(self, armat):
        found_bones = set()
        for bn in armat.data.bones:
            if len(bn.children) == 0:
                found_bones.add(bn.name)
        return found_bones


    def get_bone_by_similar_ID(self, bones_to_scan, bone_identifiers1, bone_identifiers2):
        diff_length = 100
        result = None
        if bones_to_scan:
            for bone_ID in bone_identifiers1:
                for bone_name in bones_to_scan:
                    b_name = bone_name.lower()
                    if bone_ID in b_name:
                        diff_string = b_name.replace(bone_ID,"")
                        if len(bone_identifiers2) > 0:
                            for bone_ID2 in bone_identifiers2:
                                diff_string = diff_string.replace(bone_ID2,"")
                                if len(diff_string) < diff_length:
                                    result = bone_name
                                    diff_length = len(diff_string)
                        else:
                            if len(diff_string) < diff_length:
                                diff_length = len(diff_string)
                                result = bone_name
        return result

    def find_bone(self,armat,bone_type,search_method):

        if self.knowledge_database:

            bone_knowledge = self.knowledge_database[bone_type]

            main_IDs = bone_knowledge["main_IDs"]
            children_IDs = bone_knowledge["children_IDs"]
            parent_IDs = bone_knowledge["parent_IDs"]
            side = bone_knowledge["side"]
            chain_ID =  bone_knowledge["chain_ID"]
            position_in_chain = bone_knowledge["position_in_chain"]

            if chain_ID == "spine_bones_names":
                bones_chain = self.spine_bones_names
            elif chain_ID == "rarm_bones_names":
                bones_chain = self.rarm_bones_names
            elif chain_ID == "larm_bones_names":
                bones_chain = self.larm_bones_names
            elif chain_ID == "rleg_bones_names":
                bones_chain = self.rleg_bones_names
            elif chain_ID == "lleg_bones_names":
                bones_chain = self.lleg_bones_names
            elif chain_ID == "head_bones_names":
                bones_chain = self.head_bones_names
            elif chain_ID == "pelvis_bones_names":
                bones_chain = self.pelvis_bones_names
            elif chain_ID == "rtoe_and_leg_names":
                bones_chain = self.rtoe_and_leg_names
            elif chain_ID == "ltoe_and_leg_names":
                bones_chain = self.ltoe_and_leg_names
            elif chain_ID == "rfinger0_bones_names":
                bones_chain = self.rfinger0_bones_names
            elif chain_ID == "rfinger1_bones_names":
                bones_chain = self.rfinger1_bones_names
            elif chain_ID == "rfinger2_bones_names":
                bones_chain = self.rfinger2_bones_names
            elif chain_ID == "rfinger3_bones_names":
                bones_chain = self.rfinger3_bones_names
            elif chain_ID == "rfinger4_bones_names":
                bones_chain = self.rfinger4_bones_names
            elif chain_ID == "lfinger0_bones_names":
                bones_chain = self.lfinger0_bones_names
            elif chain_ID == "lfinger1_bones_names":
                bones_chain = self.lfinger1_bones_names
            elif chain_ID == "lfinger2_bones_names":
                bones_chain = self.lfinger2_bones_names
            elif chain_ID == "lfinger3_bones_names":
                bones_chain = self.lfinger3_bones_names
            elif chain_ID == "lfinger4_bones_names":
                bones_chain = self.lfinger4_bones_names

            all_methods = ["by_exact_name", "by_chain_index","by_similar_name","by_children"]
            search_sequence = [search_method]

            for methd in all_methods:
                if methd not in search_sequence:
                    search_sequence.append(methd)

            for s_method in search_sequence:
                if s_method == "by_exact_name":
                    result = self.get_bone_by_exact_ID(bones_chain, main_IDs, side)

                    if result:
                        if result not in self.already_mapped_bones:
                            self.already_mapped_bones.append(result)
                            return result

                if s_method == "by_similar_name":
                    result = self.get_bone_by_similar_ID(bones_chain, main_IDs, side)

                    if result:
                        if result not in self.already_mapped_bones:
                            self.already_mapped_bones.append(result)
                            return result

                if s_method == "by_children":
                    result = self.get_bone_by_childr(armat, bones_chain, children_IDs)

                    if result:
                        if result not in self.already_mapped_bones:
                            self.already_mapped_bones.append(result)
                            return result

                if s_method == "by_chain_index":
                    result = self.get_bones_by_index(bones_chain,position_in_chain)

                    if result:
                        if result not in self.already_mapped_bones:
                            self.already_mapped_bones.append(result)
                            return result

            lab_logger.warning("All methods failed for {0}. No candidates found in: {1}, or the candidate found is already mapped to another bone".format(bone_type, bones_chain))
            return None
        else:
            return None


    def bone_parent_name(self,armat,b_name):
        x_bone = self.get_bone(armat,b_name)
        if x_bone:
            if x_bone.parent:
                return x_bone.parent.name
        return None

    def get_bone(self,armat,b_name,b_type = "TARGET"):
        if armat:
            if b_type == "TARGET":
                if b_name:
                    if b_name in armat.pose.bones:
                        return armat.pose.bones[b_name]
            if b_type == "SOURCE":
                b_name = self.mapped_name(b_name)
                if b_name:
                    if b_name in armat.pose.bones:
                        return armat.pose.bones[b_name]
        return None

    def get_edit_bone(self,armat,b_name,b_type = "TARGET"):
        if bpy.context.object.mode == "EDIT":
            if b_type == "TARGET":
                if b_name:
                    if b_name in armat.data.edit_bones:
                        return armat.data.edit_bones[b_name]
                    else:
                        lab_logger.warning("{0} not found in edit mode of target armature {1}".format(b_name,armat))
            if b_type == "SOURCE":
                b_name = self.mapped_name(b_name)
                if b_name:
                    if b_name in armat.data.edit_bones:
                        return armat.data.edit_bones[b_name]
                    else:
                        lab_logger.warning("{0} not found in edit mode of source armature {1}".format(b_name,armat))
        else:
            lab_logger.warning("Warning: Can't get the edit bone of {0} because the mode is {1}".format(bpy.context.scene.objects.active,bpy.context.object.mode))
        return None


    def mapped_name(self, b_name):
        if b_name in self.skeleton_mapped:
            return self.skeleton_mapped[b_name]
        else:
            return None

    def map_bone(self,armat,b_name,b_type,s_method):
        mapped_name = self.find_bone(armat,b_type,s_method)
        if mapped_name != None:
            self.skeleton_mapped[b_name] = mapped_name
        else:
            self.skeleton_mapped[b_name] = None

    def map_by_direct_parent(self,armat,childr_name,map_name):
        childr_bone_name = self.mapped_name(childr_name)

        if childr_bone_name:
            parent_bone_name = self.bone_parent_name(armat,childr_bone_name)
            if parent_bone_name:
                if parent_bone_name not in self.already_mapped_bones:
                    self.skeleton_mapped[map_name] = parent_bone_name
                    self.already_mapped_bones.append(parent_bone_name)
                return

        lab_logger.warning("Error in mapping {1} as direct parent of {0}".format(childr_name,map_name))

    def map_main_bones(self,armat):

        ending_bones = self.get_ending_bones(armat)
        chains = self.get_bone_chains(armat,ending_bones)

        self.identify_bone_chains(chains,False)
        self.map_bone(armat,"clavicle_L","LCLAVICLE","by_exact_name")
        self.map_bone(armat,"clavicle_R","RCLAVICLE","by_exact_name")
        self.map_bone(armat,"head","HEAD","by_exact_name")
        self.map_bone(armat,"lowerarm_R","RFOREARM","by_exact_name")
        self.map_bone(armat,"lowerarm_L","LFOREARM","by_exact_name")
        self.map_bone(armat,"upperarm_R","RUPPERARM","by_children")
        self.map_bone(armat,"upperarm_L","LUPPERARM","by_children")
        self.map_bone(armat,"hand_R","RHAND","by_exact_name")
        self.map_bone(armat,"hand_L","LHAND","by_exact_name")
        self.map_bone(armat,"calf_R","RCALF","by_exact_name")
        self.map_bone(armat,"calf_L","LCALF","by_exact_name")
        self.map_bone(armat,"foot_R","RFOOT","by_exact_name")
        self.map_bone(armat,"foot_L","LFOOT","by_exact_name")
        self.map_bone(armat,"toes_R","RTOE","by_exact_name")
        self.map_bone(armat,"toes_L","LTOE","by_exact_name")
        self.map_bone(armat,"pelvis","PELVIS","by_exact_name")
        self.map_bone(armat,"spine03","CHEST","by_chain_index")

        self.map_by_direct_parent(armat,"head","neck")
        self.map_by_direct_parent(armat,"spine03","spine02")
        self.map_by_direct_parent(armat,"spine02","spine01")
        self.map_by_direct_parent(armat,"calf_R","thigh_R")
        self.map_by_direct_parent(armat,"calf_L","thigh_L")

        self.map_bone(armat,"thumb03_R","RTHUMB03","by_chain_index")
        self.map_bone(armat,"thumb02_R","RTHUMB02","by_chain_index")
        self.map_bone(armat,"thumb01_R","RTHUMB01","by_chain_index")
        self.map_bone(armat,"index03_R","RINDEX03","by_chain_index")
        self.map_bone(armat,"index02_R","RINDEX02","by_chain_index")
        self.map_bone(armat,"index01_R","RINDEX01","by_chain_index")
        self.map_bone(armat,"middle03_R","RMIDDLE03","by_chain_index")
        self.map_bone(armat,"middle02_R","RMIDDLE02","by_chain_index")
        self.map_bone(armat,"middle01_R","RMIDDLE01","by_chain_index")
        self.map_bone(armat,"ring03_R","RRING03","by_chain_index")
        self.map_bone(armat,"ring02_R","RRING02","by_chain_index")
        self.map_bone(armat,"ring01_R","RRING01","by_chain_index")
        self.map_bone(armat,"pinky03_R","RPINKY03","by_chain_index")
        self.map_bone(armat,"pinky02_R","RPINKY02","by_chain_index")
        self.map_bone(armat,"pinky01_R","RPINKY01","by_chain_index")
        self.map_bone(armat,"thumb03_L","LTHUMB03","by_chain_index")
        self.map_bone(armat,"thumb02_L","LTHUMB02","by_chain_index")
        self.map_bone(armat,"thumb01_L","LTHUMB01","by_chain_index")
        self.map_bone(armat,"index03_L","LINDEX03","by_chain_index")
        self.map_bone(armat,"index02_L","LINDEX02","by_chain_index")
        self.map_bone(armat,"index01_L","LINDEX01","by_chain_index")
        self.map_bone(armat,"middle03_L","LMIDDLE03","by_chain_index")
        self.map_bone(armat,"middle02_L","LMIDDLE02","by_chain_index")
        self.map_bone(armat,"middle01_L","LMIDDLE01","by_chain_index")
        self.map_bone(armat,"ring03_L","LRING03","by_chain_index")
        self.map_bone(armat,"ring02_L","LRING02","by_chain_index")
        self.map_bone(armat,"ring01_L","LRING01","by_chain_index")
        self.map_bone(armat,"pinky03_L","LPINKY03","by_chain_index")
        self.map_bone(armat,"pinky02_L","LPINKY02","by_chain_index")
        self.map_bone(armat,"pinky01_L","LPINKY01","by_chain_index")

        head_bone_name = self.mapped_name("head")
        neck_bone_name = self.bone_parent_name(armat,head_bone_name)
        self.skeleton_mapped["neck"] = neck_bone_name


    def bake_animation(self,target_armat,source_armat):

        f_range = [0,bpy.context.scene.frame_current]
        algorithms.select_and_change_mode(target_armat,'POSE')
        if source_armat.animation_data:
            source_action = source_armat.animation_data.action
            f_range = source_action.frame_range

        bpy.ops.nla.bake(frame_start=f_range[0], frame_end=f_range[1],only_selected=False, visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})


    def reset_bones_rotations(self,armat):
        reset_val =  mathutils.Quaternion((1.0, 0.0, 0.0, 0.0))
        for p_bone in armat.pose.bones:
            if p_bone.rotation_mode == 'QUATERNION':
                reset_val =  mathutils.Quaternion((1.0, 0.0, 0.0, 0.0))
                p_bone.rotation_quaternion = reset_val
            elif p_bone.rotation_mode == 'AXIS_ANGLE':
                reset_val =  mathutils.Vector((0.0, 0.0, 1.0, 0.0))
                p_bone.rotation_axis_angle = reset_val
            else:
                reset_val =  mathutils.Euler((0.0, 0.0, 0.0))
                p_bone.rotation_euler = reset_val


    def calculate_skeleton_vectors(self,armat,armat_type,rot_type):


        algorithms.select_and_change_mode(armat,"EDIT")
        head_bone = self.get_edit_bone(armat,"head",armat_type)
        pelvis_bone = self.get_edit_bone(armat,"pelvis",armat_type)
        hand_bone1 = self.get_edit_bone(armat,"hand_R",armat_type)
        hand_bone2 = self.get_edit_bone(armat,"hand_L",armat_type)
        vect1 = None
        vect2 = None

        if head_bone != None:
            if pelvis_bone != None:
                if hand_bone1 != None:
                    if hand_bone2 != None:

                        vect1 = head_bone.head-pelvis_bone.head
                        vect2 = hand_bone2.head-hand_bone1.head

        algorithms.select_and_change_mode(armat,"POSE")

        if vect1 != None and vect2 != None:
            if rot_type == "ALIGN_SPINE":
                return vect1.normalized()
            if rot_type == "ALIGN_SHOULDERS":
                return vect2.normalized()

        return None


    def define_angle_direction(self,vect1,vect2,rot_axis,angle):

        angle1 = mathutils.Quaternion(rot_axis, angle)
        angle2 = mathutils.Quaternion(rot_axis, -angle)

        v_rot1 = vect1.copy()
        v_rot2 = vect1.copy()

        v_rot1.rotate(angle1)
        v_rot2.rotate(angle2)

        v_dot1 = v_rot1.dot(vect2)
        v_dot2 = v_rot2.dot(vect2)

        if v_dot1 >= 0 and v_dot1 >= v_dot2:
            return angle1

        if v_dot2 >= 0 and v_dot2 >= v_dot1:
            return angle2

        lab_logger.warning("Problem with armature angles",v_dot1,v_dot2)
        return mathutils.Quaternion((0.0, 0.0, 1.0), 0)


    def align_skeleton(self,target_armat,source_armat):
        self.calculate_skeleton_rotations(target_armat,source_armat,"ALIGN_SPINE")
        self.calculate_skeleton_rotations(target_armat,source_armat,"ALIGN_SHOULDERS")


    def calculate_skeleton_rotations(self,target_armat,source_armat,rot_type):

        algorithms.select_and_change_mode(source_armat,"OBJECT")
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        source_vector = self.calculate_skeleton_vectors(source_armat,'SOURCE',rot_type)
        if source_vector:
            if rot_type == "ALIGN_SPINE":
                target_vector = mathutils.Vector((0.0, 0.0, 1.0))
            if rot_type == "ALIGN_SHOULDERS":
                target_vector = self.calculate_skeleton_vectors(target_armat,'TARGET',rot_type)
                source_vector.z = 0.0

            if target_vector != None:
                angle = source_vector.angle(target_vector)
                rot_axis = source_vector.cross(target_vector)
                rot = self.define_angle_direction(source_vector,target_vector,rot_axis,angle)
                algorithms.select_and_change_mode(source_armat,"OBJECT")
                self.rotate_skeleton(source_armat,rot)
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            else:
                lab_logger.warning("Cannot calculate the target vector for armature alignment")
        else:
            lab_logger.warning("Cannot calculate the source vector for armature alignment")


    def rotate_skeleton(self,armat,rot_quat):
        armat.rotation_mode = 'QUATERNION'
        armat.rotation_quaternion = rot_quat


    def use_animation_pelvis(self,target_armat,source_armat):

        if target_armat != None:
            if source_armat != None:
                v1 = None
                v2 = None

                armat_prop = self.get_armature_proportion(target_armat,source_armat)
                algorithms.select_and_change_mode(source_armat,'EDIT')
                source_pelvis = self.get_edit_bone(source_armat,"pelvis","SOURCE")
                r_thigh_bone = self.get_edit_bone(source_armat,"thigh_R","SOURCE")
                l_thigh_bone = self.get_edit_bone(source_armat,"thigh_L","SOURCE")

                if source_pelvis != None:
                    if r_thigh_bone != None:
                        if l_thigh_bone != None:

                            p1 =  (r_thigh_bone.head + l_thigh_bone.head)*0.5
                            p2 =  source_pelvis.head
                            p3 =  source_pelvis.tail
                            v1 = armat_prop*(p2-p1)
                            v2 = armat_prop*(p3-p2)

                algorithms.select_and_change_mode(source_armat,'POSE')

                if v1 != None:
                    if v2 != None:
                        algorithms.select_and_change_mode(target_armat,'EDIT')
                        target_pelvis = self.get_edit_bone(target_armat,"pelvis","TARGET")
                        r_thigh_bone = self.get_edit_bone(target_armat,"thigh_R","TARGET")
                        l_thigh_bone = self.get_edit_bone(target_armat,"thigh_L","TARGET")

                        if target_pelvis != None:
                            if r_thigh_bone != None:
                                if l_thigh_bone != None:

                                    p1a =  (r_thigh_bone.head + l_thigh_bone.head)*0.5
                                    target_pelvis.head = p1a+v1
                                    target_pelvis.tail = target_pelvis.head + v2

                        algorithms.select_and_change_mode(target_armat,'POSE')



    def armature_height(self,armat,armat_type):

        if armat:
            algorithms.force_visible_object(armat)
            algorithms.select_and_change_mode(armat,'EDIT')

            r_foot_bone = self.get_edit_bone(armat,"foot_R",armat_type)
            l_foot_bone = self.get_edit_bone(armat,"foot_L",armat_type)

            r_clavicle_bone = self.get_edit_bone(armat,"clavicle_R",armat_type)
            l_clavicle_bone = self.get_edit_bone(armat,"clavicle_L",armat_type)

            upper_point = (l_clavicle_bone.head + r_clavicle_bone.head)*0.5
            lower_point = (l_foot_bone.head + r_foot_bone.head)*0.5

            height = upper_point-lower_point
            algorithms.select_and_change_mode(armat,'POSE')

            return height.length
        else:
            lab_logger.warning("Cannot found the source armature for height calculation")


    def get_source_armature(self):
        armat = self.get_armature()
        if armat != None:
            if 'animation_source' in armat.keys():
                source_armat_name = armat['animation_source']
                if source_armat_name in bpy.data.objects:
                    return bpy.data.objects[source_armat_name]
        return None



    def remove_copy_rotations(self):
        armat = self.get_armature()
        for b in armat.pose.bones:
            if len(b.constraints) > 0:
                for cstr in b.constraints:
                    if "mbastlab_" in cstr.name:
                        b.constraints.remove(cstr)


    def add_copy_rotations(self,target_armat,source_armat,bones_to_rotate, transf_space="WORLD"):
        for b in target_armat.pose.bones:
            if b.name in self.skeleton_mapped:
                if b.name in bones_to_rotate:
                    if self.skeleton_mapped[b.name] != None:
                        if "mbastlab_rot" not in b.constraints:
                            cstr = b.constraints.new('COPY_ROTATION')
                            cstr.target = source_armat
                            cstr.subtarget =  self.skeleton_mapped[b.name]
                            cstr.target_space = transf_space
                            cstr.owner_space = transf_space
                            cstr.name = "mbastlab_rot"


    def add_copy_location(self,target_armat,source_armat,bones_to_move, transf_space="WORLD"):
        for b in target_armat.pose.bones:
            if b.name in self.skeleton_mapped:
                if b.name in bones_to_move:
                    if "mbastlab_loc" not in b.constraints:
                        cstr = b.constraints.new('COPY_LOCATION')
                        cstr.target = source_armat
                        cstr.subtarget =  self.skeleton_mapped[b.name]
                        cstr.target_space = transf_space
                        cstr.owner_space = transf_space
                        cstr.name = "mbastlab_loc"

    def add_bone_modifiers(self,target_armat, source_armat):
        for b in target_armat.pose.bones:
            if b.name not in self.bones_to_rotate_world:
                if b.name not in self.bones_to_exclude:
                    self.bones_to_rotate_local.append(b.name)

        self.add_copy_rotations(target_armat,source_armat,self.bones_to_rotate_world)
        self.add_copy_rotations(target_armat,source_armat,self.bones_to_rotate_local,'LOCAL')
        self.add_copy_location(target_armat,source_armat,["pelvis"],'WORLD')


    def scale_armat(self,target_armat,source_armat):
        scale = self.get_armature_proportion(target_armat,source_armat)
        source_armat.scale = [scale,scale,scale]


    def clear_action(self):
        armat = self.get_armature()
        if armat:
            if armat.animation_data:
                action = armat.animation_data.action
                if action:
                    bpy.data.actions.remove(action,do_unlink=True)

    def get_armature_proportion(self,target_armat,source_armat):
        t_height = self.armature_height(target_armat,'TARGET')
        s_height = self.armature_height(source_armat,'SOURCE')
        if s_height != 0:
            armat_prop = t_height/s_height
        else:
            armat_prop = 1
        return armat_prop


