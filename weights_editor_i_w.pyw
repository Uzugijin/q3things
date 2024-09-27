import tkinter as tk
from tkinter import filedialog, ttk

# Function to save item weights data to a text file
def save_item_weights():
    data = [
        '#include "inv.h"',
        '',
        '//initial health/armor states',
        f'#define FS_HEALTH\t\t\t\t{item_scales["FS_HEALTH"].get()}',
        f'#define FS_ARMOR\t\t\t\t{item_scales["FS_ARMOR"].get()}',
        '',
        '//initial weapon weights',
        f'#define W_SHOTGUN\t\t\t\t{item_scales["W_SHOTGUN"].get()}',
        f'#define W_MACHINEGUN\t\t\t{item_scales["W_MACHINEGUN"].get()}',
        f'#define W_GRENADELAUNCHER\t\t{item_scales["W_GRENADELAUNCHER"].get()}',
        f'#define W_ROCKETLAUNCHER\t\t{item_scales["W_ROCKETLAUNCHER"].get()}',
        f'#define W_RAILGUN\t\t\t\t{item_scales["W_RAILGUN"].get()}',
        f'#define W_BFG10K\t\t\t\t{item_scales["W_BFG10K"].get()}',
        f'#define W_LIGHTNING\t\t\t{item_scales["W_LIGHTNING"].get()}',
        f'#define W_PLASMAGUN\t\t\t{item_scales["W_PLASMAGUN"].get()}',
        '',
        '//the bot has the weapons, so the weights change a little bit',
        f'#define GWW_SHOTGUN\t\t\t{item_scales["GWW_SHOTGUN"].get()}',
        f'#define GWW_MACHINEGUN\t\t{item_scales["GWW_MACHINEGUN"].get()}',
        f'#define GWW_GRENADELAUNCHER\t{item_scales["GWW_GRENADELAUNCHER"].get()}',
        f'#define GWW_ROCKETLAUNCHER\t{item_scales["GWW_ROCKETLAUNCHER"].get()}',
        f'#define GWW_RAILGUN\t\t\t{item_scales["GWW_RAILGUN"].get()}',
        f'#define GWW_BFG10K\t\t\t{item_scales["GWW_BFG10K"].get()}',
        f'#define GWW_LIGHTNING\t\t\t{item_scales["GWW_LIGHTNING"].get()}',
        f'#define GWW_PLASMAGUN\t\t\t{item_scales["GWW_PLASMAGUN"].get()}',
        '',
        '//initial powerup weights',
        f'#define W_TELEPORTER\t\t\t{item_scales["W_TELEPORTER"].get()}',
        f'#define W_MEDKIT\t\t\t\t{item_scales["W_MEDKIT"].get()}',
        f'#define W_QUAD\t\t\t\t{item_scales["W_QUAD"].get()}',
        f'#define W_ENVIRO\t\t\t\t{item_scales["W_ENVIRO"].get()}',
        f'#define W_HASTE\t\t\t\t{item_scales["W_HASTE"].get()}',
        f'#define W_INVISIBILITY\t\t\t{item_scales["W_INVISIBILITY"].get()}',
        f'#define W_REGEN\t\t\t\t{item_scales["W_REGEN"].get()}',
        f'#define W_FLIGHT\t\t\t\t{item_scales["W_FLIGHT"].get()}',
        '',
        '//flag weight',
        f'#define FLAG_WEIGHT\t\t\t{item_scales["FLAG_WEIGHT"].get()}',
        '',
        '//',
        '#include "fw_items.c"'
    ]
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("botfile", "*.c")])
    if file_path:
        with open(file_path, 'w') as file:
            file.write("\n".join(data))

# Function to save weapon weights data to a text file
def save_weapon_weights():
    data = [
        '#include "inv.h"',
        '',
        f'#define W_GAUNTLET\t\t\t\t{weapon_scales["W_GAUNTLET"].get()}',
        f'#define W_SHOTGUN\t\t\t\t{weapon_scales["W_SHOTGUN"].get()}',
        f'#define W_MACHINEGUN\t\t\t{weapon_scales["W_MACHINEGUN"].get()}',
        f'#define W_GRENADELAUNCHER\t\t{weapon_scales["W_GRENADELAUNCHER"].get()}',
        f'#define W_ROCKETLAUNCHER\t\t{weapon_scales["W_ROCKETLAUNCHER"].get()}',
        f'#define W_RAILGUN\t\t\t\t{weapon_scales["W_RAILGUN"].get()}',
        f'#define W_BFG10K\t\t\t\t{weapon_scales["W_BFG10K"].get()}',
        f'#define W_LIGHTNING\t\t\t{weapon_scales["W_LIGHTNING"].get()}',
        f'#define W_PLASMAGUN\t\t\t{weapon_scales["W_PLASMAGUN"].get()}',
        f'#define W_GRAPPLE\t\t\t\t{weapon_scales["W_GRAPPLE"].get()}',
        '',
        '//',
        '#include "fw_weap.c"'
    ]
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("botfile", "*.c")])
    if file_path:
        with open(file_path, 'w') as file:
            file.write("\n".join(data))

# Create the main window
root = tk.Tk()
root.title("Weights Editor")

# Create a notebook
notebook = ttk.Notebook(root)
notebook.pack(padx=10, pady=10)

# Create frames for tabs
item_frame = ttk.Frame(notebook)
weapon_frame = ttk.Frame(notebook)

notebook.add(item_frame, text="Item Weights")
notebook.add(weapon_frame, text="Weapon Weights")

# Dictionary to hold scales
item_scales = {}
weapon_scales = {}

# Data definitions for item weights
item_data_definitions = {
    "FS_HEALTH": 1,
    "FS_ARMOR": 1,
    "W_SHOTGUN": 1,
    "W_MACHINEGUN": 1,
    "W_GRENADELAUNCHER": 1,
    "W_ROCKETLAUNCHER": 1,
    "W_RAILGUN": 1,
    "W_BFG10K": 1,
    "W_LIGHTNING": 1,
    "W_PLASMAGUN": 1,
    "GWW_SHOTGUN": 1,
    "GWW_MACHINEGUN": 1,
    "GWW_GRENADELAUNCHER": 1,
    "GWW_ROCKETLAUNCHER": 1,
    "GWW_RAILGUN": 1,
    "GWW_BFG10K": 1,
    "GWW_LIGHTNING": 1,
    "GWW_PLASMAGUN": 1,
    "W_TELEPORTER": 1,
    "W_MEDKIT": 1,
    "W_QUAD": 1,
    "W_ENVIRO": 1,
    "W_HASTE": 1,
    "W_INVISIBILITY": 1,
    "W_REGEN": 1,
    "W_FLIGHT": 1,
    "FLAG_WEIGHT": 1
}

# Data definitions for weapon weights
weapon_data_definitions = {
    "W_GAUNTLET": 1,
    "W_SHOTGUN": 1,
    "W_MACHINEGUN": 1,
    "W_GRENADELAUNCHER": 1,
    "W_ROCKETLAUNCHER": 1,
    "W_RAILGUN": 1,
    "W_BFG10K": 1,
    "W_LIGHTNING": 1,
    "W_PLASMAGUN": 1,
    "W_GRAPPLE": 1
}

# Create frames for columns in item weights tab
item_frame1 = tk.Frame(item_frame)
item_frame1.pack(side=tk.LEFT, padx=10, pady=10)

item_frame2 = tk.Frame(item_frame)
item_frame2.pack(side=tk.LEFT, padx=10, pady=10)

item_frame3 = tk.Frame(item_frame)
item_frame3.pack(side=tk.LEFT, padx=10, pady=10)

# Create frames for columns in weapon weights tab
weapon_frame1 = tk.Frame(weapon_frame)
weapon_frame1.pack(side=tk.LEFT, padx=10, pady=10)

# Function to add scales to a frame
def add_scales_to_frame(frame, keys, scales_dict, data_definitions, from_=1, to=500):
    for key in keys:
        label = tk.Label(frame, text=key)
        label.pack()
        scale = tk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL)
        scale.set(data_definitions[key])
        scale.pack()
        scales_dict[key] = scale

# Add scales to item frames
add_scales_to_frame(item_frame1, ["FS_HEALTH", "FS_ARMOR", "W_SHOTGUN", "W_MACHINEGUN", "W_GRENADELAUNCHER", "W_ROCKETLAUNCHER", "W_RAILGUN", "W_BFG10K", "W_LIGHTNING", "W_PLASMAGUN"], item_scales, item_data_definitions)
add_scales_to_frame(item_frame2, ["GWW_SHOTGUN", "GWW_MACHINEGUN", "GWW_GRENADELAUNCHER", "GWW_ROCKETLAUNCHER", "GWW_RAILGUN", "GWW_BFG10K", "GWW_LIGHTNING", "GWW_PLASMAGUN"], item_scales, item_data_definitions)
add_scales_to_frame(item_frame3, ["W_TELEPORTER", "W_MEDKIT", "W_QUAD", "W_ENVIRO", "W_HASTE", "W_INVISIBILITY", "W_REGEN", "W_FLIGHT", "FLAG_WEIGHT"], item_scales, item_data_definitions)

# Add scales to weapon frames
add_scales_to_frame(weapon_frame1, ["W_GAUNTLET", "W_SHOTGUN", "W_MACHINEGUN", "W_GRENADELAUNCHER", "W_ROCKETLAUNCHER", "W_RAILGUN", "W_BFG10K", "W_LIGHTNING", "W_PLASMAGUN", "W_GRAPPLE"], weapon_scales, weapon_data_definitions, from_=10, to=640)

# Create the save button for item weights
save_item_button = tk.Button(item_frame, text="Save Item Weights", command=save_item_weights)
save_item_button.pack(side=tk.BOTTOM, pady=10)

# Create the save button for weapon weights
save_weapon_button = tk.Button(weapon_frame, text="Save Weapon Weights", command=save_weapon_weights)
save_weapon_button.pack(side=tk.BOTTOM, pady=10)

# Run the application
root.mainloop()
