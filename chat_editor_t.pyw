import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import re

class ChatEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chat Editor")
        self.geometry("600x600")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both')

        self.tabs = {}
        self.text_widgets = {}
        self.placeholder_labels = {}

        categories = {
            "game": ["game_enter", "game_exit"],
            "level": ["level_start", "level_end", "level_end_victory", "level_end_lose"],
            "hit": ["hit_talking", "hit_nodeath", "hit_nokill"],
            "death": ["death_telefrag", "death_cratered", "death_lava", "death_slime", "death_drown", "death_suicide", "death_gauntlet", "death_rail", "death_bfg", "death_insult", "death_praise"],
            "kill": ["kill_rail", "kill_gauntlet", "kill_telefrag", "kill_suicide", "kill_insult", "kill_praise"],
            "random": ["random_insult", "random_misc"]
        }

        self.placeholders = {
            "game": {"random": 1, "level": 4, "self": 0},
            "level": {"random": 1, "firstplace": 2, "lastplace": 3, "level": 4, "self": 0},
            "hit": {"enemy": 0, "weapon": 1},
            "death": {"enemy": 0},
            "kill": {"victim": 0},
            "random": {"random": 0, "lastvictim": 1}
        }

        for category, types in categories.items():
            self.create_tab(category, types)

        self.name_label = tk.Label(self, text="Bot Name:")
        self.name_label.pack(side=tk.LEFT, padx=5)
        
        self.name_entry = tk.Entry(self)
        self.name_entry.pack(side=tk.LEFT, padx=5)

        save_button = tk.Button(self, text="Save", command=self.save_file)
        save_button.pack(side=tk.LEFT, padx=5, pady=10)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.show_text_widget()

    def create_tab(self, category, types):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=category.capitalize())

        selected_type = tk.StringVar(value=types[0])
        dropdown = ttk.Combobox(frame, textvariable=selected_type, values=[t.replace(f"{category}_", "") for t in types], state='readonly')
        dropdown.pack(pady=10)
        dropdown.bind("<<ComboboxSelected>>", lambda event, cat=category: self.show_text_widget(cat))

        placeholder_label = tk.Label(frame, text=self.get_placeholder_text(category))
        placeholder_label.pack(pady=5)
        self.placeholder_labels[category] = placeholder_label

        for type_name in types:
            self.create_text_widget(type_name, frame)

        self.tabs[category] = (dropdown, selected_type)

    def create_text_widget(self, type_name, frame):
        text_widget = tk.Text(frame, wrap=tk.WORD)
        text_widget.pack(expand=True, fill='both')
        self.text_widgets[type_name] = text_widget
        text_widget.pack_forget()

    def show_text_widget(self, category=None):
        if category is None:
            category = self.notebook.tab(self.notebook.select(), "text").lower()
        dropdown, selected_type = self.tabs[category]
        selected_type_full = f"{category}_{selected_type.get()}"
        for type_name, text_widget in self.text_widgets.items():
            if type_name == selected_type_full:
                text_widget.pack(expand=True, fill='both')
            else:
                text_widget.pack_forget()
        self.update_placeholder_label(category)

    def on_tab_change(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text").lower()
        dropdown, selected_type = self.tabs[selected_tab]
        selected_type.set(dropdown['values'][0])
        self.show_text_widget(selected_tab)

    def get_placeholder_text(self, category):
        placeholders = self.placeholders[category]
        return "Placeholders: " + ", ".join([f"@{key}" for key in placeholders.keys()])

    def update_placeholder_label(self, category):
        placeholder_label = self.placeholder_labels[category]
        placeholder_label.config(text=self.get_placeholder_text(category))

    def replace_placeholders(self, text, category):
        placeholders = self.placeholders[category]
        for placeholder, number in placeholders.items():
            text = re.sub(rf'@{placeholder}', f'", {number}, "', text)
        return text

    def save_file(self):
        bot_name = self.name_entry.get() or "xaero"
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("botfiles", "*.c")])
        if file_path:
            with open(file_path, 'w') as file:
                file.write(f'chat "{bot_name}"\n{{\n')
                file.write('\t#include "teamplay.h"\n\n')
                for type_name, text_widget in self.text_widgets.items():
                    category = type_name.split('_')[0]
                    file.write(f'\ttype "{type_name}"\n\t{{\n')
                    lines = text_widget.get("1.0", tk.END).strip().split('\n')
                    for line in lines:
                        line = self.replace_placeholders(line, category)
                        file.write(f'\t\t"{line}";\n')
                    file.write('\t} //end type\n\n')
                file.write('}\n')

if __name__ == "__main__":
    app = ChatEditor()
    app.mainloop()
