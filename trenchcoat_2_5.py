# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#  Source code of chedap's Blender MAP Exporter: https://github.com/c-d-a/io_export_qmap
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Trenchcoat",
    "author": "chedap, uzugijin",
    "version": (2, 5),
    "blender": (4, 5, 0),
    "location": "3D View > Sidebar > Tool > Trenchcoat",
    "description": "Build with convex meshes and export scene to idTech map format",
    "category": "Import-Export"
}

global_list_of_things = []

import bpy, bmesh, math, time
from mathutils import Vector, Matrix
from numpy.linalg import solve
from numpy import format_float_positional as fformat
from bpy_extras.io_utils import ExportHelper
from bpy.props import *

class ExportQuakeMap(bpy.types.Operator, ExportHelper):
    bl_idname = 'export.map'
    bl_label = bl_info['name']
    bl_description = bl_info['description']
    bl_options = {'UNDO', 'PRESET'}
    filename_ext = ".map"
    filter_glob: StringProperty(default="*.map", options={'HIDDEN'})

    option_sel: BoolProperty(name="Selection Only",
        default=False, description="Only export selected objects, otherwise the full scene")
    option_depth: FloatProperty(name="Depth",
        default=2.0, description="Offset for extrusion, pyramid apex and terrain bottom. When using a larger grid, make sure to increase this as well")
    option_fp: IntProperty(name="Precision", min=0, soft_max=17,
        default=5, description="Number of decimal places")
    option_skip: StringProperty(name="Material",
        default="common/caulk", description="Generic Material")

    angle_keywords = {
    'left': '0 270 0',
    'right': '0 90 0', 
    'up': '270 0 0',
    'down': '90 0 0',
    'forward': '0 0 0',
    'backward': '0 180 0',
    'north': '0 0 0',
    'south': '0 180 0',
    'east': '0 90 0',
    'west': '0 270 0',
    'front': '0 0 0',
    'back': '0 180 0',
    '-y': '0 270 0',
    '+y': '0 90 0',
    'y': '0 90 0',
    '+z': '270 0 0',
    'z': '270 0 0',
    '-z': '90 0 0',
    '+x': '0 0 0',
    'x': '0 0 0',
    '-x': '0 180 0',
    }

    def draw(self, context):
        o = "option_"
        #self.layout.separator()
        spl = self.layout.row().split(factor=0.5)
        col = spl.column()
        for p in [o+"sel"]: col.prop(self, p)
        #self.layout.separator()
        spl = self.layout.row().split(factor=0.5)
        col = spl.column()
        col = spl.column()
        #self.layout.separator()
        self.layout.label(text="Coordinates:", icon='MESH_DATA')
        spl = self.layout.row().split(factor=0.5)
        col = spl.column()
        for p in [o+"depth"]: col.prop(self, p)
        col = spl.column()
        #self.layout.separator()
        spl = self.layout.row().split(factor=0.5)
        col = spl.column()
        #self.layout.separator()
        col = self.layout.column()
        col.prop(self, o+"skip", text="Material")

    def process_angle_value(self, angle_value):
        """Process angle value, converting keywords to actual angle strings"""
        if isinstance(angle_value, str):
            normalized_value = angle_value.lower().strip()
            if normalized_value in self.angle_keywords:
                return self.angle_keywords[normalized_value]
        return angle_value

    def entname(self, ent):
        tname = ent.name.rstrip('0123456789')
        tname = tname[:-1] if tname[-1] in ('.',' ') else ent.name
        name = '}\n// entity '+ ent.name + '\n{\n"classname" "' + tname + '"\n'        
        return name

    def gridsnap(self, vector):
        grid = 0
        if grid:
            return [round(co/grid)*grid for co in vector]
        else:
            return vector
            
    def printvec(self, vector, z):
        fstring = []
        if z != 0:
            vector[2] += z
        else:
            pass
        for co in vector:
            #print(co)
            fstring.append(fformat(co, precision=self.option_fp, trim='-'))
        return ' '.join(fstring)
    
    def get_object_angles_string(self, obj):
        if obj.rotation_mode == 'QUATERNION':
            euler_rot = obj.rotation_quaternion.to_euler('XYZ')
            obj_rot = euler_rot
        else:
            obj_rot = obj.rotation_euler

        x_deg = math.degrees(obj_rot.x)
        y_deg = math.degrees(obj_rot.y)
        z_deg = math.degrees(obj_rot.z)

        x_deg = round(x_deg) % 360
        y_deg = round(y_deg) % 360
        z_deg = round(z_deg) % 360

        return f"{y_deg} {z_deg} {x_deg}"

    def brushplane(self, face):
        planestring = ""
        for vert in reversed(face.verts[0:3]):
            planestring += f'( {self.printvec(vert.co, 0)} ) '
        return planestring

    def faceflags(self, obj):
        col = obj.users_collection[0]
        detail_flags = [".detail", "-detail", "_detail", "/detail"]
        if any(prefix in obj.name.lower() for prefix in detail_flags) or any(prefix in col.name.lower() for prefix in detail_flags) or col.name.lower() == "detail":
        #if ('_detail' in obj.name) or ('_detail' in col.name):
            return f" {1<<27} 0 0\n"
        else:
            return "\n"

    def texdata(self, face, mesh, obj, orig_obj):
        col = orig_obj.users_collection[0]
        common_flags = [".common/", "-common/", "_common/", "/common/"]
        mat = None
        width = height = 64

        # Get material and texture info
        if obj.material_slots:
            mat = obj.material_slots[face.material_index].material
        if mat:
            if mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        if node.image and node.image.has_data:
                            width, height = node.image.size
                            break
            texstring = mat.name.replace(" ", "_")
            if '.' in texstring and texstring.split('.')[-1].isdigit():
                texstring = texstring.rsplit('.', 1)[0]
        else:
            texstring = None
            for name in [obj.name.lower(), col.name.lower()]:
                for flag in common_flags:
                    if flag in name:
                        idx = name.find(flag) + len(flag)
                        texture_name = name[idx:]
                        if '/' in texture_name:
                            texture_name = texture_name.split('/')[-1]
                        texstring = f"common/{texture_name}"
                if texstring:
                    break
            if not texstring:
                texstring = self.option_skip

        rotation_layer = mesh.faces.layers.float.get("rotation")
        scale_x_layer = mesh.faces.layers.float.get("scale_x")
        scale_y_layer = mesh.faces.layers.float.get("scale_y") 
        offset_x_layer = mesh.faces.layers.float.get("offset_x")
        offset_y_layer = mesh.faces.layers.float.get("offset_y")

        # Get values with defaults

        rotation = face[rotation_layer] if rotation_layer else 0.0

        scale_x = face[scale_x_layer] if scale_x_layer else 1.0
        scale_y = face[scale_y_layer] if scale_y_layer else 1.0
        offset_x = face[offset_x_layer] if offset_x_layer else 0.0
        offset_y = face[offset_y_layer] if offset_y_layer else 0.0

        # Multiply every non-zero value by 10
        if rotation != 0.0:
            rotation2 = rotation
            rotation2 *= 60.0
            rotation = -rotation2
        if scale_x != 1.0:  # Note: scale defaults to 1.0, not 0.0
            scale_x *= 10.0
        if scale_y != 1.0:
            scale_y *= 10.0
        if offset_x != 0.0:
            offset_x *= 10.0
        if offset_y != 0.0:
            offset_y *= 10.0

        # Convert scale (existing code)
        scale_x = scale_x * (64.0 / width)
        scale_y = scale_y * (64.0 / height)

        finvals = [offset_x, offset_y, rotation, scale_x, scale_y]
        texstring += f" {self.printvec(finvals, 0)} // face index: {face.index}"
        return texstring

    def process_mesh(self, obj, fw, template):
        flags = self.faceflags(obj)
        #origin = self.gridsnap(obj.matrix_world.translation)
        obj.data.materials.append(None) # empty slot for new faces
        orig_obj = obj
        obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        bm = bmesh.new()
        bm.from_mesh(obj.to_mesh())
        bm.faces.ensure_lookup_table()
        bmesh.ops.transform(bm, matrix=obj.matrix_world,
                                            verts=bm.verts)
        for vert in bm.verts:
            vert.co = self.gridsnap(vert.co * 10)

        hull = bmesh.ops.convex_hull(bm, input=bm.verts)
        interior = [face for face in bm.faces if face not in hull['geom']]
        bmesh.ops.delete(bm, geom=interior, context='FACES')
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.join_triangles(bm, faces=bm.faces,
            angle_face_threshold=0.01, angle_shape_threshold=0.7)
        bmesh.ops.connect_verts_nonplanar(bm, faces=bm.faces,
                                            angle_limit=0.0)
        fw("// " + str(obj.name) + "\n")
        fw(template[0])
        for face in bm.faces:
            fw(self.brushplane(face))
            fw(self.texdata(face, bm, obj, orig_obj) + flags)
        fw(template[1])

        bm.free()
        orig_obj.data.materials.pop() # remove the empty slot

    def process_empty(self, obj, fw):
        name = obj.name.rstrip('0123456789')
        name = name[:-1] if name[-1] in ('.',' ') else obj.name
        fw("// entity " + str(obj.name) + "\n")
        fw('{\n"classname" "' + name + '"\n')
        origin = obj.matrix_world.to_translation() * 10
        zoffset = 0

        if 'origin' in obj:
            prop_value = obj['origin']
            
            # Handle special string values
            if prop_value == "player":
                prop_value = "24"
            elif prop_value == "intermission":
                prop_value = "16"
            
            # Convert to float, handle empty string
            if prop_value != '':
                zoffset = float(prop_value)
            else:
                zoffset = 0.0  # Default value for empty string
            
        fw(f'"origin" "{self.printvec(origin, zoffset)}"\n')
                    
        if 'modelscale' in obj and (obj['modelscale'] == "blender" or obj['modelscale'] == "bl"):
            # Check if all scale axes are the same
            if obj.scale.x == obj.scale.y == obj.scale.z:
                # All axes are equal, use modelscale with a single value
                scale_value = obj.scale.x * 10
                fw(f'"modelscale" "{scale_value:.4f}"\n')
            else:
                # Axes are different, use modelscale_vec
                scale_str = f"{obj.scale.x * 10:.4f} {obj.scale.y * 10:.4f} {obj.scale.z * 10:.4f}"       
                fw(f'"modelscale_vec" "{scale_str}"\n')
            
            # Remove the key so it won't be processed again
            del obj['modelscale']
        elif obj.scale.x != 1 and obj.scale.y != 1 and obj.scale.z != 1:
            scale_str = f"{obj.scale.x:.4f} {obj.scale.y:.4f} {obj.scale.z:.4f}"
            fw(f'"modelscale_vec" "{scale_str}"\n')
                
        # Handle angles with keyword support
        if 'angles' not in obj:
            angles_str = self.get_object_angles_string(obj)
            fw(f'"angles" "{angles_str}"\n')
        else:
            # Process angles value through the keyword conversion
            angles_value = obj['angles']
            processed_value = self.process_angle_value(angles_value)
            fw(f'"angles" "{processed_value}"\n')
        
        for prop in obj.keys():
            if prop != 'angles' and prop != 'origin':

                if isinstance(obj[prop], (int, float, str)):
                    prop_value = obj[prop] # no arrays
                    fw(f'"{prop}" "{prop_value}"\n')
        fw('}\n')

    def execute(self, context):
        self.report({'INFO'}, f"New Map Export Process Started:")
        timer = time.time()
        map_text = []
        fw = map_text.append
        wspwn_objs, bmodel_objs = [],[]
        empty_objs = []
        func_cols = []

        template = ['{\n', '}\n']
        fw('// entity 0\n{\n"classname" "worldspawn"\n')
        scene = bpy.context.scene
        custom_props = []
        for prop in scene.keys():
            if not scene.bl_rna.properties.get(prop):
                custom_props.append(prop)
        for prop in custom_props:
            fw(f'"{prop}" "{scene[prop]}"\n')

        # sort objects
        objects = context.scene.objects       
        if self.option_sel:
            objects = context.selected_objects
        else:
            objects = context.scene.objects

        for obj in objects:
            _, type = get_class(obj, False, context)
            if type == 'point_ent':
                empty_objs.append(obj)
                continue
            elif type == 'None':
                continue
            elif type == 'excluded':
                continue
            elif type == 'worldspawn':
                wspwn_objs.append(obj)
                continue
            elif type == 'brush_ent_group':
                if obj.users_collection[0] not in func_cols:
                    func_cols.append(obj.users_collection[0])
                continue
            elif type == 'brush_ent':
                bmodel_objs.append(obj)

        if not wspwn_objs:
            self.report({'ERROR'}, "No brushes found! Mesh object name must start with 'brush' and there must be at least one!")
            return  {'CANCELLED'}        
        
        # process objects
        for obj in wspwn_objs:
            self.process_mesh(obj, fw, template)
            
        for obj in bmodel_objs:
                fw(self.entname(obj))
                for prop in obj.keys():
                    if isinstance(obj[prop], (int, float, str)):
                        # Special handling for angles property
                        if prop == 'angles':
                            processed_value = self.process_angle_value(obj[prop])
                            fw(f'"{prop}" "{processed_value}"\n')
                        else:
                            fw(f'"{prop}" "{obj[prop]}"\n')

                self.process_mesh(obj, fw, template)

        for col in func_cols:
            fw(self.entname(col))
            # Write collection properties first (if any)
            if hasattr(col, 'keys'):
                col_keys = col.keys()
                for prop in col_keys:
                    if isinstance(col[prop], (int, float, str)):
                        # Special handling for angles property
                        if prop == 'angles':
                            processed_value = self.process_angle_value(col[prop])
                            fw(f'"{prop}" "{processed_value}"\n')
                        else:
                            fw(f'"{prop}" "{col[prop]}"\n')
       
            # Then process all mesh objects in collection
            for obj in col.objects:
                _, type = get_class(obj, True, context)      
                if type == 'brush':           
                #if obj.type == 'MESH' and (obj.data and len(obj.data.vertices) > 0) and not any(prefix in obj.name.lower() for prefix in exclude_tags):
                    self.process_mesh(obj, fw, template)
        
        fw('}\n')
        for obj in empty_objs:
                self.process_empty(obj, fw)

        # handle output
        scene_str = ''.join(map_text)
        with open(self.filepath, 'w') as file:
            file.write(scene_str)

        timer = time.time() - timer
        self.report({'INFO'},f"Finished exporting map, took {timer:g} sec")
        return {'FINISHED'}

############################ Trenchcoat ############################
############################ by uzugijin ###########################

def get_class(obj, brush_only, context):    
    exclude_tags = [".exclude", "-exclude", "_exclude", "/exclude", ".ignore", "-ignore", "_ignore", "/ignore",
            ".editor", "-editor", "_editor", "/editor",
            ] # Stuff named with these get ignored on export!
    prefixes = ["scene collection", "collection", ".col", "-col", "_col", "/col",
                    ".detail", "-detail", "_detail", "/detail", ".common/", "-common/", "_common/", "/common/"] # These will get included to worldspawn class. Normally, if you name your brush or collection, they will become entities!
    
    collection_name = obj.users_collection[0].name.lower()

    if any(prefix in obj.name.lower() for prefix in exclude_tags) or any(prefix in collection_name.lower() for prefix in exclude_tags):
        return obj, 'excluded'
    else:
        if obj.type != 'MESH':
            
            if obj.type in ('EMPTY') and obj.empty_display_type != 'PLAIN_AXES':
                return obj, 'point_ent'
            else:
                return obj, 'None'
        else:
            if "misc_model" in obj.name or ".entity" in obj.name or (obj.type == 'MESH' and obj.data and len(obj.data.vertices) == 0):
                return obj, 'point_ent'
            else:
                if not brush_only:
                    if collection_name.lower() != "detail":
                        if obj.name.lower().startswith('brush'):
                            if any(prefix in collection_name.lower() for prefix in prefixes):
                                obj = context.scene
                                return obj, 'worldspawn'
                            else:
                                obj = obj.users_collection[0]
                                return obj, 'brush_ent_group'
                        else:
                            if not any(prefix in collection_name.lower() for prefix in prefixes):
                                obj = obj.users_collection[0]
                                return obj, 'brush_ent_group'
                            else:
                                if ".detail" not in obj.name.lower():        
                                    return obj, 'brush_ent'
                                else:
                                    obj = context.scene
                                    return obj, 'worldspawn'
                    else:
                        obj = context.scene
                        return obj, 'worldspawn'
                else:
                    return obj, 'brush'

def add_player_node(node_group):
    #upper_lane
    cube_node = node_group.nodes.new('GeometryNodeMeshCube')
    node_group.nodes["Cube"].inputs[0].default_value[0] = 3.2
    node_group.nodes["Cube"].inputs[0].default_value[1] = 3.2
    node_group.nodes["Cube"].inputs[0].default_value[2] = 3.2
    
    set_pos_node = node_group.nodes.new('GeometryNodeSetPosition')
    node_group.nodes["Set Position"].inputs[3].default_value[2] = 4
    
    scale_elm_node = node_group.nodes.new('GeometryNodeScaleElements')
    node_group.nodes["Scale Elements"].domain = 'FACE'
    node_group.nodes["Scale Elements"].scale_mode = 'UNIFORM'
    node_group.nodes["Scale Elements"].inputs[2].default_value = 0.38
    
    equal_node = node_group.nodes.new('FunctionNodeCompare')
    node_group.nodes["Compare"].data_type = 'VECTOR'
    node_group.nodes["Compare"].operation = 'EQUAL'
    node_group.nodes["Compare"].inputs[12].default_value = 2.4
    
    read_pos_node = node_group.nodes.new('GeometryNodeInputPosition')
    
    #downtown
    cube_node2 = node_group.nodes.new('GeometryNodeMeshCube')
    node_group.nodes["Cube.001"].inputs[0].default_value[0] = 3.2
    node_group.nodes["Cube.001"].inputs[0].default_value[1] = 3.2
    node_group.nodes["Cube.001"].inputs[0].default_value[2] = 1.75
    
    set_pos_node2 = node_group.nodes.new('GeometryNodeSetPosition')
    node_group.nodes["Set Position.001"].inputs[3].default_value[2] = 0.875
    
    scale_elm_node2 = node_group.nodes.new('GeometryNodeScaleElements')
    node_group.nodes["Scale Elements.001"].domain = 'FACE'
    node_group.nodes["Scale Elements.001"].scale_mode = 'UNIFORM'
    node_group.nodes["Scale Elements.001"].inputs[2].default_value = 0.38    

    extrude_node = node_group.nodes.new('GeometryNodeExtrudeMesh')
    node_group.nodes["Extrude Mesh"].mode = 'FACES'
    node_group.nodes["Extrude Mesh"].inputs[3].default_value = 0.66
    node_group.nodes["Extrude Mesh"].inputs[4].default_value = True

    equal_node2 = node_group.nodes.new('FunctionNodeCompare')
    node_group.nodes["Compare.001"].data_type = 'VECTOR'
    node_group.nodes["Compare.001"].operation = 'EQUAL'
    node_group.nodes["Compare.001"].inputs[12].default_value = 0.8
    node_group.nodes["Compare.001"].inputs[5].default_value[2] = 1
    
    #center
    cyl_node = node_group.nodes.new('GeometryNodeMeshCylinder')
    node_group.nodes["Cylinder"].inputs[0].default_value = 4
    node_group.nodes["Cylinder"].inputs[3].default_value = 0.34
    node_group.nodes["Cylinder"].inputs[4].default_value = 2.41

    combine_node = node_group.nodes.new('ShaderNodeCombineXYZ')
    set_pos_node3 = node_group.nodes.new('GeometryNodeSetPosition')

    trans_node = node_group.nodes.new('GeometryNodeTransform')
    node_group.nodes["Transform Geometry"].inputs[1].default_value[0] = 1.6
    node_group.nodes["Transform Geometry"].inputs[1].default_value[2] = 2.08
    node_group.nodes["Transform Geometry"].inputs[2].default_value[1] = 1.5708

    join_node = node_group.nodes.new("GeometryNodeJoinGeometry")
    output_node = node_group.nodes.get('Group Output')
    
    #linking_upperlane
    
    node_group.links.new(cube_node.outputs['Mesh'], set_pos_node.inputs['Geometry'])
    node_group.links.new(set_pos_node.outputs['Geometry'], scale_elm_node.inputs['Geometry'])
    node_group.links.new(read_pos_node.outputs['Position'], equal_node.inputs['A'])
    node_group.links.new(equal_node.outputs['Result'], scale_elm_node.inputs['Selection'])
    node_group.links.new(scale_elm_node.outputs['Geometry'], join_node.inputs['Geometry'])
    
    #linking_downtown
    
    node_group.links.new(cube_node2.outputs['Mesh'], set_pos_node2.inputs['Geometry'])
    node_group.links.new(set_pos_node2.outputs['Geometry'], scale_elm_node2.inputs['Geometry'])
    node_group.links.new(scale_elm_node2.outputs['Geometry'], extrude_node.inputs['Mesh'])
    node_group.links.new(read_pos_node.outputs['Position'], equal_node2.inputs['A'])
    node_group.links.new(equal_node2.outputs['Result'], scale_elm_node2.inputs['Selection'])
    node_group.links.new(extrude_node.outputs['Mesh'], join_node.inputs['Geometry'])
    node_group.links.new(equal_node2.outputs['Result'], extrude_node.inputs['Selection'])
    node_group.links.new(join_node.outputs['Geometry'], output_node.inputs['Geometry'])

    #linking extra
    node_group.links.new(cyl_node.outputs['Mesh'], set_pos_node3.inputs['Geometry'])
    node_group.links.new(cyl_node.outputs['Top'], set_pos_node3.inputs['Selection'])
    node_group.links.new(combine_node.outputs['Vector'], set_pos_node3.inputs['Position'])
    node_group.links.new(set_pos_node3.outputs['Geometry'], trans_node.inputs['Geometry'])
    node_group.links.new(trans_node.outputs['Geometry'], join_node.inputs['Geometry'])
    
    return node_group

def add_ent_node(node_group):
    
    cube_node = node_group.nodes.new('GeometryNodeMeshCube')
    node_group.nodes["Cube"].inputs[0].default_value[0] = 1.75
    node_group.nodes["Cube"].inputs[0].default_value[1] = 1.75
    node_group.nodes["Cube"].inputs[0].default_value[2] = 1.75
    
    cyl_node = node_group.nodes.new('GeometryNodeMeshCylinder')
    node_group.nodes["Cylinder"].inputs[0].default_value = 4
    node_group.nodes["Cylinder"].inputs[3].default_value = 0.34
    node_group.nodes["Cylinder"].inputs[4].default_value = 2.41

    combine_node = node_group.nodes.new('ShaderNodeCombineXYZ')
    set_pos_node = node_group.nodes.new('GeometryNodeSetPosition')

    trans_node = node_group.nodes.new('GeometryNodeTransform')
    node_group.nodes["Transform Geometry"].inputs[1].default_value[0] = 2.08
    node_group.nodes["Transform Geometry"].inputs[2].default_value[1] = 1.5708

    join_node = node_group.nodes.new("GeometryNodeJoinGeometry")  
    output_node = node_group.nodes.get('Group Output')
    
    #linking
    
    #linking extra
    node_group.links.new(cyl_node.outputs['Mesh'], set_pos_node.inputs['Geometry'])
    node_group.links.new(cyl_node.outputs['Top'], set_pos_node.inputs['Selection'])
    node_group.links.new(combine_node.outputs['Vector'], set_pos_node.inputs['Position'])
    node_group.links.new(set_pos_node.outputs['Geometry'], trans_node.inputs['Geometry'])
    node_group.links.new(trans_node.outputs['Geometry'], join_node.inputs['Geometry'])
    node_group.links.new(cube_node.outputs['Mesh'], join_node.inputs['Geometry'])
    node_group.links.new(join_node.outputs['Geometry'], output_node.inputs['Geometry'])
    
    return node_group

def add_item_node(node_group):
        
    cyl_node = node_group.nodes.new('GeometryNodeMeshCylinder')
    node_group.nodes["Cylinder"].inputs[0].default_value = 4
    node_group.nodes["Cylinder"].inputs[3].default_value = 0.34
    node_group.nodes["Cylinder"].inputs[4].default_value = 2.41

    combine_node = node_group.nodes.new('ShaderNodeCombineXYZ')
    set_pos_node = node_group.nodes.new('GeometryNodeSetPosition')

    trans_node = node_group.nodes.new('GeometryNodeTransform')
    node_group.nodes["Transform Geometry"].inputs[1].default_value[0] = 2.03
    node_group.nodes["Transform Geometry"].inputs[1].default_value[2] = 1.8
    node_group.nodes["Transform Geometry"].inputs[2].default_value[1] = 1.5708

    cube_node = node_group.nodes.new('GeometryNodeMeshCube')
    node_group.nodes["Cube"].inputs[0].default_value[0] = 3.2
    node_group.nodes["Cube"].inputs[0].default_value[1] = 3.2
    node_group.nodes["Cube"].inputs[0].default_value[2] = 0.39

    set_pos_node2 = node_group.nodes.new('GeometryNodeSetPosition')
    node_group.nodes["Set Position.001"].inputs[3].default_value[2] = 0.195

    cube_node2 = node_group.nodes.new('GeometryNodeMeshCube')
    node_group.nodes["Cube.001"].inputs[0].default_value[0] = 1.64
    node_group.nodes["Cube.001"].inputs[0].default_value[1] = 1.64
    node_group.nodes["Cube.001"].inputs[0].default_value[2] = 2.9

    set_pos_node3 = node_group.nodes.new('GeometryNodeSetPosition')
    node_group.nodes["Set Position.002"].inputs[3].default_value[2] = 1.81

    join_node = node_group.nodes.new("GeometryNodeJoinGeometry")  
    output_node = node_group.nodes.get('Group Output')
    
    #linking
    
    #linking extra
    node_group.links.new(cyl_node.outputs['Mesh'], set_pos_node.inputs['Geometry'])
    node_group.links.new(cyl_node.outputs['Top'], set_pos_node.inputs['Selection'])
    node_group.links.new(combine_node.outputs['Vector'], set_pos_node.inputs['Position'])
    node_group.links.new(set_pos_node.outputs['Geometry'], trans_node.inputs['Geometry'])
    node_group.links.new(trans_node.outputs['Geometry'], join_node.inputs['Geometry'])

    node_group.links.new(cube_node.outputs['Mesh'], set_pos_node2.inputs['Geometry'])
    node_group.links.new(set_pos_node2.outputs['Geometry'], join_node.inputs['Geometry'])

    node_group.links.new(cube_node2.outputs['Mesh'], set_pos_node3.inputs['Geometry'])
    node_group.links.new(set_pos_node3.outputs['Geometry'], join_node.inputs['Geometry'])

    node_group.links.new(join_node.outputs['Geometry'], output_node.inputs['Geometry'])
    
    return node_group

def add_convex_hull_node(node_group):

    vet_neighbors_node = node_group.nodes.new('GeometryNodeInputMeshVertexNeighbors')
    del_geometry_node = node_group.nodes.new('GeometryNodeDeleteGeometry')
    join_geometry_node = node_group.nodes.new('GeometryNodeJoinGeometry')

    convex_hull_node = node_group.nodes.new('GeometryNodeConvexHull')
    input_node = node_group.nodes.get('Group Input')
    output_node = node_group.nodes.get('Group Output')

    node_group.links.new(vet_neighbors_node.outputs['Vertex Count'], del_geometry_node.inputs['Selection'])
    node_group.links.new(input_node.outputs['Geometry'], del_geometry_node.inputs['Geometry'])
    node_group.links.new(del_geometry_node.outputs['Geometry'], convex_hull_node.inputs['Geometry'])
    node_group.links.new(convex_hull_node.outputs['Convex Hull'], join_geometry_node.inputs['Geometry'])
    node_group.links.new(output_node.inputs['Geometry'], join_geometry_node.outputs['Geometry'])
    node_group.links.new(input_node.outputs['Geometry'], join_geometry_node.inputs['Geometry'])
    return node_group

def add_geonode_to_object(obj, name, node):
            # Check if the object already has a Geometry Node modifier
                try:
                    modifier = obj.modifiers.get(name)
                except:
                    pass
                if modifier is None:
                    modifier = obj.modifiers.new(name, 'NODES')
                    try:
                        modifier.node_group = bpy.data.node_groups[name+"GeometryGroup"]
                    except:
                        pass
                    if modifier.node_group is None:
                        bpy.ops.node.new_geometry_node_group_assign()        
                        modifier.node_group.name = name+"GeometryGroup"
                        group_name = modifier.node_group.name  
                        if node == "convex_hull":
                            add_convex_hull_node(modifier.node_group)
                        elif node == "player":
                            add_player_node(modifier.node_group)
                        elif node == "ent":
                            add_ent_node(modifier.node_group)
                        elif node == "item":
                            add_item_node(modifier.node_group)

                        return group_name

class DuplicateObjectOperator(bpy.types.Operator):
    bl_idname = "object.duplicate_shared"
    bl_label = "Duplicate Object (Shared Mesh)"
    bl_description = "Makes a symmetrical duplicate"
    bl_options = {'UNDO'}

    def execute(self, context):
        bpy.context.scene.tool_settings.use_transform_pivot_point_align = False
        selectedobjects = []
        for obj in bpy.context.selected_objects:
            selectedobjects.append(obj)
        if context.scene.invasive_mirror:
            active_object = bpy.context.active_object
            bpy.ops.object.select_all(action='DESELECT')
            active_object.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            previous_pp = bpy.context.scene.tool_settings.transform_pivot_point
            bpy.context.scene.tool_settings.transform_pivot_point = 'BOUNDING_BOX_CENTER'
            bpy.ops.view3d.snap_cursor_to_selected()
            bpy.context.scene.tool_settings.transform_pivot_point = previous_pp
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            try:
                selectedobjects.remove(active_object)
            except:
                self.report({'ERROR'}, "There was no active selection!")
                return {'CANCELLED'}
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in selectedobjects:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            if context.scene.invasive_mirror:
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            bpy.ops.object.duplicate_move()
            
            axis_block = []
            if context.scene.mirror_axis == "x":
                axis_block = (True, False, False)
            elif context.scene.mirror_axis == "y":
                axis_block = (False, True, False)
            elif context.scene.mirror_axis == "z":
                axis_block = (False, False, True)
            bpy.ops.transform.mirror(orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(axis_block))
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            obj.select_set(False)
            bpy.context.view_layer.objects.active = None
            bpy.ops.object.select_all(action='DESELECT')
        for obj in selectedobjects:
            obj.select_set(True)    
        return {'FINISHED'}

class SnapOriginToCenter(bpy.types.Operator):
    """Snaps the origin(s) of the object(s) to world origin"""
    bl_idname = "object.set_origin_to_world"
    bl_label = "Set Origin to World"
    bl_options = {'UNDO'}

    def execute(self, context):
        previous_cursor_loc = bpy.context.scene.cursor.location.copy()
        print(previous_cursor_loc)
        previous_mode = bpy.context.object.mode
        print(previous_cursor_loc)
        bpy.ops.object.mode_set(mode='OBJECT')
        print(previous_cursor_loc)
        bpy.context.scene.cursor.location = (0, 0, 0)
        print(previous_cursor_loc)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        print(previous_cursor_loc)
        bpy.context.scene.cursor.location = previous_cursor_loc
        print(previous_cursor_loc)
        bpy.ops.object.mode_set(mode=previous_mode)
        
        return {'FINISHED'}

class SnapOriginToMedian(bpy.types.Operator):
    """Snaps the origin(s) of the object(s) to the(ir) bounding box center"""
    bl_idname = "object.set_origin_to_median"
    bl_label = "Set Origin to Bounding Box Center"
    bl_options = {'UNDO'}

    def execute(self, context):
        previous_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        bpy.ops.object.mode_set(mode=previous_mode)
        return {'FINISHED'}

class SnapOriginToActive(bpy.types.Operator):
    """Snaps the origin(s) of the object(s) to the active object's origin"""
    bl_idname = "object.set_origin_to_active"
    bl_label = "Set Origin to Active"
    bl_options = {'UNDO'}

    def execute(self, context):
        active = bpy.context.active_object
        selected = bpy.context.selected_objects
        previous_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.cursor.location = active.location
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        bpy.ops.object.mode_set(mode=previous_mode)
        return {'FINISHED'}

class OBJECT_OT_snap_ori(bpy.types.Operator):
    """Snaps the origin(s) of the object(s) to the selected vertex"""
    bl_idname = "object.set_origin_to_selected"
    bl_label = "Set Origin"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                bpy.ops.object.mode_set(mode='EDIT')

                # Snap the cursor to the selected vertex
                bpy.ops.view3d.snap_cursor_to_selected()

                # Switch back to object mode
                bpy.ops.object.mode_set(mode='OBJECT')

                # Set the origin to the cursor location
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class OBJECT_OT_snap_selected_to_grid(bpy.types.Operator):
    """Snaps all vertices of the mesh object(s) to the grid"""
    bl_idname = "object.snap_selected_to_grid"
    bl_label = "Snap Vertices to Grid"
    bl_options = {'UNDO'}

    def execute(self, context):
        
        # Get selected objects
        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH' and obj.data and len(obj.data.vertices) > 0]
        if bpy.context.active_object.type == 'MESH' and bpy.context.active_object.data and len(bpy.context.active_object.data.vertices) > 0:
            selected_objects.append(bpy.context.active_object)
        original_grid = bpy.context.space_data.overlay.grid_scale              
        original_mode = bpy.context.object.mode
        grid_scale = float(bpy.context.scene.grid_size)
        
        if not selected_objects:
            for obj in bpy.context.selected_objects:
                if obj:
                    bpy.context.space_data.overlay.grid_scale = grid_scale
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.view3d.snap_selected_to_grid()
                    bpy.context.space_data.overlay.grid_scale = original_grid
                else:
                    print("No objects selected")
            return {'FINISHED'}
        
        # Results storage
        results = {
            'aligned_verts': 0,
            'misaligned_verts': 0,
            'misaligned_objects': []
        }
            
        for obj in selected_objects:
            # Make sure we're working with the object's data
            mesh = obj.data
            
            # Get the world matrix for object transformations
            world_matrix = obj.matrix_world
            
            # Check if object is in edit mode
            if obj.mode == 'EDIT':
                # Get a bmesh from the edit mesh
                bm = bmesh.from_edit_mesh(mesh)
                verts = bm.verts
            else:
                # For object mode, use the mesh vertices directly
                verts = mesh.vertices
            
            object_results = {
                'name': obj.name,
                'aligned_verts': 0,
                'misaligned_verts': 0,
                'misaligned_positions': []
            }
            
            for vert in verts:
                # Get the world position of the vertex
                if obj.mode == 'EDIT':
                    vert_world_pos = world_matrix @ vert.co
                else:
                    vert_world_pos = world_matrix @ vert.co
                
                # Check if each coordinate is aligned to the grid
                aligned = True
                for i in range(3):
                    # Calculate how many grid steps this coordinate represents
                    coord_steps = vert_world_pos[i] / grid_scale
                    
                    # Check if it's close to a whole number (within a small tolerance)
                    if abs(coord_steps - round(coord_steps)) > 0.0001:
                        aligned = False
                        break
                
                if aligned:
                    object_results['aligned_verts'] += 1
                    results['aligned_verts'] += 1
                else:
                    object_results['misaligned_verts'] += 1
                    #object_results['misaligned_positions'].append(vert_world_pos.copy())
                    results['misaligned_verts'] += 1
            
            if object_results['misaligned_verts'] > 0:
                results['misaligned_objects'].append(object_results)
                           
                bpy.ops.object.mode_set(mode='EDIT')
                  
                if context.scene.snap_alone == False:
                    bpy.ops.mesh.select_all(action='SELECT')
                
                bpy.context.space_data.overlay.grid_scale = grid_scale
                bpy.ops.view3d.snap_selected_to_grid()
                                              
                # Remove doubles
                #bpy.ops.mesh.remove_doubles()
                bpy.context.space_data.overlay.grid_scale = original_grid
                
                if context.scene.snap_alone == False:
                    bpy.ops.mesh.select_all(action='DESELECT')
                        
                # Restore original active object and mode
                bpy.ops.object.mode_set(mode=original_mode)
                        
        if results['misaligned_objects']:
            for obj_result in results['misaligned_objects']:
                print(f"  {obj_result['name']}: {obj_result['misaligned_verts']} misaligned vertices")
            self.report({'INFO'}, "Misaligned vertices snapped to grid!")
        else:
            print("All vertices are aligned to the grid!")
            self.report({'INFO'}, "No snapping is needed!")
        
        return {'FINISHED'}

#SHORTCUTS

class TCShortcuts_XRAY(bpy.types.Operator):
    bl_idname = "object.trenchcoat_shortcuts_xray"
    bl_label = "Trenchcoat Shortcuts"
    bl_description = "Toggle XRAY"
    bl_options = {'UNDO'}

    def execute(self, context):

        if not context.scene.shrt_xray:
            context.space_data.shading.show_xray = True
            context.scene.shrt_xray = True
        else:            
            context.space_data.shading.show_xray = False
            context.scene.shrt_xray = False   

        return {'FINISHED'}

class TCShortcuts_OBJCOL(bpy.types.Operator):
    bl_idname = "object.trenchcoat_shortcuts_objcol"
    bl_label = "Trenchcoat Shortcuts"
    bl_description = "Toggle Vertex-Only View"
    bl_options = {'UNDO'}

    def execute(self, context):
        if not context.scene.shrt_obj_col:           
            context.space_data.overlay.show_retopology = True
            context.scene.shrt_obj_col = True
        else:
            context.space_data.overlay.show_retopology = False
            context.scene.shrt_obj_col = False
        return {'FINISHED'}

class TCShortcuts_PIVOTCURSOR(bpy.types.Operator):
    bl_idname = "object.trenchcoat_shortcuts_pivot_cursor"
    bl_label = "Trenchcoat Shortcuts"
    bl_description = "Toggle 3D Cursor Pivot"
    bl_options = {'UNDO'}

    def execute(self, context):
        
        if not context.scene.shrt_pivot_cursor:
            context.scene.tool_settings.transform_pivot_point = 'CURSOR'

            context.scene.shrt_pivot_cursor = True
        else:
            context.scene.tool_settings.transform_pivot_point = 'MEDIAN_POINT'
            context.scene.shrt_pivot_cursor = False
        return {'FINISHED'}

class TCShortcuts_INCREMENT(bpy.types.Operator):
    bl_idname = "object.trenchcoat_shortcuts_increment"
    bl_label = "Trenchcoat Shortcuts"
    bl_description = "Toggles gridsnapping"
    bl_options = {'UNDO'}

    def execute(self, context):
        bpy.context.space_data.overlay.grid_scale = float(bpy.context.scene.grid_size)
        if bpy.context.scene.tool_settings.snap_elements_base != {'INCREMENT'} or bpy.context.scene.tool_settings.use_snap == False:
            bpy.context.scene.tool_settings.snap_elements_base = {'INCREMENT'}
            bpy.context.scene.tool_settings.use_snap = True
            context.scene.snapset1 = True
        else:
            bpy.context.scene.tool_settings.use_snap = False
            bpy.context.scene.tool_settings.snap_elements_base = {'VERTEX', 'EDGE', 'EDGE_MIDPOINT'}
            context.scene.snapset1 = False

        return {'FINISHED'}

class CalcGridstance(bpy.types.Operator):
    bl_idname = "object.gridstancecalc"
    bl_label = "Calculate Grid steps between 2 verts"
    bl_description = "Calculate Grid steps between 2 verts"
    bl_options = {'UNDO'}

    def execute(self, context):
        
        # Get the active mesh
        obj = bpy.context.edit_object
        if obj is None:
            print("No active object in edit mode")
            return {'FINISHED'}
        
        # Create a bmesh from the mesh data
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        
        # Get selected vertices
        selected_verts = [v for v in bm.verts if v.select]
        
        if len(selected_verts) != 2:
            print("Please select exactly 2 vertices")
            return {'FINISHED'}
        
        # Get vertex coordinates
        v1_co = selected_verts[0].co
        v2_co = selected_verts[1].co
        
        # Get the current grid scale
        grid_scale = float(context.scene.grid_size)
       
        # Calculate the distance vector between the vertices
        distance_vector = v2_co - v1_co
        
        # Calculate grid steps in each axis
        grid_steps_x = abs(distance_vector.x) / grid_scale
        grid_steps_y = abs(distance_vector.y) / grid_scale
        grid_steps_z = abs(distance_vector.z) / grid_scale
        
        # Calculate total grid steps (Euclidean distance)
        total_grid_steps = distance_vector.length / grid_scale
        
        # Print results
        print(f"Distance between vertices: {distance_vector.length:.4f} units")
        print(f"Grid scale: {grid_scale:.4f} units")
        print(f"Grid steps in X axis: {grid_steps_x:.2f}")
        print(f"Grid steps in Y axis: {grid_steps_y:.2f}")
        print(f"Grid steps in Z axis: {grid_steps_z:.2f}")
        print(f"Total grid steps (Euclidean distance): {total_grid_steps:.2f}")
#         
#         return {
#             'x_steps': grid_steps_x,
#             'y_steps': grid_steps_y,
#             'z_steps': grid_steps_z,
#             'total_steps': total_grid_steps
#         }
        context.scene.gridsteps = total_grid_steps
        return {'FINISHED'}

class ConvexHullBrush(bpy.types.Operator):
    bl_idname = "object.convexhull_brush"
    bl_label = "Make Brush"
    bl_description = "Register as brush: Renames mesh to brush, attaches convex hull nodegroup (requires HintCage material), optionally merges brushes"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Get the active object
        obj = context.active_object
        grid_size = float(context.scene.grid_size)
        snap = context.scene.snap
        original_grid = bpy.context.space_data.overlay.grid_scale
        original_mode = bpy.context.object.mode

        # Store originally selected objects
        original_selected = list(context.selected_objects)

        # Process each mesh object and track which ones were processed
        processed_objects = []

        for obj in original_selected:
            if obj.type == 'MESH':
                # Remove custom properties
                for key in list(obj.keys()):
                    if key not in ['_RNA_UI']:  # Keep Blender's internal properties
                        del obj[key]

                bpy.ops.object.mode_set(mode='OBJECT')
                # Select only this object 
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj
                bpy.ops.object.convert(target='MESH')
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.separate(type='LOOSE')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.convex_hull()
                if snap:
                    bpy.context.space_data.overlay.grid_scale = grid_size
                    bpy.ops.view3d.snap_selected_to_grid()
                    bpy.context.space_data.overlay.grid_scale = original_grid
                bpy.ops.mesh.delete(type='EDGE_FACE')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.convex_hull()
                bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')

                if context.scene.hintcage:
                    add_geonode_to_object(obj, "ConvexHullBrush", "convex_hull")
                
                # Store the processed object
                processed_objects.append(obj)
                
                bpy.ops.object.mode_set(mode=original_mode)
                if context.scene.material is not None:
                    if context.scene.material.name not in obj.data.materials:
                        obj.data.materials.append(context.scene.material)
            else:
                self.report({'WARNING'}, f"Skipping non-mesh object: {obj.name}")

        # Handle automerge AFTER processing all objects
        if context.scene.automerge and processed_objects:
            # Deselect all objects first
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            # Select only the processed objects
            for obj in processed_objects:
                obj.select_set(True)
            
            # Set the first processed object as active
            context.view_layer.objects.active = processed_objects[0]
            
            # Join all processed objects
            bpy.ops.object.join()
            bpy.ops.object.convert(target='MESH')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.convex_hull()
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Get the merged object
            merged_obj = context.active_object
            
            # Rename the merged object
            merged_obj.name = "brush"
            merged_obj.data.name = "brush"
            
            # Add geometry nodes to the merged object
            if context.scene.hintcage:
                add_geonode_to_object(merged_obj, "ConvexHullBrush", "convex_hull")
            
            # Apply material if needed
            if context.scene.material is not None:
                if context.scene.material.name not in merged_obj.data.materials:
                    merged_obj.data.materials.append(context.scene.material)

        # If not automerging, just rename the processed objects
        else:
            for i, obj in enumerate(processed_objects):
                obj.name = f"brush.{i:03d}"
                obj.data.name = f"brush.{i:03d}"


        for obj in (processed_objects if not context.scene.automerge else [context.active_object]):
            obj.select_set(True)

        return {'FINISHED'}

class ApplyMaterial(bpy.types.Operator):
    bl_idname = "object.apply_material"
    bl_label = "Apply Material"
    bl_description = "Apply the input material to the selected object(s)"
    bl_options = {'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if context.scene.material is not None:
                    obj.data.materials.clear()
                    obj.data.materials.append(context.scene.material)
                else:
                    self.report({'ERROR'}, "No material selected!")
        return {'FINISHED'}
    
class DuplicateMaterial(bpy.types.Operator):
    bl_idname = "object.duplicate_material"
    bl_label = "Duplicate Material"
    bl_description = "Make a duplicate of the input material"
    bl_options = {'UNDO'}

    def execute(self, context):
        context.scene.material.copy()
        return {'FINISHED'}
    
class DeleteMaterial(bpy.types.Operator):
    bl_idname = "object.delete_material"
    bl_label = "Delete Material"
    bl_description = "Delete the input material."
    bl_options = {'UNDO'}

    def execute(self, context):
        bpy.data.materials.remove(context.scene.material)
        return {'FINISHED'}

class Solo_brush(bpy.types.Operator):
    bl_idname = "object.solo_brush"
    bl_label = "Solo Brush"
    bl_description = "Solo da brush so ye can see"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Get selected objects (not necessarily the active one)
        global global_list_of_things
        list_of_things = global_list_of_things
        print(global_list_of_things)
        if list_of_things == []:
            if bpy.context.object.mode == 'EDIT':
                for obj in bpy.data.objects:
                    if obj != context.edit_object:
                        list_of_things.append(obj)
                        obj.hide_viewport = True
            else:
                self.report({'WARNING'}, "Edit mode only")
        else:
            for obj in list_of_things:
                obj.hide_viewport = False
                global_list_of_things = []

        return {'FINISHED'}

class Popfront(bpy.types.Operator):
    bl_idname = "object.popfront"
    bl_label = "Pop Front"
    bl_description = "Set display mode to In Front. Solid and Workbench only."
    bl_options = {'UNDO'}

    def execute(self, context):
        # Get selected objects (not necessarily the active one)
        obj = context.active_object
        if obj.show_in_front == True:
            obj.show_in_front = False
        else:
            obj.show_in_front = True
        return {'FINISHED'}

class Popfront_Reset(bpy.types.Operator):
    bl_idname = "object.popfront_reset"
    bl_label = "Clear In Front"
    bl_description = "Reset display mode to not normal for all objects"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Get selected objects (not necessarily the active one)
        for obj in bpy.data.objects:
            obj.show_in_front = False
        return {'FINISHED'}

class CreatePlayerCube(bpy.types.Operator):
    bl_idname = "object.create_player_cube"
    bl_label = "Spawn Player Pawn"
    bl_description = "Spawn a quake 3 player sized pawn at 3d cursor"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Create a new bmesh
        
        grid_size = float(context.scene.grid_size)
        original_grid = bpy.context.space_data.overlay.grid_scale

        for data in bpy.data.meshes:
            if data.name == "null":
                mesh_data = data
                break
            else:
                mesh_data = bpy.data.meshes.new("null")
                bm = bmesh.new()
                bm.to_mesh(mesh_data)
                bm.free()
            
        mesh_obj = bpy.data.objects.new("info_player_deathmatch", mesh_data)
        bpy.context.collection.objects.link(mesh_obj)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = mesh_obj
        
        mesh_obj.select_set(True)
        add_geonode_to_object(mesh_obj, "PlayerEntGen", "player")
        
        # Set the object color to red
        mesh_obj.color = (1.0, 0.0, 0.0, 1.0)
        mesh_obj["origin"] = "24"
        bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
        
        bpy.context.space_data.overlay.grid_scale = grid_size
        bpy.ops.view3d.snap_selected_to_grid()
        bpy.context.space_data.overlay.grid_scale = original_grid

        return {'FINISHED'}

class CreateEntityCube(bpy.types.Operator):
    bl_idname = "object.create_entity_cube"
    bl_label = "Spawn Entity Dummy"
    bl_description = "Spawn a point entity box at 3d cursor"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Create a new bmesh
        
        grid_size = float(context.scene.grid_size)
        original_grid = bpy.context.space_data.overlay.grid_scale

        for data in bpy.data.meshes:
            if data.name == "null":
                mesh_data = data
                break
            else:
                mesh_data = bpy.data.meshes.new("null")
                bm = bmesh.new()
                bm.to_mesh(mesh_data)
                bm.free()
            
        mesh_obj = bpy.data.objects.new("generic_entity", mesh_data)
        bpy.context.collection.objects.link(mesh_obj)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = mesh_obj
        
        mesh_obj.select_set(True)
        add_geonode_to_object(mesh_obj, "GenericEntGen", "ent")
       
        # Set the object color to red
        mesh_obj.color = (0.0, 0.720, 0.0, 1.0)
        mesh_obj["origin"] = ""
        bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
        
        bpy.context.space_data.overlay.grid_scale = grid_size
        bpy.ops.view3d.snap_selected_to_grid()
        bpy.context.space_data.overlay.grid_scale = original_grid

        return {'FINISHED'}

class CreateItemCube(bpy.types.Operator):
    bl_idname = "object.create_item_cube"
    bl_label = "Spawn Item Dummy"
    bl_description = "Spawn a point item entity box at 3d cursor"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Create a new bmesh
        
        grid_size = float(context.scene.grid_size)
        original_grid = bpy.context.space_data.overlay.grid_scale

        for data in bpy.data.meshes:
            if data.name == "null":
                mesh_data = data
                break
            else:
                mesh_data = bpy.data.meshes.new("null")
                bm = bmesh.new()
                bm.to_mesh(mesh_data)
                bm.free()
            
        mesh_obj = bpy.data.objects.new("generic_entity", mesh_data)
        bpy.context.collection.objects.link(mesh_obj)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = mesh_obj
        
        mesh_obj.select_set(True)
        add_geonode_to_object(mesh_obj, "GenericItemGen", "item")
       
        # Set the object color to red
        mesh_obj.color = (0.700, 0.0, 1.0, 1.0)
        mesh_obj["origin"] = "24"
        bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
        
        bpy.context.space_data.overlay.grid_scale = grid_size
        bpy.ops.view3d.snap_selected_to_grid()
        bpy.context.space_data.overlay.grid_scale = original_grid

        return {'FINISHED'}

class CreateSkyBox(bpy.types.Operator):
    bl_idname = "object.create_skybox"
    bl_label = "Spawn Entity Dummy"
    bl_description = "Spawn a point entity box at 3d cursor"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Create a new bmesh
        obj = context.active_object
        obj.name = 'brush'
        grid_size = float(context.scene.grid_size)
        original_grid = bpy.context.space_data.overlay.grid_scale
        original_mode = bpy.context.object.mode
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.mesh.edge_split(type='EDGE')
        bpy.ops.mesh.solidify(thickness=-0.5)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.context.space_data.overlay.grid_scale = grid_size
        bpy.ops.view3d.snap_selected_to_grid()
        bpy.context.space_data.overlay.grid_scale = original_grid
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode=original_mode)

        return {'FINISHED'}

class OBJECT_OT_AddPropertyFromText(bpy.types.Operator):
    bl_idname = "object.add_property_from_text"
    bl_label = "Add/Update Property"
    bl_description = "Add or update property from text input (format: propname, value)"
    
    def execute(self, context):
        try:
            active_obj, active_type = get_class(context.active_object, False, context)
        except:
            self.report({'ERROR'}, "No active object!")
            return {'CANCELLED'}
        
        text_input = context.scene.text_of_prop.strip()
        if not text_input:
            self.report({'ERROR'}, "Text input is empty")
            return {'CANCELLED'}
        
        # Check for target assignment syntax
        if text_input.startswith('target->') or text_input.startswith('target<-'):
            return self.handle_target_assignment(context, text_input, active_obj)
        
        if text_input.startswith('target2->') or text_input.startswith('target2<-'):
            return self.handle_target_assignment2(context, text_input, active_obj)
        
        # Check if the entire input is just a copy command
        if text_input.lower().startswith('get '):
            prop_name = text_input[4:].strip()
            if prop_name and prop_name in active_obj:
                value = str(active_obj[prop_name])
                context.scene.text_of_prop = value
                self.report({'INFO'}, f"Copied {prop_name} to textbox")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Property '{prop_name}' not found")
                return {'CANCELLED'}
            
        if text_input.lower().startswith('? '):
            # Single ? command - find references
            search_value = text_input[2:].strip()
            
            if not search_value:
                self.report({'ERROR'}, "No value specified")
                return {'CANCELLED'}
            
            if not active_obj:
                self.report({'ERROR'}, "No active object selected")
                return {'CANCELLED'}
            
            selected_count = 0
            
            # Check what type of property the value belongs to on active object
            if ('target' in active_obj and active_obj['target'] == search_value) or \
            ('target2' in active_obj and active_obj['target2'] == search_value):
                # Value is a target/target2 - find objects/collections that are targeted (targetname/targetname2)
                for obj in bpy.data.objects:
                    if ('targetname' in obj and obj['targetname'] == search_value) or \
                    ('targetname2' in obj and obj['targetname2'] == search_value):
                        obj.select_set(True)
                        selected_count += 1
                
                # Also check collections
                for coll in bpy.data.collections:
                    if ('targetname' in coll and coll['targetname'] == search_value) or \
                    ('targetname2' in coll and coll['targetname2'] == search_value):
                        # Select all objects in this collection
                        for obj in coll.objects:
                            if obj.type in {'MESH', 'EMPTY'}:
                                obj.select_set(True)
                                selected_count += 1
                
                self.report({'INFO'}, f"Selected {selected_count} objects targeted by '{search_value}'")
            
            elif ('targetname' in active_obj and active_obj['targetname'] == search_value) or \
                ('targetname2' in active_obj and active_obj['targetname2'] == search_value):
                # Value is a targetname/targetname2 - find objects/collections that target them (target/target2)
                for obj in bpy.data.objects:
                    if ('target' in obj and obj['target'] == search_value) or \
                    ('target2' in obj and obj['target2'] == search_value):
                        obj.select_set(True)
                        selected_count += 1
                
                # Also check collections
                for coll in bpy.data.collections:
                    if ('target' in coll and coll['target'] == search_value) or \
                    ('target2' in coll and coll['target2'] == search_value):
                        # Select all objects in this collection
                        for obj in coll.objects:
                            if obj.type in {'MESH', 'EMPTY'}:
                                obj.select_set(True)
                                selected_count += 1
                
                self.report({'INFO'}, f"Selected {selected_count} objects targeting '{search_value}'")
            
            else:
                # Check if the value matches any property on active object's collections
                found_in_collection = False
                for coll in active_obj.users_collection:
                    if ('target' in coll and coll['target'] == search_value) or \
                    ('target2' in coll and coll['target2'] == search_value):
                        # Find objects/collections with targetname/targetname2 matching this value
                        for obj in bpy.data.objects:
                            if ('targetname' in obj and obj['targetname'] == search_value) or \
                            ('targetname2' in obj and obj['targetname2'] == search_value):
                                obj.select_set(True)
                                selected_count += 1
                        
                        for coll2 in bpy.data.collections:
                            if ('targetname' in coll2 and coll2['targetname'] == search_value) or \
                            ('targetname2' in coll2 and coll2['targetname2'] == search_value):
                                # Select all objects in this collection
                                for obj in coll2.objects:
                                    if obj.type in {'MESH', 'EMPTY'}:
                                        obj.select_set(True)
                                        selected_count += 1
                        
                        found_in_collection = True
                        self.report({'INFO'}, f"Selected {selected_count} objects targeted by '{search_value}' (from collection)")
                        break
                    
                    elif ('targetname' in coll and coll['targetname'] == search_value) or \
                        ('targetname2' in coll and coll['targetname2'] == search_value):
                        # Find objects/collections with target/target2 matching this value
                        for obj in bpy.data.objects:
                            if ('target' in obj and obj['target'] == search_value) or \
                            ('target2' in obj and obj['target2'] == search_value):
                                obj.select_set(True)
                                selected_count += 1
                        
                        for coll2 in bpy.data.collections:
                            if ('target' in coll2 and coll2['target'] == search_value) or \
                            ('target2' in coll2 and coll2['target2'] == search_value):
                                # Select all objects in this collection
                                for obj in coll2.objects:
                                    if obj.type in {'MESH', 'EMPTY'}:
                                        obj.select_set(True)
                                        selected_count += 1
                        
                        found_in_collection = True
                        self.report({'INFO'}, f"Selected {selected_count} objects targeting '{search_value}' (from collection)")
                        break
                
                if not found_in_collection:
                    self.report({'ERROR'}, f"Value '{search_value}' not found in target properties of the active object or its collections")
                    return {'CANCELLED'}
            
            return {'FINISHED'}

        elif text_input.lower().startswith('?? '):
            # Double ?? command - find objects with same property values
            search_value = text_input[3:].strip()
            
            if not search_value:
                self.report({'ERROR'}, "No value specified")
                return {'CANCELLED'}
            
            if not active_obj:
                self.report({'ERROR'}, "No active object selected")
                return {'CANCELLED'}
            
            selected_count = 0
            
            # Check what type of property the value belongs to on active object
            if 'team' in active_obj and active_obj['team'] == search_value:
                # Value is a team - find all objects/collections with same team
                for obj in bpy.data.objects:
                    if 'team' in obj and obj['team'] == search_value:
                        obj.select_set(True)
                        selected_count += 1
                
                for coll in bpy.data.collections:
                    if 'team' in coll and coll['team'] == search_value:
                        # Select all objects in this collection
                        for obj in coll.objects:
                            if obj.type in {'MESH', 'EMPTY'}:
                                obj.select_set(True)
                                selected_count += 1
                
                self.report({'INFO'}, f"Selected {selected_count} objects with team '{search_value}'")
            
            elif ('target' in active_obj and active_obj['target'] == search_value) or \
                ('target2' in active_obj and active_obj['target2'] == search_value):
                # Value is a target/target2 - find all objects/collections with same target/target2
                for obj in bpy.data.objects:
                    if ('target' in obj and obj['target'] == search_value) or \
                    ('target2' in obj and obj['target2'] == search_value):
                        obj.select_set(True)
                        selected_count += 1
                
                for coll in bpy.data.collections:
                    if ('target' in coll and coll['target'] == search_value) or \
                    ('target2' in coll and coll['target2'] == search_value):
                        # Select all objects in this collection
                        for obj in coll.objects:
                            if obj.type in {'MESH', 'EMPTY'}:
                                obj.select_set(True)
                                selected_count += 1
                
                self.report({'INFO'}, f"Selected {selected_count} objects with target/target2 '{search_value}'")
            
            elif ('targetname' in active_obj and active_obj['targetname'] == search_value) or \
                ('targetname2' in active_obj and active_obj['targetname2'] == search_value):
                # Value is a targetname/targetname2 - find all objects/collections with same targetname/targetname2
                for obj in bpy.data.objects:
                    if ('targetname' in obj and obj['targetname'] == search_value) or \
                    ('targetname2' in obj and obj['targetname2'] == search_value):
                        obj.select_set(True)
                        selected_count += 1
                
                for coll in bpy.data.collections:
                    if ('targetname' in coll and coll['targetname'] == search_value) or \
                    ('targetname2' in coll and coll['targetname2'] == search_value):
                        # Select all objects in this collection
                        for obj in coll.objects:
                            if obj.type in {'MESH', 'EMPTY'}:
                                obj.select_set(True)
                                selected_count += 1
                
                self.report({'INFO'}, f"Selected {selected_count} objects with targetname/targetname2 '{search_value}'")
            
            else:
                # Check if the value matches any property on active object's collections
                found_in_collection = False
                for coll in active_obj.users_collection:
                    if 'team' in coll and coll['team'] == search_value:
                        # Find all objects/collections with same team
                        for obj in bpy.data.objects:
                            if 'team' in obj and obj['team'] == search_value:
                                obj.select_set(True)
                                selected_count += 1
                        
                        for coll2 in bpy.data.collections:
                            if 'team' in coll2 and coll2['team'] == search_value:
                                # Select all objects in this collection
                                for obj in coll2.objects:
                                    if obj.type in {'MESH', 'EMPTY'}:
                                        obj.select_set(True)
                                        selected_count += 1
                        
                        found_in_collection = True
                        self.report({'INFO'}, f"Selected {selected_count} objects with team '{search_value}' (from collection)")
                        break
                    
                    elif ('target' in coll and coll['target'] == search_value) or \
                        ('target2' in coll and coll['target2'] == search_value):
                        # Find all objects/collections with same target/target2
                        for obj in bpy.data.objects:
                            if ('target' in obj and obj['target'] == search_value) or \
                            ('target2' in obj and obj['target2'] == search_value):
                                obj.select_set(True)
                                selected_count += 1
                        
                        for coll2 in bpy.data.collections:
                            if ('target' in coll2 and coll2['target'] == search_value) or \
                            ('target2' in coll2 and coll2['target2'] == search_value):
                                # Select all objects in this collection
                                for obj in coll2.objects:
                                    if obj.type in {'MESH', 'EMPTY'}:
                                        obj.select_set(True)
                                        selected_count += 1
                        
                        found_in_collection = True
                        self.report({'INFO'}, f"Selected {selected_count} objects with target/target2 '{search_value}' (from collection)")
                        break
                    
                    elif ('targetname' in coll and coll['targetname'] == search_value) or \
                        ('targetname2' in coll and coll['targetname2'] == search_value):
                        # Find all objects/collections with same targetname/targetname2
                        for obj in bpy.data.objects:
                            if ('targetname' in obj and obj['targetname'] == search_value) or \
                            ('targetname2' in obj and obj['targetname2'] == search_value):
                                obj.select_set(True)
                                selected_count += 1
                        
                        for coll2 in bpy.data.collections:
                            if ('targetname' in coll2 and coll2['targetname'] == search_value) or \
                            ('targetname2' in coll2 and coll2['targetname2'] == search_value):
                                # Select all objects in this collection
                                for obj in coll2.objects:
                                    if obj.type in {'MESH', 'EMPTY'}:
                                        obj.select_set(True)
                                        selected_count += 1
                        
                        found_in_collection = True
                        self.report({'INFO'}, f"Selected {selected_count} objects with targetname/targetname2 '{search_value}' (from collection)")
                        break
                
                if not found_in_collection:
                    self.report({'ERROR'}, f"Value '{search_value}' not found in properties of the active object or its collections")
                    return {'CANCELLED'}
            
            return {'FINISHED'}
                                
        # Process each line for other commands
        for line in text_input.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue
            
            # Check for delete all command
            if line.lower().strip() == 'del all':
                # Get all custom property keys
                custom_props = [key for key in active_obj.keys() 
                               if not key.startswith(('_', 'cycles_', 'rna_')) and key not in active_obj.bl_rna.properties]
                
                if custom_props:
                    # Delete all custom properties
                    for prop_name in custom_props:
                        del active_obj[prop_name]
                    self.report({'INFO'}, f"Deleted all {len(custom_props)} custom properties")
                else:
                    self.report({'WARNING'}, "No custom properties to delete")
                continue
            
            # Check for delete command - handle multiple properties separated by commas
            if line.lower().startswith('del '):
                prop_names_str = line[4:].strip()
                if prop_names_str:
                    # Split by comma and remove any empty strings
                    prop_names = [name.strip() for name in prop_names_str.split(',') if name.strip()]
                    
                    deleted_count = 0
                    for prop_name in prop_names:
                        if prop_name in active_obj:
                            del active_obj[prop_name]
                            deleted_count += 1
                    
                    if deleted_count > 0:
                        self.report({'INFO'}, f"Deleted {deleted_count} properties")
                    else:
                        self.report({'WARNING'}, "No matching properties found to delete")
                continue
            


            if text_input.startswith('!') and (',' in text_input or ':' in text_input):
                # Batch property assignment: !prop, value
                parts = text_input[1:].split(',', 1) if ',' in text_input else text_input[1:].split(':', 1)
                
                if len(parts) != 2:
                    self.report({'ERROR'}, "Invalid format. Use: !property, value")
                    return {'CANCELLED'}
                
                prop_name = parts[0].strip()
                prop_value_str = parts[1].strip()
                
                if not prop_name:
                    self.report({'ERROR'}, "No property name specified")
                    return {'CANCELLED'}
                
                selected_objects = context.selected_objects
                if not selected_objects:
                    self.report({'ERROR'}, "No objects selected")
                    return {'CANCELLED'}
                
                processed_count = 0
                
                # Parse the property value (supporting references and math operations)
                try:
                    # Check if the value is a reference to another property
                    if prop_value_str.startswith('(') and prop_value_str.endswith(')'):
                        # Reference syntax: !team, (other_prop)
                        ref_content = prop_value_str[1:-1].strip()
                        
                        # Get reference value from active object (or its class)
                        ref_value = None
                        active_class_obj, _ = get_class(context.active_object, False, context)
                        
                        if ref_content in active_class_obj:
                            ref_value = active_class_obj[ref_content]
                        else:
                            # Try to find in collections or scene
                            for coll in context.active_object.users_collection:
                                if ref_content in coll:
                                    ref_value = coll[ref_content]
                                    break
                            else:
                                # Try scene
                                if ref_content in context.scene:
                                    ref_value = context.scene[ref_content]
                        
                        if ref_value is not None:
                            final_value = ref_value
                        else:
                            self.report({'ERROR'}, f"Referenced property '{ref_content}' not found")
                            return {'CANCELLED'}
                            
                    else:
                        # Regular value assignment with type conversion
                        if prop_value_str.isdigit():
                            final_value = int(prop_value_str)
                        elif prop_value_str.replace('.', '', 1).isdigit() and prop_value_str.count('.') < 2:
                            final_value = float(prop_value_str)
                        elif prop_value_str.lower() in ('true', 'false'):
                            final_value = prop_value_str.lower() == 'true'
                        else:
                            final_value = prop_value_str
                            
                except Exception as e:
                    self.report({'ERROR'}, f"Error parsing value: {str(e)}")
                    return {'CANCELLED'}
                
                # Apply the property to all selected objects (using their appropriate class)
                for obj in selected_objects:
                    try:
                        # Get the appropriate class (object, collection, or scene) for this object
                        class_obj, _ = get_class(obj, False, context)
                        
                        # Set the property
                        class_obj[prop_name] = final_value
                        processed_count += 1
                        
                    except Exception as e:
                        self.report({'WARNING'}, f"Could not set property on {obj.name}: {str(e)}")
                
                # Clear the input field
                context.scene.text_of_prop = ""
                
                # Report results
                self.report({'INFO'}, f"Set {prop_name} on {processed_count} objects/collections")
                return {'FINISHED'}


            # Parse property assignment
            if ',' in line:
                parts = line.split(',', 1)
            elif ':' in line:
                parts = line.split(':', 1)
            else:
                continue

            if len(parts) != 2:
                continue

            prop_name = parts[0].strip()
            prop_value_str = parts[1].strip()

            if not prop_name:
                continue

            # Check if the value is a reference to another property (enclosed in parentheses)
            if prop_value_str.startswith('(') and prop_value_str.endswith(')'):
                # Extract the referenced property name
                ref_prop_name = prop_value_str[1:-1].strip()
                
                # Get the value from the referenced property
                try:
                    if ref_prop_name in active_obj:
                        # Copy value from another property on the same object
                        active_obj[prop_name] = active_obj[ref_prop_name]
                    else:
                        # Try to find the referenced property in collections
                        found = False
                        for coll in active_obj.users_collection:
                            if ref_prop_name in coll:
                                active_obj[prop_name] = coll[ref_prop_name]
                                found = True
                                break
                        
                        if not found:
                            self.report({'WARNING'}, f"Referenced property '{ref_prop_name}' not found")
                except Exception as e:
                    self.report({'ERROR'}, f"Error copying property value: {str(e)}")

            else:
                # Regular value assignment
                try:
                    if prop_value_str.isdigit():
                        active_obj[prop_name] = int(prop_value_str)
                    elif prop_value_str.replace('.', '', 1).isdigit() and prop_value_str.count('.') < 2:
                        active_obj[prop_name] = float(prop_value_str)
                    elif prop_value_str.lower() in ('true', 'false'):
                        active_obj[prop_name] = prop_value_str.lower() == 'true'
                    else:
                        active_obj[prop_name] = prop_value_str
                except Exception as e:
                    self.report({'ERROR'}, f"Error setting property '{prop_name}': {str(e)}")

            # Clear the input field after processing other commands
            context.scene.text_of_prop = ""
        
        return {'FINISHED'}
    
    def handle_target_assignment(self, context, text_input, active_obj):
        """Handle the target-> and target<- syntax for multiple objects"""
        selected_objects = context.selected_objects
        
        if len(selected_objects) < 2:
            self.report({'ERROR'}, "Need at least 2 selected objects for target assignment")
            return {'CANCELLED'}
        
        # Parse the target value
        if '->' in text_input:
            direction = '->'
            value = text_input.split('->', 1)[1].strip()
        elif '<-' in text_input:
            direction = '<-'
            value = text_input.split('<-', 1)[1].strip()
        else:
            self.report({'ERROR'}, "Invalid target syntax. Use 'target-> value' or 'target<- value'")
            return {'CANCELLED'}
        
        if not value:
            self.report({'ERROR'}, "No value specified for target")
            return {'CANCELLED'}
        
        processed_count = 0
        cleared_self_refs = 0
        
        for obj in selected_objects:
            try:
                # Get the appropriate class (object, collection, or scene) for this object
                target_class_obj, _ = get_class(obj, False, context)
                
                if direction == '->':
                    # Active object gets "target", others get "targetname"
                    if obj == context.active_object:
                        # For active object: set target, clear targetname if it would self-reference
                        target_class_obj["target"] = value
                        if "targetname" in target_class_obj and target_class_obj["targetname"] == value:
                            del target_class_obj["targetname"]
                            cleared_self_refs += 1
                    else:
                        # For other objects: set targetname, clear target if it would self-reference
                        target_class_obj["targetname"] = value
                        if "target" in target_class_obj and target_class_obj["target"] == value:
                            del target_class_obj["target"]
                            cleared_self_refs += 1
                
                else:  # direction == '<-'
                    # Active object gets "targetname", others get "target"
                    if obj == context.active_object:
                        # For active object: set targetname, clear target if it would self-reference
                        target_class_obj["targetname"] = value
                        if "target" in target_class_obj and target_class_obj["target"] == value:
                            del target_class_obj["target"]
                            cleared_self_refs += 1
                    else:
                        # For other objects: set target, clear targetname if it would self-reference
                        target_class_obj["target"] = value
                        if "targetname" in target_class_obj and target_class_obj["targetname"] == value:
                            del target_class_obj["targetname"]
                            cleared_self_refs += 1
                
                processed_count += 1
                
            except Exception as e:
                self.report({'WARNING'}, f"Could not process object: {obj.name}")
        
        # Clear the input field
        context.scene.text_of_prop = ""
        
        # Report results
        if cleared_self_refs > 0:
            self.report({'INFO'}, f"Set target properties on {processed_count} objects, cleared {cleared_self_refs} self-references")
        else:
            self.report({'INFO'}, f"Set target properties on {processed_count} objects")
        
        return {'FINISHED'}

    def handle_target_assignment2(self, context, text_input, active_obj):
        """Handle the target-> and target<- syntax for multiple objects"""
        selected_objects = context.selected_objects
        
        if len(selected_objects) < 2:
            self.report({'ERROR'}, "Need at least 2 selected objects for target assignment")
            return {'CANCELLED'}
        
        # Parse the target value
        if '->' in text_input:
            direction = '->'
            value = text_input.split('->', 1)[1].strip()
        elif '<-' in text_input:
            direction = '<-'
            value = text_input.split('<-', 1)[1].strip()
        else:
            self.report({'ERROR'}, "Invalid target syntax. Use 'target2-> value' or 'target2<- value'")
            return {'CANCELLED'}
        
        if not value:
            self.report({'ERROR'}, "No value specified for target")
            return {'CANCELLED'}
        
        processed_count = 0
        cleared_self_refs = 0
        
        for obj in selected_objects:
            try:
                # Get the appropriate class (object, collection, or scene) for this object
                target_class_obj, _ = get_class(obj, False, context)
                
                if direction == '->':
                    # Active object gets "target", others get "targetname"
                    if obj == context.active_object:
                        # For active object: set target, clear targetname if it would self-reference
                        target_class_obj["target2"] = value
                        if "targetname2" in target_class_obj and target_class_obj["targetname2"] == value:
                            del target_class_obj["targetname2"]
                            cleared_self_refs += 1
                    else:
                        # For other objects: set targetname, clear target if it would self-reference
                        target_class_obj["targetname2"] = value
                        if "target2" in target_class_obj and target_class_obj["target2"] == value:
                            del target_class_obj["target2"]
                            cleared_self_refs += 1
                
                else:  # direction == '<-'
                    # Active object gets "targetname", others get "target"
                    if obj == context.active_object:
                        # For active object: set targetname, clear target if it would self-reference
                        target_class_obj["targetname2"] = value
                        if "target2" in target_class_obj and target_class_obj["target2"] == value:
                            del target_class_obj["target2"]
                            cleared_self_refs += 1
                    else:
                        # For other objects: set target, clear targetname if it would self-reference
                        target_class_obj["target2"] = value
                        if "targetname2" in target_class_obj and target_class_obj["targetname2"] == value:
                            del target_class_obj["targetname2"]
                            cleared_self_refs += 1
                
                processed_count += 1
                
            except Exception as e:
                self.report({'WARNING'}, f"Could not process object: {obj.name}")
        
        # Clear the input field
        context.scene.text_of_prop = ""
        
        # Report results
        if cleared_self_refs > 0:
            self.report({'INFO'}, f"Set target properties on {processed_count} objects, cleared {cleared_self_refs} self-references")
        else:
            self.report({'INFO'}, f"Set target properties on {processed_count} objects")
        
        return {'FINISHED'}

class MESH_OT_add_bounding_box_vertices(bpy.types.Operator):
    """Add vertices at the corners of the mesh's bounding box"""
    bl_idname = "mesh.add_bounding_box_vertices"
    bl_label = "Add Bounding Box Vertices"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the active object
        obj = context.active_object
        grid_size = float(context.scene.grid_size)
        snap = context.scene.snap
        original_grid = bpy.context.space_data.overlay.grid_scale
        
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        original_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        # Get the mesh data
        mesh = obj.data
        
        # Calculate world space bounding box corners
        world_matrix = obj.matrix_world
        local_bbox_corners = [Vector(corner) for corner in obj.bound_box]
        world_bbox_corners = [world_matrix @ corner for corner in local_bbox_corners]
        
        # Create a new mesh for the vertices (or add to existing)
        bm = bmesh.new()
        
        # If we want to add vertices to the existing mesh
        if context.mode == 'EDIT_MESH':
            bm = bmesh.from_mesh(mesh)
        
        # Add vertices at each corner
        for corner in world_bbox_corners:
            # Convert world space to local space for the mesh
            local_pos = obj.matrix_world.inverted() @ corner
            bm.verts.new(local_pos)
                           
        # Update the mesh
        bm.to_mesh(mesh)
        bm.free()
        
        # Update the viewport
        mesh.update()
        if snap:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')          
            bpy.context.space_data.overlay.grid_scale = grid_size
            bpy.ops.view3d.snap_selected_to_grid()
            bpy.context.space_data.overlay.grid_scale = original_grid
            bpy.ops.mesh.select_all(action='DESELECT')

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.uv_texture_add()        
        bpy.ops.object.mode_set(mode=original_mode)
        return {'FINISHED'}
        
def cleanup_floating_verts(obj):
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    # Iterate over the vertices
    for v in bm.verts:
        # Check if the vertex has no edges connected to it
        if len(v.link_edges) == 0:
            v.select_set(True)
        print(len(v.link_edges))
    bmesh.update_edit_mesh(mesh)
    bm.free()

class OBJECT_PT_snap_all_to_grid_panel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Trenchcoat"
    bl_idname = "OBJECT_PT_snap_all_to_grid"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Trenchcoat'

    def draw(self, context):

        layout = self.layout
        obj = context.active_object
        snapset1 = context.scene.snapset1
        gridsteps = context.scene.gridsteps
        version_str = ".".join(map(str, bl_info["version"]))
        version = layout.row()
        version.label(text=f"Version {version_str}")
        if obj is not None:
            box = layout.box()
            row = box.row(align=True)
            row.label(text="Grid Size")
            row.prop(context.scene, "grid_size", text = "")
            if context.scene.snap:
                row.prop(context.scene, "snap", text = "", icon="SNAP_ON", toggle=True)
            else:
                row.prop(context.scene, "snap", text = "", icon="SNAP_OFF", toggle=True)            
            if bpy.context.object.mode == 'EDIT':               
                row = box.row(align=True)
                row.operator("object.snap_selected_to_grid", text = "Snap Vertices to Grid", icon="SNAP_GRID")
                if context.scene.snap_alone:
                    row.prop(context.scene, "snap_alone", text = "", icon="TRACKER", toggle=True)
                else:
                    row.prop(context.scene, "snap_alone", text = "", icon="TRACKER", toggle=True)               
            elif obj.type == 'MESH' and obj.data and len(obj.data.vertices) > 0:
                row = box.row(align=True)
                row.operator("object.snap_selected_to_grid", text = "Snap Vertices to Grid", icon="SNAP_GRID")  
            else:
                row = box.row(align=True)
                row.operator("object.snap_selected_to_grid", text = "Snap Entity to Grid", icon="SNAP_GRID")
            row = box.row(align=True)
            row.operator("object.convexhull_brush", text = "Make Brush", icon="SNAP_VOLUME")  
            row.prop(context.scene, "hintcage", text = "", icon="MESH_ICOSPHERE", toggle=True)          
            if context.scene.automerge:
                row.prop(context.scene, "automerge", text = "", icon="AUTOMERGE_ON", toggle=True)
            else:
                row.prop(context.scene, "automerge", text = "", icon="AUTOMERGE_OFF", toggle=True)
            row = box.row(align=True)
            row.prop(context.scene, "material", text = "")
            row.operator("object.apply_material", text = "", icon="MATERIAL")
            row.operator("object.duplicate_material", text = "", icon="PLUS")
            row.operator("object.delete_material", text = "", icon="TRASH")
            row = box.row(align=True)

            if bpy.context.object.mode == 'OBJECT':
                row = box.row(align=True)
                row.label(text="Spawn:")
                row.operator("object.create_player_cube", text = "Player", icon="OUTLINER_OB_ARMATURE")
                row.operator("object.create_item_cube", text = "Item", icon="GEOMETRY_SET")
                row.operator("object.create_entity_cube", text = "Entity", icon="TRACKER")
                row = layout.row(align=True)
                row.scale_x = 2.3
                if len(context.selected_objects) > 0 and len([o for o in context.selected_objects if o.type == 'MESH']) == len(context.selected_objects):
                    row.operator("object.duplicate_shared", text = "Symmetrize", icon="MOD_MIRROR")
                    split = row.split(factor=1.0)
                    split.prop(context.scene, "mirror_axis", text = "")                    
                    split = row.split(factor=0.55)
                    split.prop(context.scene, "invasive_mirror", text = "", icon="SNAP_PEEL_OBJECT", toggle=True)
            row = layout.row(align=True)
            split = row.split(factor=0.72)
            split.operator("mesh.add_bounding_box_vertices", text = "Shape To Bounding Box", icon="FULLSCREEN_ENTER")
            split.operator("object.create_skybox", text = "Room", icon="MOD_SOLIDIFY")
            box2 = layout.box()
            row = box2.row()
            row.label(text="Set Origin To:")
            row = box2.row(align=True)
            if bpy.context.object.mode == 'EDIT':
                row.operator("object.set_origin_to_selected", text = "Vertex")
            else:
                if len(context.selected_objects) > 1 and len([o for o in context.selected_objects if o.type == 'MESH']) == len(context.selected_objects):
                    row.operator("object.set_origin_to_active", text = "Active")                
            row.operator("object.set_origin_to_median", text = "Geometry")
            row.operator("object.set_origin_to_world", text = "World")                    
            row = layout.row(align=True)
        elif obj is None or obj.type != 'MESH':
            row = layout.row(align=True)
            row.label(text="No object selected")
            row = layout.row(align=True)
            row.operator("object.create_player_cube", text = "+Player", icon="OUTLINER_OB_ARMATURE")
            row.operator("object.create_item_cube", text = "+Item", icon="GEOMETRY_SET")
            row.operator("object.create_entity_cube", text = "+Entity", icon="TRACKER")
            
        row = layout.row(align=True)
        row.label(text="Shortcuts:")
        row = layout.row(align=True)
        if context.scene.shrt_obj_col:
            row.alert = True
        else:
            row.alert = False
        row.operator("object.trenchcoat_shortcuts_objcol", text = "NoHull", icon="GHOST_ENABLED")
        if context.scene.shrt_xray:
            row.alert = True
        else:
            row.alert = False
        row.operator("object.trenchcoat_shortcuts_xray", text = "XRay", icon="MOD_WIREFRAME")
        if context.scene.shrt_pivot_cursor:
            row.alert = True
        else:
            row.alert = False
        row.operator("object.trenchcoat_shortcuts_pivot_cursor", text = "Pivot", icon="PIVOT_CURSOR")
        row = layout.row(align=True)
        split = row.split(factor=0.60)
        is_in_front = obj and obj.show_in_front if obj else False
        if is_in_front:
            split.alert = True
            split.operator("object.popfront", text = "In Front On/Off", icon="ZOOM_SELECTED")
        else:
            split.operator("object.popfront", text = "In Front On/Off", icon="ZOOM_SELECTED")
        split.alert = False
        split.operator("object.popfront_reset", text = "", icon="ZOOM_PREVIOUS")
        if global_list_of_things == []:
            split.operator("object.solo_brush", text=f"Solo", icon="HIDE_OFF")
        else:
            split.operator("object.solo_brush", text=f"Reset", icon="HIDE_ON")

        row = layout.row(align=True)
        split = row.split(factor=0.60)
        if snapset1:
            split.alert = True
            if bpy.context.space_data.overlay.grid_scale == float(bpy.context.scene.grid_size):
                split.operator("object.trenchcoat_shortcuts_increment", text=f"Move on Grid", icon="SNAP_INCREMENT")
            else:
                split.operator("object.trenchcoat_shortcuts_increment", text=f"Out of Sync!", icon="SNAP_INCREMENT")
        else:
            split.alert = False
            split.operator("object.trenchcoat_shortcuts_increment", text=f"Move on Grid", icon="SNAP_INCREMENT")
        
        split.alert = False
        split.operator("object.gridstancecalc", text=f"{context.scene.gridsteps:.1f}", icon="DRIVER_DISTANCE")       
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Output:")
        row = box.row(align=True)
        row.operator("export.map", text = "Export .map", icon="MOD_BUILD")

        layout = self.layout
        row = layout.row()
        row.label(text="Inspector:")
        if context.active_object:
            obj, type = get_class(context.active_object, False, context)
            row = layout.row(align=True)
            if type != 'excluded':
                if type == 'worldspawn':
                    row = layout.row()
                    row.label(text=f"Selected: {obj.name}")
                    row = layout.row()
                    row.label(text=f"Type: worldspawn brush")
                    row = layout.row()
                    row.label(text=f"Class: worldspawn")
                elif type == "brush_ent_group":
                    row = layout.row()
                    row.label(text=f"Selected: {obj.name}")
                    row = layout.row()
                    row.label(text=f"Type: group entity")
                    row = layout.row()
                    collection_name = obj.name.split('.')[0]
                    row.label(text=f"Class: {collection_name}")
                elif type == "brush_ent":
                    row = layout.row()
                    row.label(text=f"Selected: {obj.name}")
                    row = layout.row()
                    row.label(text=f"Type: brush entity")
                    row = layout.row()
                    obj_name = obj.name.split('.')[0]
                    row.label(text=f"Class: {obj_name}")
                elif type == "point_ent":
                    row = layout.row()
                    row.label(text=f"Selected: {obj.name}")
                    row = layout.row()
                    row.label(text=f"Type: point entity")
                    row = layout.row()
                    obj_name = obj.name.split('.')[0]
                    row.label(text=f"Class: {obj_name}")
                else:
                    row = layout.row()
                    row.label(text=f"Selected: {obj.name}")
                    row = layout.row()
                    row.label(text=f"Type: none")
                    row = layout.row()
                    obj_name = obj.name.split('.')[0]
                    row.label(text=f"Class: none")
            else:
                    row = layout.row()
                    row.label(text=f"Selected: {obj.name}")
                    row = layout.row()
                    row.label(text=f"Type: excluded on export")
                    row = layout.row()
                    obj_name = obj.name.split('.')[0]
                    row.label(text=f"Class: unused")
            row = layout.row(align=True)
            row.prop(context.scene, "text_of_prop")
            row.operator("object.add_property_from_text", text = "", icon="CHECKMARK")
            custom_props = {key: obj[key] for key in obj.keys() 
                        if not key.startswith(('_', 'cycles_', 'rna_')) and key not in obj.bl_rna.properties}
            if custom_props:
                for key, value in custom_props.items():
                    row = layout.row()
                    row.label(text=f"{key}: {value}")                                
        else:
            row = layout.row()
            row.label(text="No object selected")
       
classes = (
    OBJECT_PT_snap_all_to_grid_panel, #Panel
    OBJECT_OT_snap_selected_to_grid,
    OBJECT_OT_snap_ori,
    ConvexHullBrush,
    CreatePlayerCube,
    CreateEntityCube,
    CreateItemCube,
    DuplicateObjectOperator,
    TCShortcuts_OBJCOL,
    TCShortcuts_XRAY,
    TCShortcuts_PIVOTCURSOR,
    SnapOriginToCenter,
    SnapOriginToMedian,
    ApplyMaterial,
    SnapOriginToActive,
    MESH_OT_add_bounding_box_vertices,
    ExportQuakeMap,
    Popfront,
    Popfront_Reset,
    CalcGridstance,
    TCShortcuts_INCREMENT,
    Solo_brush,
    OBJECT_OT_AddPropertyFromText,
    DuplicateMaterial,
    DeleteMaterial,
    CreateSkyBox

)

def menu_func_export(self, context):
    self.layout.operator(ExportQuakeMap.bl_idname, text="Quake Map (.map)")

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.Scene.text_of_prop = bpy.props.StringProperty(name="", default="", description="commands:\n[<key>, <value>] to set key and value pairs\n[<key>, (<key>)] to assign other key's value\n[!<key>, value] sets key and value on all selected entities\n[del <key>, <key2>, etc.] to delete keys\n[del all] to delete all keys\n[get <key>] to return key's value into the text box\n[target<- <name>] to set target and targetname on selected objects, target being self.\n[target-> <name>] to set target and targetname on selected objects, target being others\n[? <name>] select referenced entities\n[?? <name>] select similar purpose entities")
    bpy.types.Scene.snapset1 = bpy.props.BoolProperty(name="Snapset1", default=False, description="Snapping set 1")
    bpy.types.Scene.hintcage = bpy.props.BoolProperty(name="Hint Cage", default=False, description="Generate Convex Hint Cage On Brush")
    bpy.types.Scene.gridsteps = FloatProperty(name="Steps", default=5.0, description="Steps to take")
    bpy.types.Scene.automerge = bpy.props.BoolProperty(name="Merge Selected", default=True, description="Merge all selected objects into one brush")
    bpy.types.Scene.snap = bpy.props.BoolProperty(name="Snap to Grid", default=True, description="Automatically snaps to grid on brush conversion. Snapping ensures best conversion, but distorts rotation of mesh")
    bpy.types.Scene.invasive_mirror = bpy.props.BoolProperty(name="Use Active Object", default=True, description="Uses the active object's bounding box to set new origins")
    bpy.types.Scene.snap_alone = bpy.props.BoolProperty(name="Only selected", default=False, description="Snap only the selected vertices")
    bpy.types.Scene.mirror_axis = bpy.props.EnumProperty(name="Mirror Axis", description="Which axis to mirror onto", items=[("x", "X", ""),("y", "Y", ""), ("z", "Z", "")], default="x")
    bpy.types.Scene.shrt_snap = bpy.props.BoolProperty(name="Snap", default=False, description="Snap to Grid")
    bpy.types.Scene.shrt_proport = bpy.props.BoolProperty(name="Proportional Edit", default=False, description="Proportional Edit")
    bpy.types.Scene.shrt_xray = bpy.props.BoolProperty(name="X-Ray", default=False, description="X-Ray")
    bpy.types.Scene.shrt_obj_col = bpy.props.BoolProperty(name="Object Color", default=False, description="Object Color")
    bpy.types.Scene.material = bpy.props.PointerProperty(type=bpy.types.Material)
    bpy.types.Scene.shrt_pivot_cursor = bpy.props.BoolProperty(name="Pivot Cursor", default=False, description="Pivot Cursor")
    bpy.types.Scene.grid_size = bpy.props.EnumProperty(
        name="Grid Size",
        description="The Grid's size which to snap to",
        items=[
            ('0.125', "0.125", ""),
            ('0.25', "0.25", ""),
            ('0.5', "0.5", ""),
            ('1', "1", ""),
            ('2', "2", ""),
            ('4', "4", ""),
            ('8', "8", ""),
            ('16', "16", ""),
            ('32', "32", ""),
            ('64', "64", ""),
            ('128', "128", ""),
            ('256', "256", ""),
            ('512', "512", ""),
            ('1024', "1024", ""),
        ],
        default='0.25'
    )
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    del bpy.types.Scene.snapset1
    del bpy.types.Scene.automerge
    del bpy.types.Scene.snap
    del bpy.types.Scene.gridsteps
    del bpy.types.Scene.grid_size
    del bpy.types.Scene.mirror_axis
    del bpy.types.Scene.invasive_mirror
    del bpy.types.Scene.shrt_snap
    del bpy.types.Scene.shrt_proport
    del bpy.types.Scene.shrt_xray
    del bpy.types.Scene.shrt_obj_col
    del bpy.types.Scene.material
    del bpy.types.Scene.shrt_pivot_cursor
    del bpy.types.Scene.hintcage
    del bpy.types.Scene.text_of_prop



if __name__ == "__main__":
    register()