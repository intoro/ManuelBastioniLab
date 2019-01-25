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

from . import algorithms
import os, json, time
import mathutils
import logging
import bpy
lab_logger = logging.getLogger('manuelbastionilab_logger')


def get_boundary_verts(blender_object):
    obj = blender_object
    polygons_dict = {}
    for polyg in obj.data.polygons:
        for i in polyg.vertices:
            if str(i) not in polygons_dict:
                indices = [n for n in polyg.vertices if n != i]
                polygons_dict[str(i)] = indices
            else:
                for vert_id in polyg.vertices:
                    if vert_id != i and vert_id not in polygons_dict[str(i)]:
                        polygons_dict[str(i)].append(vert_id)

    return polygons_dict

def kdtree_with_basedata(body_obj, base_body_vertices):
    research_tree = mathutils.kdtree.KDTree(len(body_obj.data.polygons))
    for face in body_obj.data.polygons:
        verts_coords = []
        for v_idx in face.vertices:
            verts_coords.append(base_body_vertices[v_idx])
        bcenter = algorithms.average_center(verts_coords)
        research_tree.insert(bcenter, face.index)
    research_tree.balance()
    return research_tree

def get_shapekey(obj, shapekey_name):
    shapekey_data = None
    if  obj.data.shape_keys:
        if shapekey_name in obj.data.shape_keys.key_blocks:
            shapekey_data = obj.data.shape_keys.key_blocks[shapekey_name]
    if shapekey_data == None:
        lab_logger.warning("{0} has not shape keys {1}".format(obj.name,shapekey_name))
    return shapekey_data


def new_shapekey(obj, shapekey_name):

    if shapekey_name in obj.data.shape_keys.key_blocks:
        shapekey_data =  obj.data.shape_keys.key_blocks[shapekey_name]
    else:
        shapekey_data = obj.shape_key_add(name=shapekey_name, from_mix=False)
    shapekey_data.slider_min = 0
    shapekey_data.slider_max = 1.0
    shapekey_data.value = 1.0
    obj.use_shape_key_edit_mode = True
    return shapekey_data



def calculate_finishing_morph(blender_object, shapekey_name = "Fitted", threshold=0.2):

    shape_to_finish = get_shapekey(blender_object, shapekey_name)
    if shape_to_finish:
        boundary_verts = get_boundary_verts(blender_object)

        for polyg in blender_object.data.polygons:
            polyg_base_verts = []
            polyg_current_verts = []
            for vert_index in polyg.vertices:
                polyg_base_verts.append(blender_object.data.vertices[vert_index].co)
                polyg_current_verts.append(shape_to_finish.data[vert_index].co)
            base_factors = algorithms.polygon_forma(polyg_base_verts)
            current_factors = algorithms.polygon_forma(polyg_current_verts)

            deformations = []
            for idx in range(len(current_factors)):
                deformations.append(abs(current_factors[idx]-base_factors[idx]))
            max_deform = max(deformations)/2.0

            if max_deform > threshold:
                for idx in polyg.vertices:
                    b_verts = boundary_verts[str(idx)]
                    average = mathutils.Vector((0, 0, 0))
                    for vidx in b_verts:
                        coords = shape_to_finish.data[vidx].co
                        average += coords
                    average = average/len(b_verts)
                    corrected_position = shape_to_finish.data[idx].co*(1.0 - max_deform) + average*max_deform
                    shape_to_finish.data[idx].co = corrected_position # + fitted_forma.vertices[idx].normal*difference.length
                    blender_object.data.vertices[idx].select = True

def calculate_normal():
    p1 = base_vertices[body_base_polygon.vertices[0]]
    p2 = base_vertices[body_base_polygon.vertices[1]]
    p3 = base_vertices[body_base_polygon.vertices[2]]
    if len(body_base_polygon.vertices) == 4:
        p_extra = base_vertices[body_base_polygon.vertices[3]]
        body_base_plane_norm = mathutils.geometry.normal(p1,p2,p3,p_extra)
    else:
        body_base_plane_norm = mathutils.geometry.normal(p1,p2,p3)



def proxy_collision(body_obj, proxy_obj, base_body_vertices, min_distance = 0.0025, correction_factor = 1):

    body_mesh = body_obj.to_mesh(bpy.context.scene, True, 'PREVIEW')
    proxy_mesh =proxy_obj.to_mesh(bpy.context.scene, True, 'PREVIEW')
    shape_to_correct = get_shapekey(proxy_obj, "Fitted")

    body_tree = kdtree_with_basedata(body_obj, base_body_vertices)

    for proxy_polygon in proxy_mesh.polygons:
        rest_proxy_polygon = proxy_obj.data.polygons[proxy_polygon.index] #the proxy in rest pose
        closer_body_polygon_data = body_tree.find(rest_proxy_polygon.center)
        idx = closer_body_polygon_data[1]
        closer_body_polygon = body_mesh.polygons[idx]
        distance = mathutils.geometry.distance_point_to_plane(proxy_polygon.center, closer_body_polygon.center, closer_body_polygon.normal)

        if distance < 0:
            for v_index in proxy_polygon.vertices:
                shape_to_correct.data[v_index].co += -proxy_polygon.normal*distance*correction_factor #+ proxy_polygon.normal*min_distance
    if bpy.app.version > (2,77,0):
        bpy.data.meshes.remove(proxy_mesh, do_unlink=True)
        bpy.data.meshes.remove(body_mesh, do_unlink=True)
    else:
        bpy.data.meshes.remove(proxy_mesh)
        bpy.data.meshes.remove(body_mesh)



def reset_proxy_object(proxy):
    if proxy.data.shape_keys:
        for sk in proxy.data.shape_keys.key_blocks:
            if sk != proxy.data.shape_keys.reference_key:
                sk.value = 0
                proxy.shape_key_remove(sk)

        proxy.shape_key_remove(proxy.data.shape_keys.reference_key)

def calibrate_proxy_object(proxy):

    reset_proxy_object(proxy)
    proxy.shape_key_add(name="Basis", from_mix=False)



def fit_proxy_object(body, proxy, base_vertices):

    lab_logger.info("Fitting proxy {0}".format(proxy.name))
    disable_modifiers(body)

    if not proxy.data.shape_keys:
        lab_logger.warning("Proxy {0} has not shape keys base data".format(proxy.name))
        return None


    current_body_mesh = body.to_mesh(bpy.context.scene, True, 'PREVIEW')
    lab_logger.info("Proxyengine: number of polygons for base original mesh: {0}".format(len(body.data.polygons)))
    lab_logger.info("Proxyengine: number of polygons for morphed mesh: {0}".format(len(current_body_mesh.polygons)))

    if len(body.data.polygons) == len(current_body_mesh.polygons):

        current_proxy_mesh = new_shapekey(proxy,"Fitted")
        body_tree = kdtree_with_basedata(body, base_vertices)

        for proxy_vert_index in range(len(proxy.data.vertices)):
            proxy_base_vert = proxy.data.vertices[proxy_vert_index] #data always refers to basis form
            body_closer_polygons = body_tree.find_n(proxy_base_vert.co,25) #search in base body

            for data in body_closer_polygons:
                body_polygon_index = data[1]
                body_base_polygon = body.data.polygons[data[1]]

                #body_base_polygon.normal cannot be used because affected by the current morph
                p1 = base_vertices[body_base_polygon.vertices[0]]
                p2 = base_vertices[body_base_polygon.vertices[1]]
                p3 = base_vertices[body_base_polygon.vertices[2]]
                if len(body_base_polygon.vertices) == 4:
                    p_extra = base_vertices[body_base_polygon.vertices[3]]
                    body_base_plane_norm = mathutils.geometry.normal(p1,p2,p3,p_extra)
                else:
                    body_base_plane_norm = mathutils.geometry.normal(p1,p2,p3)

                if body_base_plane_norm.dot(proxy_base_vert.normal) > 0:
                    break

            line_a = proxy_base_vert.co
            line_b = proxy_base_vert.co + body_base_plane_norm

            distance = mathutils.geometry.distance_point_to_plane(proxy_base_vert.co, p1, body_base_plane_norm)
            base_intersection = mathutils.geometry.intersect_line_plane(line_a, line_b, p1, body_base_plane_norm)

            proxy_current_vert = current_proxy_mesh.data[proxy_vert_index]
            body_current_polygon = current_body_mesh.polygons[body_polygon_index]

            p4 = current_body_mesh.vertices[body_current_polygon.vertices[0]].co
            p5 = current_body_mesh.vertices[body_current_polygon.vertices[1]].co
            p6 = current_body_mesh.vertices[body_current_polygon.vertices[2]].co

            current_intersection = mathutils.geometry.barycentric_transform(base_intersection,p1,p2,p3,p4,p5,p6)
            delta_vector = body_current_polygon.normal * distance
            proxy_current_vert.co = current_intersection + delta_vector
    else:
        lab_logger.warning("The number of polygons in the current mesh is different from the number of polygons in the lab base mesh. Are you using a special modifier?")



    if bpy.app.version > (2,77,0):
        bpy.data.meshes.remove(current_body_mesh, do_unlink=True)
    else:
        bpy.data.meshes.remove(current_body_mesh)



def prepare_proxy_for_calibration(human_obj):
    proxy_obj = bpy.context.active_object

    if proxy_obj.type != 'MESH':
        proxy_status = "{0} cannot be used as proxy mesh".format(proxy_obj.name)
        lab_logger.warning(proxy_status)
        return proxy_status

    disable_modifiers(human_obj)
    move_proxy_origin_to_human_origin(human_obj)
    scale_proxy_to_human(human_obj)



def validate_proxy_select(human_obj, proxy_obj, human_label):

    if proxy_obj == human_obj:
        proxy_status = "Please select the proxy mesh"        
        return proxy_status

    if proxy_obj.type != 'MESH':
        proxy_status = "{0} cannot be used as proxy mesh".format(proxy_obj.name)        
        return proxy_status

    if 'proxy_ID' in proxy_obj.keys():
        prx_id = getattr(proxy_obj, 'proxy_ID')
        if prx_id == human_label:
            return "IS_PROXY"
        elif prx_id != "":
            return "Proxy calibrated for: {0}".format(prx_id)
        else:
            return "Proxy not calibrated yet"
    else:
        return "Proxy not calibrated yet"


def move_proxy_origin_to_human_origin(human_obj):
    scn = bpy.context.scene
    proxy_obj = bpy.context.active_object

    if proxy_obj.location != human_obj.location:
        scn.cursor_location = human_obj.location
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        lab_logger.info("Origin of {0} moved to origin of {1}".format(proxy_obj.name,human_obj.name))

def scale_proxy_to_human(human_obj):
    proxy_obj = bpy.context.active_object
    if proxy_obj.scale != human_obj.scale:
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        lab_logger.info("Applied transformation to {0}".format(proxy_obj.name))

def disable_modifiers(human_obj):
    proxy_obj = bpy.context.active_object

    for modf in proxy_obj.modifiers:
        if modf.type == 'ARMATURE':
            modf.show_viewport = False
            modf.show_render = False
            modf.show_in_editmode = False
            modf.show_on_cage = False
            lab_logger.info("Armature can create unpredictable results. The lab disabled it during the fit proxy to in {0}".format(proxy_obj.name))

    for modf in human_obj.modifiers:
        if modf.type == 'SUBSURF':
            modf.show_viewport = False
            modf.show_render = False
            modf.show_in_editmode = False
            modf.show_on_cage = False
            lab_logger.info("Subdivision surface can create unpredictable results. The lab disabled it during the fit proxy to in {0}".format(proxy_obj.name))

    for modf in human_obj.modifiers:
        if modf.type == 'MASK':
            modf.show_viewport = False
            modf.show_render = False
            modf.show_in_editmode = False
            modf.show_on_cage = False
            lab_logger.info("Mask can create unpredictable results. The lab disabled it during the fit proxy to in {0}".format(proxy_obj.name))



