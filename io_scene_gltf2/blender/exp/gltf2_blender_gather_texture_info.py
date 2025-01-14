# Copyright 2018-2019 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bpy
import typing
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.com.gltf2_io_extensions import Extension


@cached
def gather_texture_info(blender_shader_sockets_or_texture_slots: typing.Union[
    typing.Tuple[bpy.types.NodeSocket], typing.Tuple[bpy.types.Texture]],
        export_settings):
    if not __filter_texture_info(blender_shader_sockets_or_texture_slots, export_settings):
        return None

    texture_info = gltf2_io.TextureInfo(
        extensions=__gather_extensions(blender_shader_sockets_or_texture_slots, export_settings),
        extras=__gather_extras(blender_shader_sockets_or_texture_slots, export_settings),
        index=__gather_index(blender_shader_sockets_or_texture_slots, export_settings),
        tex_coord=__gather_tex_coord(blender_shader_sockets_or_texture_slots, export_settings)
    )

    if texture_info.index is None:
        return None

    return texture_info


def __filter_texture_info(blender_shader_sockets_or_texture_slots, export_settings):
    if not blender_shader_sockets_or_texture_slots:
        return False
    if not all([elem is not None for elem in blender_shader_sockets_or_texture_slots]):
        return False
    if isinstance(blender_shader_sockets_or_texture_slots[0], bpy.types.NodeSocket):
        if any([__get_tex_from_socket(socket) is None for socket in blender_shader_sockets_or_texture_slots]):
            # sockets do not lead to a texture --> discard
            return False

        resolution = __get_tex_from_socket(blender_shader_sockets_or_texture_slots[0]).shader_node.image.size
        if any(any(a != b for a, b in zip(__get_tex_from_socket(elem).shader_node.image.size, resolution))
               for elem in blender_shader_sockets_or_texture_slots):
            def format_image(image_node):
                return "{} ({}x{})".format(image_node.image.name, image_node.image.size[0], image_node.image.size[1])

            images = [format_image(__get_tex_from_socket(elem).shader_node) for elem in
                      blender_shader_sockets_or_texture_slots]

            print_console("ERROR", "Image sizes do not match. In order to be merged into one image file, "
                                   "images need to be of the same size. Images: {}".format(images))
            return False

    return True


def __gather_extensions(blender_shader_sockets_or_texture_slots, export_settings):
    if not hasattr(blender_shader_sockets_or_texture_slots[0], 'links'):
        return None

    texture_node = blender_shader_sockets_or_texture_slots[0].links[0].from_node
    texture_transform = gltf2_blender_get.get_texture_transform_from_texture_node(texture_node)
    if texture_transform is None:
        return None

    extension = Extension("KHR_texture_transform", texture_transform)
    return {"KHR_texture_transform": extension}


def __gather_extras(blender_shader_sockets_or_texture_slots, export_settings):
    return None


def __gather_index(blender_shader_sockets_or_texture_slots, export_settings):
    # We just put the actual shader into the 'index' member
    return gltf2_blender_gather_texture.gather_texture(blender_shader_sockets_or_texture_slots, export_settings)


def __gather_tex_coord(blender_shader_sockets_or_texture_slots, export_settings):
    if isinstance(blender_shader_sockets_or_texture_slots[0], bpy.types.NodeSocket):
        blender_shader_node = __get_tex_from_socket(blender_shader_sockets_or_texture_slots[0]).shader_node
        if len(blender_shader_node.inputs['Vector'].links) == 0:
            return 0

        input_node = blender_shader_node.inputs['Vector'].links[0].from_node

        if isinstance(input_node, bpy.types.ShaderNodeMapping):

            if len(input_node.inputs['Vector'].links) == 0:
                return 0

            input_node = input_node.inputs['Vector'].links[0].from_node

        if not isinstance(input_node, bpy.types.ShaderNodeUVMap):
            return 0

        if input_node.uv_map == '':
            return 0

        # Try to gather map index.
        for blender_mesh in bpy.data.meshes:
            texCoordIndex = blender_mesh.uv_layers.find(input_node.uv_map)
            if texCoordIndex >= 0:
                return texCoordIndex

        return 0
    elif isinstance(blender_shader_sockets_or_texture_slots[0], bpy.types.MaterialTextureSlot):
        # TODO: implement for texture slots
        return 0
    else:
        raise NotImplementedError()


def __get_tex_from_socket(socket):
    result = gltf2_blender_search_node_tree.from_socket(
        socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    if result[0].shader_node.image is None:
        return None
    return result[0]

