import json
import os
import xml.etree.ElementTree as ET


def add_libs_to_vcxproj(vcxproj_path, lib_config_path):
    # Đọc danh sách thư viện từ file JSON
    with open(lib_config_path, 'r') as f:
        new_libs = json.load(f)

    # Load file .vcxproj
    tree = ET.parse(vcxproj_path)
    root = tree.getroot()
    namespace = {'ns': 'http://schemas.microsoft.com/developer/msbuild/2003'}

    relative_lib_folder = "$(ProjectDir)Lib"

    # Duyệt qua các thư viện mới
    for lib_name in new_libs:
        include_path = f"{relative_lib_folder}\\{lib_name}\\include"
        debug_lib_path = f"{relative_lib_folder}\\{lib_name}\\debug\\lib"
        release_lib_path = f"{relative_lib_folder}\\{lib_name}\\lib"
        
        # Tìm tất cả ItemDefinitionGroup cho cả Debug và Release
        item_groups = root.findall(".//ns:ItemDefinitionGroup", namespace)
        
        for item_group in item_groups:
            # Kiểm tra Condition để xác định Debug hay Release
            condition = item_group.get('Condition', '')
            if condition == "'$(Configuration)|$(Platform)'=='Debug|x64'" :
                lib_path = debug_lib_path
            else:
                lib_path = release_lib_path

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

            post_build = item_group.find("ns:PostBuildEvent", namespace)
            if post_build is None:
                post_build = ET.SubElement(item_group, "PostBuildEvent")
                
            command_line = post_build.find("ns:Command", namespace)
            if command_line is None:
                command_line = ET.SubElement(post_build, "Command")

            # Thêm include path nếu chưa tồn tại
            if additional_includes.text is None:
                additional_includes.text = include_path
            elif include_path not in additional_includes.text:
                additional_includes.text += f";{include_path}"

            # Thêm lib path nếu chưa tồn tại
            if additional_libs.text is None:
                additional_libs.text = lib_path
            elif lib_path not in additional_libs.text:
                additional_libs.text += f";{lib_path}"

            # Thêm post-build command
            command = f"xcopy /Y /I \"{relative_lib_folder}\\{lib_name}\\bin\\*\" \"$(OutDir)\""
            if condition == "'$(Configuration)|$(Platform)'=='Debug|x64'" :
                command = f"xcopy /Y /I \"{relative_lib_folder}\\{lib_name}\\debug\\bin\\*\" \"$(OutDir)\""
            if command_line.text is None:
                command_line.text = command
            elif command not in command_line.text:
                command_line.text += f"\r\n{command}"

    # Ghi lại file .vcxproj sau khi sửa
    ET.register_namespace('', "http://schemas.microsoft.com/developer/msbuild/2003")
    tree.write(vcxproj_path, encoding="utf-8", xml_declaration=True)

# Cấu hình đầu vào
vcxproj_path = "F:/OutSource/PYTHON/AUTO_ADD_LIB/IndoorNavigationService.vcxproj"
lib_config_path = "F:/OutSource/PYTHON/AUTO_ADD_LIB/lib.json"

add_libs_to_vcxproj(vcxproj_path, lib_config_path)