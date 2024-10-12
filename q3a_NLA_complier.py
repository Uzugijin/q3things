bl_info = {
    "name": "Q3A - NLA Complier",
    "author": "Uzugijin",
    "version": (1, 3, 0),
    "blender": (4, 00, 0),
    "category": "Animation",
    "location": "Nonlinear Animation > Side panel (N) > Q3 Animation Config",
    "description": (
        "Puts actions onto NLA and can mark frames for easier distinction"
    ),
    "doc_url": "https://uzugijin.github.io",
}

import bpy
import os

class Q3AnimationConfigProperties(bpy.types.PropertyGroup):
    selected_object: bpy.props.PointerProperty(name="Armature of model", type=bpy.types.Object, description="Only the NLA track of this armature will be used")
    mark_frames: bpy.props.BoolProperty(name="Mark Frames", default=True, description="Mark the first frame of every strip in the NLA track")
    offset_by_1: bpy.props.BoolProperty(name="Offset By 1", default=True, description="Offset marks by 1 frame")
class Q3AnimationConfigPanel(bpy.types.Panel):
    bl_label = "Q3A NLA Compiler"
    bl_idname = "VIEW3D_PT_q3_animation_config"
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Q3A NLA Compiler'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        q3_props = scene.q3_animation_config
        row = layout.row()
        row.prop(q3_props, "selected_object", text="Armature")
        row = layout.row()
        row.prop(context.scene.q3_animation_config, "mark_frames", text="Mark Frames", toggle=False)
        if context.scene.q3_animation_config.mark_frames:
            row.prop(context.scene.q3_animation_config, "offset_by_1", text="Offset By 1", toggle=True)
        row = layout.row()
        row = layout.row()
        row.operator("q3.import_actions", text="(Re)Compile NLA")

        row = layout.row()
        row.operator("q3.open_cheatsheet", text="Open Cheatsheet")

class Q3OpenCheatsheetOperator(bpy.types.Operator):
    bl_idname = "q3.open_cheatsheet"
    bl_label = "Open Cheatsheet"
    bl_description = "https://icculus.org/gtkradiant/documentation/Model_Manual/model_manual.htm"

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://icculus.org/gtkradiant/documentation/Model_Manual/model_manual.htm")
        return {'FINISHED'}

class Q3ImportActionsOperator(bpy.types.Operator):
    bl_idname = "q3.import_actions"
    bl_label = "Import Actions"
    bl_description = "Compile Actions on NLA for export. All other tracks will be removed on the selected armature."
    def execute(self, context):
        scene = context.scene
        q3_props = scene.q3_animation_config
        obj = q3_props.selected_object

        for obj2 in bpy.data.objects:
            if obj2.animation_data is not None:
                for track in obj2.animation_data.nla_tracks:
                    if track.name == "Q3ANIM":
                        obj2.animation_data.nla_tracks.remove(track)

            # Check if a cube object already exists
        frame_buddy_name = "NLA-Compiler"

        existing_cube = bpy.data.objects.get(frame_buddy_name)
        if existing_cube:
            # Delete the existing cube object and its associated data
            for obj2 in bpy.data.objects:
                if frame_buddy_name in obj2.name:
                    bpy.data.objects.remove(obj2)

            # Delete actions
            for action in bpy.data.actions:
                if frame_buddy_name in action.name:
                    bpy.data.actions.remove(action)

        # Create a cube object
        if q3_props.mark_frames and obj is None:
            bpy.ops.object.empty_add(type='ARROWS', location=(0, 0, 0))
            cube = bpy.context.active_object
            cube.name = frame_buddy_name
            cube.animation_data_create()
            obj = cube
        elif q3_props.mark_frames and obj is not None:
            bpy.ops.object.empty_add(type='ARROWS', location=(0, 0, 0))
            cube = bpy.context.active_object
            cube.name = frame_buddy_name
            cube.animation_data_create()
        elif not q3_props.mark_frames and obj is None:
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
            cube = bpy.context.active_object
            cube.name = frame_buddy_name
            cube.animation_data_create()
            obj = cube
        elif not q3_props.mark_frames and obj is not None:
            pass



        actions = [
            "BOTH_DEATH1", "BOTH_DEAD1", "BOTH_DEATH2", "BOTH_DEAD2", "BOTH_DEATH3", "BOTH_DEAD3",
            "TORSO_GESTURE", "TORSO_ATTACK", "TORSO_ATTACK2", "TORSO_DROP", "TORSO_RAISE", "TORSO_STAND",
            "TORSO_STAND2", "LEGS_WALKCR", "LEGS_WALK", "LEGS_RUN", "LEGS_BACK", "LEGS_SWIM", "LEGS_JUMP",
            "LEGS_LAND", "LEGS_JUMPB", "LEGS_LANDB", "LEGS_IDLE", "LEGS_IDLECR", "LEGS_TURN",
            "TORSO_GETFLAG", "TORSO_GUARDBASE", "TORSO_PATROL", "TORSO_FOLLOWME", "TORSO_AFFIRMATIVE", "TORSO_NEGATIVE"
        ]

        track = obj.animation_data.nla_tracks.new(prev=None)
        track.name = "Q3ANIM"
        frame_offset = 0

        for action_name in actions:
            action = bpy.data.actions.get(action_name)
            if action:
                strip = track.strips.new(action_name, int(frame_offset), action)
                strip.action = action
                frame_offset += strip.frame_end - strip.frame_start

        bpy.context.scene.frame_end = int(frame_offset)

        if q3_props.mark_frames:

            # Create an action for the cube
            cube_action = bpy.data.actions.new(frame_buddy_name + "Action")
            # Initialize variables
            y_offset = 14
            z_offset = 35
            y_direction = 1
            z_direction = 1

            cube.animation_data_create()
            cube.animation_data.action = cube_action


            # Iterate over the NLA strips
            current_frame = bpy.context.scene.frame_current
            for strip in track.strips:
                # Calculate the new Y and Z positions
                new_y = y_offset * y_direction
                new_z = z_offset * z_direction

                # Set the current frame to the strip's start frame
                if q3_props.offset_by_1:
                    bpy.context.scene.frame_set(int(strip.frame_start)+1)
                else:
                    bpy.context.scene.frame_set(int(strip.frame_start))

                # Insert a keyframe for the cube's position
                cube.location = (0, new_y, new_z)
                bpy.ops.anim.keyframe_insert(type='Location')

                # Update the Y and Z directions for the next strip
                y_direction *= -1
                z_direction *= -1
                if z_direction == -1:
                    z_offset = 23
                else:
                    z_offset = 35

            bpy.context.scene.frame_set(current_frame)

            fcurve_x = cube.animation_data.action.fcurves.find('location', index=0)
            fcurve_y = cube.animation_data.action.fcurves.find('location', index=1)
            fcurve_z = cube.animation_data.action.fcurves.find('location', index=2)

            for kp in fcurve_x.keyframe_points:
                kp.interpolation = 'CONSTANT'
            for kp in fcurve_y.keyframe_points:
                kp.interpolation = 'CONSTANT'
            for kp in fcurve_z.keyframe_points:
                kp.interpolation = 'CONSTANT'


        return {'FINISHED'}


classes = (
    Q3AnimationConfigProperties,
    Q3AnimationConfigPanel,
    Q3OpenCheatsheetOperator,
    Q3ImportActionsOperator,
)



def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.q3_animation_config = bpy.props.PointerProperty(type=Q3AnimationConfigProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.q3_animation_config

if __name__ == "__main__":
    register()