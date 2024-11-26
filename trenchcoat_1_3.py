bl_info = {
    "name": "Trenchcoat",
    "version": (1, 3, 0),
    "blender": (4, 00, 0),
    "category": "Object",
    "location": "3D View > Sidebar > Tool > Trenchcoat",
    "description": "BSP like structure builder",
    "author": "Uzugijin",
}

import bpy
import mathutils
import bmesh

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

def add_geonode_to_object(obj, name):
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
                        add_convex_hull_node(modifier.node_group)

class DuplicateObjectOperator(bpy.types.Operator):
    bl_idname = "object.duplicate_shared"
    bl_label = "Duplicate Object (Shared Mesh)"
    bl_description = "Makes a linked mirrored duplicate"
    bl_options = {'UNDO'}

    def execute(self, context):
        #deselect all objects
        obj = bpy.context.active_object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        obj_location = obj.location.copy()
        if context.scene.world_center == True:       
            bpy.context.scene.cursor.location = (0, 0, 0)
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        bpy.ops.object.duplicate_move_linked()
        obj.select_set(False)
        axis_block = []
        if context.scene.mirror_axis == "x":
            axis_block = (True, False, False)
            mirror_axis = 0
        elif context.scene.mirror_axis == "y":
            axis_block = (False, True, False)
            mirror_axis = 1
        elif context.scene.mirror_axis == "z":
            axis_block = (False, False, True)
            mirror_axis = 2
        bpy.ops.transform.mirror(orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(axis_block))
        if context.scene.world_center == False:
            for o in bpy.context.selected_objects:
                if o != obj:
                    location = list(obj_location)
                    location[mirror_axis] = -location[mirror_axis]
                    o.location = tuple(location)

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
        original_grid = bpy.context.space_data.overlay.grid_scale
        grid_size = context.scene.grid_size
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if context.scene.snap_alone == False:
                    bpy.ops.mesh.select_all(action='SELECT')
                bpy.context.space_data.overlay.grid_scale = grid_size
                bpy.ops.view3d.snap_selected_to_grid()
                bpy.context.space_data.overlay.grid_scale = original_grid
                if context.scene.snap_alone == False:
                    bpy.ops.mesh.select_all(action='DESELECT')
        return {'FINISHED'}

#Convert to Mesh Operator:
class ConvertToMesh(bpy.types.Operator):
    bl_idname = "object.convert_to_mesh"
    bl_label = "Convert to Mesh"
    bl_description = "Convert the selected object to a mesh"
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.active_object
        grid_size = context.scene.grid_size
        original_grid = bpy.context.space_data.overlay.grid_scale
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.join()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        if context.scene.snap:
            bpy.context.space_data.overlay.grid_scale = grid_size
            bpy.ops.view3d.snap_selected_to_grid()
            bpy.context.space_data.overlay.grid_scale = original_grid
        bpy.ops.mesh.remove_doubles()       
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.uv.smart_project(island_margin=0.05)
        except:
            self.report({'ERROR'}, "Mesh was too small for snapping!")
        bpy.ops.mesh.select_all(action='DESELECT')
        xray_state = bpy.context.space_data.shading.show_xray
        if xray_state:
            bpy.context.space_data.shading.show_xray = False
        obj["is_brush"] = False
        obj.name = "Mesh"
        obj.data.name = "Mesh"
        return {'FINISHED'}
    
class ConvexHullBrush(bpy.types.Operator):
    bl_idname = "object.convexhull_brush"
    bl_label = "Make Brush"
    bl_description = "Add a Convex Hull node to the selected joined object"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Get the active object
        obj = context.active_object
        grid_size = context.scene.grid_size
        snap = context.scene.snap
        original_grid = bpy.context.space_data.overlay.grid_scale
        if obj.type == 'MESH':
            if context.scene.automerge:
                bpy.ops.object.join()
                bpy.ops.object.convert(target='MESH')
                
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            if snap:
                bpy.context.space_data.overlay.grid_scale = grid_size
                bpy.ops.view3d.snap_selected_to_grid()
                bpy.context.space_data.overlay.grid_scale = original_grid
            bpy.ops.mesh.delete(type='EDGE_FACE')
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
            #bpy.ops.object.mode_set(mode='OBJECT')
            xray_state = bpy.context.space_data.shading.show_xray
            if xray_state == False:
                bpy.context.space_data.shading.show_xray = True

            add_geonode_to_object(obj, "ConvexHullBrush")

        #TODO: Handling curves
        # elif obj.type == 'CURVE':
        #     modifier = obj.modifiers.get("SplitUpCurve")
        #     if modifier is None:
        #         modifier = obj.modifiers.new("SplitUpCurve", 'NODES')
        #         hello = modifier.node_group = bpy.data.node_groups["SplitUpCurve"]
        #         if hello is None:
        #             print("Modifier already exists")
        #             pass
        #     else:
        #         bpy.ops.object.mode_set(mode='OBJECT')
        #         bpy.ops.object.convert(target='MESH')
        #         bpy.ops.object.mode_set(mode='EDIT')
        #         bpy.ops.mesh.select_all(action='SELECT')
        #         bpy.ops.mesh.separate(type='LOOSE')
        #         bpy.ops.object.mode_set(mode='OBJECT')
  
        obj["is_brush"] = True
        obj.name = "Brush"
        obj.data.name = "Brush"
        return {'FINISHED'}

#i will make a crate player cube
class CreatePlayerCube(bpy.types.Operator):
    bl_idname = "object.create_player_cube"
    bl_label = "Promote to Player Size"
    bl_description = "Transform the selected object to a quake 3 playermodel sized box"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Create a new bmesh
        
        grid_size = context.scene.grid_size
        original_grid = bpy.context.space_data.overlay.grid_scale

        try:
                for mesh in bpy.data.meshes:
                    if "Player" in mesh.name:
                        bpy.data.meshes.remove(mesh)
                for obj in bpy.data.objects:
                    if "Player" in obj.name:
                        bpy.data.objects.remove(obj)
        except:
                pass
        obj = bpy.context.active_object        
        if obj is None or obj.type != 'MESH':
            # Create a new object at the 3D cursor
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            mesh = bpy.data.meshes.new("Player")
            bm.to_mesh(mesh)
            obj = bpy.data.objects.new("Player", mesh)
            bpy.context.collection.objects.link(obj)
            obj.select_set(True)
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            #make it the active object
            bpy.context.view_layer.objects.active = obj

        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        bm = bmesh.new()

        # Create a cube with the specified dimensions
        bmesh.ops.create_cube(bm, size=1)
        bm.transform(mathutils.Matrix.Scale(32, 4, (1, 0, 0)))
        bm.transform(mathutils.Matrix.Scale(32, 4, (0, 1, 0)))
        bm.transform(mathutils.Matrix.Scale(56, 4, (0, 0, 1)))
        bm.transform(mathutils.Matrix.Translation((0, 0, 28)))
        # Create a new mesh from the bmesh
        mesh = bpy.data.meshes.new("Player")
        bm.to_mesh(mesh)
        obj.data = mesh

        # Set the object color to red
        obj.color = (1.0, 0.0, 0.0, 1.0)
        obj.name = "Player"
        
        bpy.context.space_data.overlay.grid_scale = grid_size
        bpy.ops.view3d.snap_selected_to_grid()
        bpy.context.space_data.overlay.grid_scale = original_grid

        return {'FINISHED'}

class OBJECT_PT_snap_all_to_grid_panel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Trenchcoat"
    bl_idname = "OBJECT_PT_snap_all_to_grid"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):

        layout = self.layout
        obj = context.active_object
        if obj is not None:
            try:
                modifier = obj.modifiers.get("SplitUpCurve")
            except:
                pass
            if bpy.context.object.mode == 'EDIT':
                box = layout.box()
                box.operator("object.set_origin_to_selected", text = "Set Origin", icon="CURSOR")
                row = box.row(align=True)
                row.operator("object.snap_selected_to_grid", text = "Snap Vertices to Grid", icon="SNAP_GRID")
                if context.scene.snap_alone:
                    row.prop(context.scene, "snap_alone", text = "", icon="TRACKER", toggle=True)
                else:
                    row.prop(context.scene, "snap_alone", text = "", icon="TRACKER", toggle=True)
            else:
                box = layout.box()
                if modifier is not None and obj.type == 'CURVE':
                    box.operator("object.convexhull_brush", text = "2. Apply Split") 
                elif obj.type == 'CURVE':
                    box.operator("object.convexhull_brush", text = "1. Split Curve")
                else:
                    row = box.row(align=True)
                    row.operator("object.convexhull_brush", text = "Make Brush", icon="SNAP_VOLUME")
                    if context.scene.automerge:
                        row.prop(context.scene, "automerge", text = "", icon="AUTOMERGE_ON", toggle=True)
                    else:
                        row.prop(context.scene, "automerge", text = "", icon="AUTOMERGE_OFF", toggle=True)
                    row = box.row(align=True)
                    row.operator("object.convert_to_mesh", text = "Convert to Mesh", icon="MESH_DATA")
                    row = layout.row(align=True)
                    row.operator("object.create_player_cube", text = "Convert to Player Box", icon="USER")
                    row = layout.row(align=True)
                    row.scale_x = 2.3
                    row.operator("object.duplicate_shared", text = "Linked Mirrored", icon="MOD_MIRROR")
                    split = row.split(factor=1.0)
                    split.prop(context.scene, "mirror_axis", text = "")
                    split = row.split(factor=0.55)

                    split.label(text="")
                    split.prop(context.scene, "world_center", text = "", icon="WORLD")
                    
            row = layout.row(align=True)
            row.prop(context.scene, "grid_size", text = "Grid Size")
            if context.scene.snap:
                row.prop(context.scene, "snap", text = "", icon="SNAP_ON", toggle=True)
            else:
                row.prop(context.scene, "snap", text = "", icon="SNAP_OFF", toggle=True)

        elif obj is None or obj.type != 'MESH':
            row = layout.row(align=True)
            row.label(text="No object selected")
            row = layout.row(align=True)
            row.operator("object.create_player_cube", text = "Spawn a Player Box at Cursor", icon="USER")

classes = (
    OBJECT_PT_snap_all_to_grid_panel, #Panel
    OBJECT_OT_snap_selected_to_grid,
    OBJECT_OT_snap_ori,
    ConvexHullBrush,
    ConvertToMesh,
    CreatePlayerCube,
    DuplicateObjectOperator
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    #register properties of autmerge and snap
    bpy.types.Scene.automerge = bpy.props.BoolProperty(name="Merge Selected", default=True, description="Merge all selected objects into one brush")
    bpy.types.Scene.snap = bpy.props.BoolProperty(name="Snap to Grid", default=True, description="Snapping ensures best conversion, but distorts rotation of mesh")
    bpy.types.Scene.snap_alone = bpy.props.BoolProperty(name="Only selected", default=False, description="Snap only the selected vertices")
    bpy.types.Scene.grid_size = bpy.props.IntProperty(
    name="Grid Size",
    default=8,
    min=1,
    max=1024
    )
    bpy.types.Scene.world_center = bpy.props.BoolProperty(name="At World Origin", default=False, description="Mirror the mesh at the world origin")
    bpy.types.Scene.mirror_axis = bpy.props.EnumProperty(name="Mirror Axis", description="Whixh axis to mirror onto", items=[("x", "X", ""),("y", "Y", ""), ("z", "Z", "")], default="x")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.automerge
    del bpy.types.Scene.snap
    del bpy.types.Scene.grid_size
    del bpy.types.Scene.mirror_axis
    del bpy.types.Scene.world_center

if __name__ == "__main__":
    register()
