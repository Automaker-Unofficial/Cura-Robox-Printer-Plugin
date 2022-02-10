# !/usr/bin/python
import os


# This is a Python script to convert Robox Cel's material's profiles to Cura siutable format.
# Written RodzynK, ver.1.2

def covert_files():
    # Read data from Robox filament file

    file_robox_profile = open(name_file)
    read_lines = file_robox_profile.readlines()
    dict_data = {}
    for i in range(4, len(read_lines)):
        split_data = read_lines[i].split()
        if split_data[0] == "name":
            dict_data[split_data[0]] = split_data[2:]
        else:
            dict_data[split_data[0]] = split_data[2]

    file_robox_profile.close()

    # cel_website = "https://cel-uk.com/shop-category/additive-manufacturing/filament/"
    # General density values to calculate mass
    generic_density = {"PLA": 1.24, "ABS": 1.10, "mABS": 1.10, "ASA": 1.11, "CPE": 1.27, "HIPS": 1.05, "HIP": 1.05,
                       "Nylon": 1.14, "PC": 1.20, "PETG": 1.27,
                       "PET": 1.27, "PVOH": 1.23, "PVA": 1.23, "TPU": 1.22, "PA12": 1.14, "CO-PET": 1.38, "MBS": 1.20,
                       "P12": 1.02, "N66": 1.11, "PCP": 1.20, "PTG": 1.27}

    name = ""
    for i in range(len(dict_data["name"])):
        name = name + dict_data["name"][i].split("\\")[0] + " "  # remove backslash from name

    d = float(dict_data["diameter_mm"]) * 0.001
    length = float(dict_data["default_length_m"])
    area = d * d / 4 * 3.14
    volume = area * length
    weight = volume * 1e6 * generic_density[dict_data["material"]]  # weight in grams

    # Save data in the xml format compatabile with Cura

    f = open(save_file, "w")
    lines = ["<?xml version='1.0' encoding='utf-8'?>",
             "\n<fdmmaterial version=\"1.3\" xmlns=\"http://www.ultimaker.com/material\" xmlns:cura=\"http://www.ultimaker.com/cura\">",
             # seems to be important
             "\n  <metadata>",
             "\n    <name>",
             "\n      <brand>Robox Filaments</brand>",
             "\n      <material>" + dict_data["material"] + "</material>",
             "\n      <color>Generic</color>",
             "\n      <label>" + name + "</label>",
             "\n    </name>",
             "\n    <GUID>72b08246-30bc-464d-bb47-5f225f32c6e6</GUID>",  # seems to be important
             "\n    <description>""FilamentID = " + dict_data["reelID"] + "</description>",
             "\n    <version>1</version>",
             "\n    <color_code>" + dict_data["display_colour"] + "</color_code>",
             "\n    <adhesion_info>Standard info</adhesion_info>",
             "\n  </metadata>",
             "\n  <properties>",
             "\n    <cost>" + dict_data["cost_gbp_per_kg"] + "</cost>",  # Does not work yet
             "\n    <weight>" + str(round(weight)) + "</weight>",
             "\n    <diameter>" + dict_data["diameter_mm"] + "</diameter>",
             "\n    <density>" + str(generic_density[dict_data["material"]]) + "</density>",
             "\n  </properties>",
             "\n  <settings>",
             "\n    <setting key=\"heated bed temperature\">" + dict_data["bed_temperature_C"] + "</setting>",
             "\n    <setting key=\"build volume temperature\">" + dict_data["ambient_temperature_C"] + "</setting>",
             "\n    <setting key=\"print temperature\">" + dict_data["nozzle_temperature_C"] + "</setting>",
             "\n    <cura:setting key=\"material_bed_temperature_layer_0\">" + dict_data[
                 "first_layer_bed_temperature_C"] + "</cura:setting>",
             "\n    <cura:setting key=\"material_print_temperature_layer_0\">" + dict_data[
                 "first_layer_nozzle_temperature_C"] + "</cura:setting>",
             "\n    <cura:setting key=\"material_flow\">" + str(
                 float(dict_data["filament_multiplier"]) * 100) + "</cura:setting>",
             "\n  </settings>",
             "\n</fdmmaterial>"]

    f.writelines(lines)
    f.close()


if __name__ == '__main__':

    flag = 2  # 1) Convert one file, 2) Folder with files

    if flag == 1:
        name_file = "CO-PET - colorFabb nGen Dark Blue (240m).roboxfilament"  # Set path to the read file with name
        save_file = "Robox_" + name_file.replace(" ", "_").split('.')[0] + ".xml.fdm_material"
        covert_files()

    elif flag == 2:
        path_dir_read = 'C:/Program Files/CEL/Common/Filaments/'  # Set path to the read directory
        path_dir_save = 'C:/Cura/'  # Set path to the read directory
        files = os.listdir(path_dir_read)

        for s in files:
            name_file = path_dir_read + s
            save_file = path_dir_save + "Robox_" + s.replace(" ", "_").split('.')[0] + ".xml.fdm_material"
            covert_files()
