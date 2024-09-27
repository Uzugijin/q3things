import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import random

class AttributeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Character Editor")
        
        self.attributes = {
            "NAME": "string",
            "GENDER": "string",
            "ATTACK_SKILL": "float",
            "WEAPONWEIGHTS": "string",
            "AIM_SKILL": "float",
            "AIM_ACCURACY": "float",
            "VIEW_FACTOR": "float",
            "VIEW_MAXCHANGE": "integer",
            "REACTIONTIME": "float",
            "CHAT_FILE": "string",
            "CHAT_NAME": "string",
            "CHAT_CPM": "integer",
            "CHAT_INSULT": "float",
            "CHAT_MISC": "float",
            "CHAT_STARTENDLEVEL": "float",
            "CHAT_ENTEREXITGAME": "float",
            "CHAT_KILL": "float",
            "CHAT_DEATH": "float",
            "CHAT_ENEMYSUICIDE": "float",
            "CHAT_HITTALKING": "float",
            "CHAT_HITNODEATH": "float",
            "CHAT_HITNOKILL": "float",
            "CHAT_RANDOM": "float",
            "CHAT_REPLY": "float",
            "CROUCHER": "float",
            "JUMPER": "float",
            "WALKER": "float",
            "WEAPONJUMPING": "float",
            "GRAPPLE_USER": "float",
            "ITEMWEIGHTS": "string",
            "AGGRESSION": "float",
            "SELFPRESERVATION": "float",
            "VENGEFULNESS": "float",
            "CAMPER": "float",
            "EASY_FRAGGER": "float",
            "ALERTNESS": "float",
            "AIM_ACCURACY_MACHINEGUN": "float",
            "AIM_ACCURACY_SHOTGUN": "float",
            "AIM_ACCURACY_ROCKETLAUNCHER": "float",
            "AIM_ACCURACY_GRENADELAUNCHER": "float",
            "AIM_ACCURACY_LIGHTNING": "float",
            "AIM_ACCURACY_PLASMAGUN": "float",
            "AIM_ACCURACY_RAILGUN": "float",
            "AIM_ACCURACY_BFG10K": "float",
            "AIM_SKILL_ROCKETLAUNCHER": "float",
            "AIM_SKILL_GRENADELAUNCHER": "float",
            "AIM_SKILL_PLASMAGUN": "float",
            "AIM_SKILL_BFG10K": "float",
            "FIRETHROTTLE": "float"
        }
        
        self.entries = {f"skill_{i}": {} for i in range(1, 6)}
        self.include_vars = {f"skill_{i}": tk.BooleanVar(value=(i == 1)) for i in range(1, 6)}
        self.create_widgets()
        
    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(padx=10, pady=10, expand=True, fill='both')
        
        for i in range(1, 6):
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=f'Skill {i}')
            self.create_skill_widgets(frame, f'skill_{i}')
        
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=25)
        
        randomize_button = tk.Button(control_frame, text="Randomize", command=self.randomize_attributes)
        randomize_button.pack(side=tk.LEFT, padx=5)
        
        copy_button = tk.Button(control_frame, text="Copy from skill", command=self.open_copy_window)
        copy_button.pack(side=tk.LEFT, padx=5)
        

        
        save_button = tk.Button(control_frame, text="Save", command=self.save_attributes)
        save_button.pack(side=tk.LEFT, padx=5)
        
    def create_skill_widgets(self, frame, skill):
        include_check = tk.Checkbutton(frame, text="Include", variable=self.include_vars[skill], command=lambda: self.toggle_skill(skill))
        include_check.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        columns = 6
        current_column = 1
        current_row = 1
        
        for attr, attr_type in self.attributes.items():
            if current_column == columns:
                current_column = 1
                current_row += 2
            
            label = tk.Label(frame, text=attr, anchor="w", justify='left')
            label.grid(row=current_row, column=current_column, padx=5, pady=0)
            
            if attr_type == "float":
                scale_frame = tk.Frame(frame)
                scale_frame.grid(row=current_row + 1, column=current_column, padx=5, pady=0)
                scale = tk.Scale(scale_frame, from_=0, to=1, orient=tk.HORIZONTAL, resolution=0.01, showvalue=1)
                scale.pack()
                self.entries[skill][attr] = scale
            elif attr_type == "integer":
                entry = tk.Entry(frame)
                entry.grid(row=current_row + 1, column=current_column, padx=5, pady=5)
                self.entries[skill][attr] = entry
            elif attr_type == "string":
                entry = tk.Entry(frame)
                entry.grid(row=current_row + 1, column=current_column, padx=5, pady=5)
                self.entries[skill][attr] = entry
            
            current_column += 1
        
        self.toggle_skill(skill)
        
    def toggle_skill(self, skill):
        state = tk.NORMAL if self.include_vars[skill].get() else tk.DISABLED
        for attr, widget in self.entries[skill].items():
            if isinstance(widget, tk.Entry) or isinstance(widget, tk.Scale):
                widget.configure(state=state)
        
    def open_copy_window(self):
        self.copy_window = tk.Toplevel(self.root)
        self.copy_window.title("Copy from skill")
        
        label = tk.Label(self.copy_window, text="Select skill to copy from:")
        label.pack(pady=10)
        
        self.copy_var = tk.StringVar()
        self.copy_listbox = tk.Listbox(self.copy_window, listvariable=self.copy_var, height=5)
        for i in range(1, 6):
            if self.include_vars[f'skill_{i}'].get():
                self.copy_listbox.insert(tk.END, f'Skill {i}')
        self.copy_listbox.pack(padx=10, pady=10)
        
        ok_button = tk.Button(self.copy_window, text="Ok", command=self.copy_attributes)
        ok_button.pack(pady=10)
        
    def copy_attributes(self):
        selected_index = self.copy_listbox.curselection()
        if not selected_index:
            return
        
        selected_skill = f'skill_{selected_index[0] + 1}'
        current_tab = self.notebook.select()
        current_skill = self.notebook.tab(current_tab, "text").lower().replace(" ", "_")
        
        for attr, widget in self.entries[selected_skill].items():
            value = widget.get() if isinstance(widget, tk.Entry) else widget.get()
            if isinstance(self.entries[current_skill][attr], tk.Entry):
                self.entries[current_skill][attr].delete(0, tk.END)
                self.entries[current_skill][attr].insert(0, value)
            else:
                self.entries[current_skill][attr].set(value)
        
        self.copy_window.destroy()
        
    def randomize_attributes(self):
        names = ["anarki", "biker", "bitterman", "bones", "crash", "doom", "grunt", "hunter", "keel", "klesk", "lucy", "major", "mynx", "orbb", "ranger", "razor", "sarge", "slash", "visor", "xaero", "sorlag"]
        for i in range(1, 6):
            skill = f'skill_{i}'
            if not self.include_vars[skill].get():
                continue
            picked_name = random.choice(names)
            for attr, widget in self.entries[skill].items():
                if attr == "CHAT_CPM":
                    widget.delete(0, tk.END)
                    widget.insert(0, "400")
                elif attr == "VIEW_MAXCHANGE":
                    widget.delete(0, tk.END)
                    widget.insert(0, random.choice([90, 180, 360]))
                elif attr == "CHAT_NAME":
                    widget.delete(0, tk.END)
                    widget.insert(0, picked_name)
                elif attr == "WEAPONWEIGHTS":
                    widget.delete(0, tk.END)
                    widget.insert(0, f"botfiles/{picked_name}_w.c")
                elif attr == "ITEMWEIGHTS":
                    widget.delete(0, tk.END)
                    widget.insert(0, f"botfiles/{picked_name}_i.c")
                elif attr == "CHAT_FILE":
                    widget.delete(0, tk.END)
                    widget.insert(0, f"botfiles/{picked_name}_t.c")
                elif isinstance(widget, tk.Scale):
                    widget.set(random.uniform(0.2, 1))
        
    def save_attributes(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("botfiles", "*.c")])
        if not file_path:
            return
        
        with open(file_path, "w") as file:
            file.write('#include "chars.h"\n\n')
            for i in range(1, 6):
                skill = f'skill_{i}'
                if not self.include_vars[skill].get():
                    continue
                file.write(f'skill {i}\n{{\n')
                for attr, widget in self.entries[skill].items():
                    value = widget.get() if isinstance(widget, tk.Entry) else f"{widget.get():.2f}"
                    if self.attributes[attr] == "string":
                        value = f'"{value}"'
                    file.write(f'\tCHARACTERISTIC_{attr}\t\t\t\t{value}\n')
                file.write('}\n\n')

if __name__ == "__main__":
    root = tk.Tk()
    app = AttributeGUI(root)
    root.mainloop()
