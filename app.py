import glob
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import xml.etree.ElementTree as ET
import zipfile
from tkinter import filedialog, messagebox, ttk

if getattr(sys, 'frozen', False):
    # Nếu đang chạy từ tệp .exe
    base_path = sys._MEIPASS
else:
    # Nếu đang phát triển (không phải .exe)
    base_path = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(base_path, 'config.json')
icon_path = os.path.join(base_path, 'icon.ico')

def add_libs_to_vcxproj(vcxproj_path, lib_name):
  
    # Load file .vcxproj
    tree = ET.parse(vcxproj_path)
    root = tree.getroot()
    namespace = {'ns': 'http://schemas.microsoft.com/developer/msbuild/2003'}

    relative_lib_folder = "$(ProjectDir)Lib"

    include_path = f"{relative_lib_folder}\\{lib_name}\\include"
    debug_lib_path = f"{relative_lib_folder}\\{lib_name}\\debug\\lib"
    release_lib_path = f"{relative_lib_folder}\\{lib_name}\\lib"
    debug_bin_path = f"{relative_lib_folder}\\{lib_name}\\debug\\bin"
    release_bin_path = f"{relative_lib_folder}\\{lib_name}\\bin"

    # Check if the required folders exist
    lib_folder = os.path.join(os.path.dirname(vcxproj_path), "Lib", lib_name)
    include_exists = os.path.exists(os.path.join(lib_folder, "include"))
    debug_lib_exists = os.path.exists(os.path.join(lib_folder, "debug", "lib"))
    release_lib_exists = os.path.exists(os.path.join(lib_folder, "lib"))
    debug_bin_exists = os.path.exists(os.path.join(lib_folder, "debug", "bin"))
    release_bin_exists = os.path.exists(os.path.join(lib_folder, "bin"))
    
    # Tìm tất cả ItemDefinitionGroup cho cả Debug và Release
    item_groups = root.findall(".//ns:ItemDefinitionGroup", namespace)
    
    for item_group in item_groups:
        # Kiểm tra Condition để xác định Debug hay Release
        condition = item_group.get('Condition', '')
        if condition == "'$(Configuration)|$(Platform)'=='Debug|x64'":
            if not debug_lib_exists:
                continue
            lib_path = debug_lib_path
            bin_path = debug_bin_path if debug_bin_exists else None
            # Lấy danh sách file .lib trong thư mục debug
            dlp = f"{os.path.dirname(vcxproj_path)}\\Lib\\{lib_name}\\debug\\lib"
            lib_files = [f for f in os.listdir(dlp) if f.endswith('.lib')] if os.path.exists(dlp) else []
        elif condition == "'$(Configuration)|$(Platform)'=='Release|x64'":
            if not release_lib_exists:
                continue
            lib_path = release_lib_path
            bin_path = release_bin_path if release_bin_exists else None
            # Lấy danh sách file .lib trong thư mục release
            rlp = f"{os.path.dirname(vcxproj_path)}\\Lib\\{lib_name}\\lib"
            lib_files = [f for f in os.listdir(rlp) if f.endswith('.lib')] if os.path.exists(rlp) else []
        else:
            continue

        # Tìm hoặc tạo các phần tử cần thiết trong ItemDefinitionGroup
        cl_compile = item_group.find("ns:ClCompile", namespace)
        if cl_compile is None:
            cl_compile = ET.SubElement(item_group, "ClCompile")
        
        additional_includes = cl_compile.find("ns:AdditionalIncludeDirectories", namespace)
        if additional_includes is None:
            additional_includes = ET.SubElement(cl_compile, "AdditionalIncludeDirectories")

        link = item_group.find("ns:Link", namespace)
        if link is None:
            link = ET.SubElement(item_group, "Link")
            
        additional_libs = link.find("ns:AdditionalLibraryDirectories", namespace)
        if additional_libs is None:
            additional_libs = ET.SubElement(link, "AdditionalLibraryDirectories")
            
        additional_dependencies = link.find("ns:AdditionalDependencies", namespace)
        if additional_dependencies is None:
            additional_dependencies = ET.SubElement(link, "AdditionalDependencies")

        post_build = item_group.find("ns:PostBuildEvent", namespace)
        if post_build is None:
            post_build = ET.SubElement(item_group, "PostBuildEvent")
            
        command_line = post_build.find("ns:Command", namespace)
        if command_line is None:
            command_line = ET.SubElement(post_build, "Command")

        # Add include path only if it exists
        if include_exists:
            if additional_includes.text is None:
                additional_includes.text = include_path
            elif include_path not in additional_includes.text:
                additional_includes.text += f";{include_path}"

        # Add lib path only if it exists
        if additional_libs.text is None:
            additional_libs.text = lib_path
        elif lib_path not in additional_libs.text:
            additional_libs.text += f";{lib_path}"

        # Thêm các file .lib vào AdditionalDependencies
        existing_libs = [] if additional_dependencies.text is None else additional_dependencies.text.split(';')
        for lib_file in lib_files:
            if lib_file not in existing_libs:
                if additional_dependencies.text is None:
                    additional_dependencies.text = lib_file
                else:
                    additional_dependencies.text += f";{lib_file}"

        # Add post-build command only if the bin folder exists
        if bin_path:
            command = f"xcopy /Y /I \"{bin_path}\\*\" \"$(OutDir)\""
            if command_line.text is None:
                command_line.text = command
            elif command not in command_line.text:
                command_line.text += f"\r\n{command}"

    # Ghi lại file .vcxproj sau khi sửa
    ET.register_namespace('', "http://schemas.microsoft.com/developer/msbuild/2003")
    tree.write(vcxproj_path, encoding="utf-8", xml_declaration=True)

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("500x100")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # VCPKG Path
        vcpkg_frame = ttk.Frame(main_frame)
        vcpkg_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(vcpkg_frame, text="VCPKG Path:").pack(side=tk.LEFT)
        self.vcpkg_path = ttk.Entry(vcpkg_frame)
        self.vcpkg_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        ttk.Button(vcpkg_frame, text="Browse", command=self.browse_vcpkg).pack(side=tk.RIGHT)
        
        # Load current config
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.vcpkg_path.insert(0, config.get('vcpkg_path', ''))
        except FileNotFoundError:
            pass
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def browse_vcpkg(self):
        path = filedialog.askdirectory(title="Select VCPKG Directory")
        if path:
            self.vcpkg_path.delete(0, tk.END)
            self.vcpkg_path.insert(0, path)

    def save_settings(self):
        config = {
            'vcpkg_path': self.vcpkg_path.get()
        }
        
        try:
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

class CMakeStyleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VCProj Library Manager")
        self.root.geometry("800x600")

        # Get screen resolution
        scr_width, scr_height = root.winfo_screenwidth(), root.winfo_screenheight()

        # Calculate window position
        win_width, win_height = 800, 600  # Kích thước đã đặt trước
        x = (scr_width - win_width) // 2
        y = (scr_height - win_height) // 2

        # Place the window at the calculated position
        root.geometry(f"{win_width}x{win_height}+{x}+{y}")

        self.console_bg = '#000000'
        self.console_fg = '#00FF00'
        self.console_font = ('Consolas', 10)
        
        self.console_queue = queue.Queue()
        self.load_config()
        self.create_widgets()
        self.check_console_queue()

        self.done = 1
        
    def load_config(self):
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {"vcpkg_path": ""}
            with open(config_path, 'w') as f:
                json.dump(self.config, f)

    def setting(self):
        SettingsDialog(self.root)
        # Reload config after dialog closes
        self.load_config()

    def create_widgets(self):
        # Frame cho vcproj path
        vcproj_frame = ttk.Frame(self.root, padding="5")
        vcproj_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(vcproj_frame, text="Vcproj Path   ").pack(side=tk.LEFT)
        self.vcproj_path = ttk.Entry(vcproj_frame)
        self.vcproj_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        ttk.Button(vcproj_frame, text="Browse", command=self.browse_vcproj).pack(side=tk.RIGHT)

        # Frame cho library input
        lib_frame = ttk.Frame(self.root, padding="5")
        lib_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(lib_frame, text="Library Name").pack(side=tk.LEFT)
        self.lib_entry = ttk.Entry(lib_frame)
        self.lib_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        self.lib_entry.bind('<Return>', self.on_enter_pressed)
        self.b_add_lib = ttk.Button(lib_frame, text="Add Library", command=self.add_library)
        self.b_add_lib.pack(side=tk.RIGHT)

        # Frame cho actions
        action_frame = ttk.Frame(self.root, padding="5")
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(action_frame, text="Setting", command=self.setting).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Clear Console", command=self.clear_console).pack(side=tk.LEFT)


        # Console frame
        console_container = ttk.Frame(self.root, padding="5")
        console_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        h_scrollbar = ttk.Scrollbar(console_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        v_scrollbar = ttk.Scrollbar(console_container)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.console = tk.Text(
            console_container, 
            wrap=tk.NONE,
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set,
            bg=self.console_bg,
            fg=self.console_fg,
            insertbackground=self.console_fg,
            font=self.console_font,
            padx=5,
            pady=5
        )
        self.console.pack(fill=tk.BOTH, expand=True)
        
        h_scrollbar.config(command=self.console.xview)
        v_scrollbar.config(command=self.console.yview)
        self.console.config(state=tk.DISABLED)

    def on_enter_pressed(self, event):
        self.add_library()

    def browse_vcproj(self):
        filename = filedialog.askopenfilename(
            title="Select vcxproj file",
            filetypes=(("Visual C++ Project", "*.vcxproj"), ("All files", "*.*"))
        )
        if filename:
            self.vcproj_path.delete(0, tk.END)
            self.vcproj_path.insert(0, filename)

    def execute_command(self, command):
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True
            )
            
            kq = 0
            # Read stdout
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    if "Total install time:" in output or "The following packages are already installed" in output:
                        kq = 1
                    self.console_queue.put(output)
            
            # Read stderr
            for line in process.stderr:
                self.console_queue.put(f"Error: {line}")
            
            rc = process.poll()
            return rc == 0, kq

        except Exception as e:
            self.console_queue.put(f"Error executing command: {str(e)}\n")
            return False
    
    def process_library(self, new_libs):
        self.done = 0


        vcpkg_path = os.path.join(self.config['vcpkg_path'], 'vcpkg.exe')
        if not os.path.exists(vcpkg_path):
            self.console_queue.put(f"\n-> Error: vcpkg not found at {vcpkg_path}\n")
            self.done = 1
            return
        
        # Get vcproj directory path
        vcproj_dir = os.path.dirname(self.vcproj_path.get())
        lib_dir = os.path.join(vcproj_dir, "Lib")
        os.makedirs(lib_dir, exist_ok=True)
        
        for lib_name in new_libs:
            # 0. Check exist lib
            target_lib_dir = os.path.join(lib_dir, lib_name)
            if os.path.exists(target_lib_dir):
                self.console_queue.put(f"\n-> {lib_name} already exists\n")
                add_libs_to_vcxproj(self.vcproj_path.get(),lib_name)
                self.console_queue.put(f"\n-> {lib_name} has already been installed\n")
                continue
        
            # 1. Install library
            self.console_queue.put(f"\n* Installing {lib_name}...\n")
            success, kq = self.execute_command(f'"{vcpkg_path}" install {lib_name}:x64-windows')
            
            if not success:
                self.console_queue.put(f"\n-> Failed to install {lib_name}\n")
                continue
            if kq == 1:
                self.console_queue.put(f"\n-> Downloaded {lib_name}...\n")
            
            # 2. Export library
            self.console_queue.put(f"\n* Exporting {lib_name}...\n")
            success, _ = self.execute_command(f'"{vcpkg_path}" export {lib_name}:x64-windows --zip')
            
            if not success:
                self.console_queue.put(f"\n-> Failed to export {lib_name}\n")
                continue

            # Find the newest zip file
            self.console_queue.put("\n* Processing export files...\n")
            zip_files = glob.glob(os.path.join(self.config['vcpkg_path'], "*.zip"))
            if not zip_files:
                self.console_queue.put("\n-> No exported zip file found\n")
                continue
            
            newest_zip = max(zip_files, key=os.path.getctime)
            zip_basename = os.path.basename(newest_zip)
            
            # Move and extract zip
            target_zip = os.path.join(lib_dir, zip_basename)
            shutil.move(newest_zip, target_zip)
            
            # Extract zip
            with zipfile.ZipFile(target_zip, 'r') as zip_ref:
                extract_dir = os.path.join(lib_dir, "temp_extract")
                zip_ref.extractall(extract_dir)

            # Find and move x64-windows folder
            x64_windows_path = None
            for root, dirs, files in os.walk(extract_dir):
                if "x64-windows" in dirs:
                    x64_windows_path = os.path.join(root, "x64-windows")
                    break
            if x64_windows_path:
                if os.path.exists(target_lib_dir):
                    shutil.rmtree(target_lib_dir)
                shutil.move(x64_windows_path, target_lib_dir)

            # Cleanup
            os.remove(target_zip)
            shutil.rmtree(extract_dir)

            add_libs_to_vcxproj(self.vcproj_path.get(),lib_name)
            self.console_queue.put(f"\n-> {lib_name} has already been installed\n")

        self.done = 1
    
    def add_library(self):
        if self.done == 0 :
            return
        lib_names = self.lib_entry.get().strip()
        if not lib_names:
            self.console_queue.put("-> Please enter a library name\n")
            return
        
        if not self.vcproj_path.get():
            self.console_queue.put("-> Please select a vcxproj file first\n")
            return
        
        new_libs = []
        for lib in lib_names.split(", "):
            new_libs.append(lib)

        #self.lib_entry.delete(0, tk.END)
        #self.b_add_lib.focus_set()

        threading.Thread(target=self.process_library, args=(new_libs,), daemon=True).start()

    def clear_console(self):
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)

    def check_console_queue(self):
        while True:
            try:
                message = self.console_queue.get_nowait()
                self.console.config(state=tk.NORMAL)
                self.console.insert(tk.END, message)
                self.console.see(tk.END)
                self.console.config(state=tk.DISABLED)
                self.console_queue.task_done()
            except queue.Empty:
                break
        
        self.root.after(100, self.check_console_queue)

def main():
    root = tk.Tk()
    app = CMakeStyleGUI(root)
    root.iconbitmap(icon_path)
    root.title("Easy VS Configuration")
    root.mainloop()

if __name__ == "__main__":
    main()