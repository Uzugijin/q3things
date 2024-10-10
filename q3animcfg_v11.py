bl_info = {
    "name": "Q3-AnimationConfig",
    "author": "Uzugijin",
    "version": (1, 1, 0),
    "blender": (4, 00, 0),
    "category": "Animation",
    "location": "Nonlinear Animation > Side panel (N) > Q3 Animation Config",
    "description": (
        "Writes config file from NLA strips. Please see documentation for details."
    ),
    "doc_url": "https://uzugijin.github.io",
}

import bpy
import os

class Q3AnimationConfigProperties(bpy.types.PropertyGroup):
    selected_object: bpy.props.PointerProperty(name="Armature of model", type=bpy.types.Object, description="Only the NLA track of this armature will be used")
    sex_defined: bpy.props.EnumProperty(
        items=[
            ("sex n", "Neutral", ""),
            ("sex m", "Male", ""),
            ("sex f", "Female", ""),
        ],
        name="Sex",
        default="sex n",
    )
    footsteps_defined: bpy.props.EnumProperty(
        items=[
            ("footsteps normal", "Normal", ""),
            ("footsteps boot", "Boots", ""),
            ("footsteps flesh", "Flesh", ""),
            ("footsteps mech", "Mech", ""),
            ("footsteps energy", "Energy", ""),
        ],
        name="Footsteps",
        default="footsteps normal",
    )
    crop_loops: bpy.props.BoolProperty(name="Crop Loops by 1", default=True, description="Subtract 1 from looping frames for animation config (recommended)")
    fixedtorso: bpy.props.BoolProperty(name="Fixed Torso", default=False, description="Don't rotate torso pitch when looking up or down")
    fixedlegs: bpy.props.BoolProperty(name="Fixed Legs", default=False, description="Don't rotate legs (always align with torso)")
class Q3AnimationConfigPanel(bpy.types.Panel):
    bl_label = "Q3 Animation Config"
    bl_idname = "VIEW3D_PT_q3_animation_config"
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Q3 Animation Config'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        q3_props = scene.q3_animation_config

        row = layout.row()
        row.prop(q3_props, "sex_defined")
        row = layout.row()
        row.prop(q3_props, "footsteps_defined")
        row = layout.row()

        row.prop(context.scene.q3_animation_config, "fixedtorso", text="Fixed Torso", toggle=False)
        row.prop(context.scene.q3_animation_config, "fixedlegs", text="Fixed Legs", toggle=False)
        row = layout.row()
        row.prop(q3_props, "selected_object", text="Armature")
        row = layout.row()
        row = layout.row()
        row.operator("q3.import_actions", text="Actions to NLA")
        row.operator("q3.save_animation_config", text="Write Config File")
        row = layout.row()
        row.prop(context.scene.q3_animation_config, "crop_loops", text="Crop Loops")

        row = layout.row()
        row.operator("q3.open_cheatsheet", text="Open Cheatsheet")

class Q3SaveAnimationConfigOperator(bpy.types.Operator):
    bl_idname = "q3.save_animation_config"
    bl_label = "Save Animation Config"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        q3_props = scene.q3_animation_config
        obj = q3_props.selected_object
        if not obj:
            self.report({'ERROR'}, "Please select an armature!")
            return {'CANCELLED'}
        
        # Define the output file path
        output_file_path = self.filepath if self.filepath else os.path.join(bpy.path.abspath("//"), "animation.cfg")

        def parse_action_name(action_name):
            looping_anims = [
                'LEGS_WALKCR',
                'LEGS_WALK',
                'LEGS_RUN',
                'LEGS_BACK',
                'LEGS_SWIM',
                'LEGS_IDLE',
                'LEGS_IDLECR',
                'LEGS_TURN'
            ]

            dead_anims = [
                'BOTH_DEATH1',
                'BOTH_DEATH2',
                'BOTH_DEATH3'
            ]

            parts = action_name.split('.')
            name = parts[0]
            fps = bpy.context.scene.render.fps
            looping_frames = 0
            is_dead = False

            if name in looping_anims:
                looping_frames = num_frames  # Placeholder to indicate looping frames should match num_frames
                if q3_props.crop_loops:
                    looping_frames -= 1  # subtract 1 from looping frames if crop_loops is True

            if name in dead_anims:
                is_dead = True
                #name = rename_to_dead(name)

            for part in parts[1:]:
                if part.isdigit():
                    fps = int(part)

            return name, fps, looping_frames, is_dead

        def rename_to_dead(name):
            parts = name.split('_')
            if len(parts) > 1:
                base = parts[0]
                number = ''.join(filter(str.isdigit, parts[1]))
                return f"{base}_DEAD{number}"
            return name

        # Open a file to write the output
        with open(output_file_path, "w") as file:
            file.write("// animation config file generated by q3animcfg blender3d extension\n\n")
            file.write(f"{q3_props.sex_defined}\n")
            file.write(f"{q3_props.footsteps_defined}\n")
            if q3_props.fixedtorso:
                file.write("fixedtorso\n")
            if q3_props.fixedlegs:
                file.write("fixedlegs\n")
            file.write("\n// first frame, num frames, looping frames, frames per second\n\n")

            # Iterate through all NLA tracks
            objects = [q3_props.selected_object] if q3_props.selected_object else bpy.data.objects
            for obj in objects:
                if obj and obj.animation_data and obj.animation_data.nla_tracks:
                    for track in obj.animation_data.nla_tracks:
                        for strip in track.strips:
                            start_frame = int(strip.frame_start)
                            end_frame = int(strip.frame_end)
                            num_frames = end_frame - start_frame

                            name, fps, looping_frames, is_dead = parse_action_name(strip.name)
                            if looping_frames == -1:
                                looping_frames = num_frames

                            # Write the formatted output to the file
                            file.write(f"{start_frame}\t{num_frames}\t{looping_frames}\t{fps}\t\t// {name}\n")

                            print("Is dead:", is_dead)
                            if is_dead:
                                dead_name = rename_to_dead(name)
                                file.write(f"{end_frame - 1}\t1\t0\t{fps}\t\t// {dead_name}\n")
        self.report({'INFO'}, "Animation config file has been created.")
        return {'FINISHED'}

    def invoke(self, context, event):
        #blend_file_name = bpy.path.display_name(bpy.context.blend_data.filepath)
        self.filepath = "animation.cfg"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

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

        if not obj:
            self.report({'ERROR'}, "Please select an armature!")
            return {'CANCELLED'}
        
        for track in obj.animation_data.nla_tracks:
            obj.animation_data.nla_tracks.remove(track)

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
        return {'FINISHED'}


classes = (
    Q3AnimationConfigProperties,
    Q3AnimationConfigPanel,
    Q3SaveAnimationConfigOperator,
    Q3OpenCheatsheetOperator,
    Q3ImportActionsOperator,
)



def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.q3_animation_config = bpy.props.PointerProperty(type=Q3AnimationConfigProperties)
    bpy.types.Scene.q3_animation_config_crop_loops = bpy.props.BoolProperty(name="Crop Loops by 1", default=False)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.q3_animation_config
    del bpy.types.Scene.q3_animation_config_crop_loops

if __name__ == "__main__":
    register()