####################################################################
# Robox plugin for Ultimaker Cura
# A plugin to enable Cura to write custom gcode files for
# the Robox printers
#
# Written by Tim Schoenmackers
# Based on the GcodeWriter plugin written by Ultimaker
#
# the GcodeWriter plugin source can be found here:
# https://github.com/Ultimaker/Cura/tree/master/plugins/GCodeWriter
#
# This plugin is released under the terms of the LGPLv3 or higher.
# The full text of the LGPLv3 License can be found here:
# https://github.com/timmehtimmeh/Cura-Dremel-Printer-Plugin/blob/master/LICENSE
####################################################################

import os  # for listdir
import os.path  # for isfile and join and path
import sys
import zipfile  # For unzipping the printer files
import stat  # For setting file permissions correctly
import re  # For escaping characters in the settings.
import json
import copy
import shutil

from . import _version
from . import RoboxPostProcessing

from distutils.version import StrictVersion  # for upgrade installations

from UM.i18n import i18nCatalog
from UM.Extension import Extension
from UM.Message import Message
from UM.Resources import Resources
from UM.Logger import Logger
from UM.Preferences import Preferences
from UM.Mesh.MeshWriter import MeshWriter
from UM.Settings.InstanceContainer import InstanceContainer
from UM.Qt.Duration import DurationFormat
from UM.Qt.Bindings.Theme import Theme
from UM.PluginRegistry import PluginRegistry

from UM.Application import Application
from UM.Settings.InstanceContainer import InstanceContainer
from cura.Machines.ContainerTree import ContainerTree
from cura.Utils.Threading import call_on_qt_thread
from cura.Snapshot import Snapshot

from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtGui import QPixmap, QScreen, QColor, qRgb, QImageReader, QImage, QDesktopServices
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt, QSize, pyqtSlot, QObject, QUrl, pyqtSlot

from . import G3DremHeader

catalog = i18nCatalog("cura")

files = [
    ["definitions", "cel_robox_dual.def.json"],
    ["definitions", "cel_robox_quickfill.def.json"],
    ["extruders", "cel_robox_dual_extruder_1.def.json"],
    ["extruders", "cel_robox_dual_extruder_2.def.json"],
    ["extruders", "cel_robox_quickfill_extruder_1.def.json"],
    ["extruders", "cel_robox_quickfill_extruder_2.def.json"],
]

dirs = [
    ["quality", "roboxquality"],
    ["materials", "roboxmat"],
]


class RoboxPrinterPlugin(QObject, MeshWriter, Extension):
    ######################################################################
    ##  The version number of this plugin
    ##  Please ensure that the version number is the same match in all
    ##  three of the following Locations:
    ##    1) below (this file)
    ##    2) .\plugin.json
    ##    3) ..\..\resources\package.json
    ######################################################################
    version = _version.__version__

    ######################################################################
    ##  Dictionary that defines how characters are escaped when embedded in
    #   g-code.
    #
    #   Note that the keys of this dictionary are regex strings. The values are
    #   not.
    ######################################################################
    escape_characters = {
        re.escape("\\"): "\\\\",  # The escape character.
        re.escape("\n"): "\\n",  # Newlines. They break off the comment.
        re.escape("\r"): "\\r"  # Carriage return. Windows users may need this for visualisation in their editors.
    }

    _setting_keyword = ";SETTING_"

    def __init__(self):
        super().__init__(add_to_recent_files=False)
        self._application = Application.getInstance()

        if self.getPreferenceValue("curr_version") is None:
            self.setPreferenceValue("curr_version", "0.0.0")

        self.this_plugin_path = os.path.join(Resources.getStoragePath(Resources.Resources), "plugins",
                                             "RoboxPrinterPlugin", "RoboxPrinterPlugin")

        self._preferences_window = None
        Logger.log("i", "Robox Plugin setting up")
        # Prompt user to uninstall the old plugin, as this one supercedes it
        self.PromptToUninstallOldPluginFiles()

        needs_to_be_installed = False

        if self.isInstalled():
            Logger.log("i", "All Robox files are installed")

            # if the version isn't the same, then force installation
            if not self.versionsMatch():
                Logger.log("i", "Robox Plugin detected that plugin needs to be upgraded")
                needs_to_be_installed = True

        else:
            Logger.log("i", "Some Robox Plugin files are NOT installed")
            needs_to_be_installed = True

        # if we need to install the files, then do so
        if needs_to_be_installed:
            self.installPluginFiles()

        self.addMenuItem(catalog.i18nc("@item:inmenu", "Preferences"), self.showPreferences)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Report Issue"), self.reportIssue)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Help "), self.showHelp)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Robox Printer Plugin Version " + RoboxPrinterPlugin.version),
                         self.openPluginWebsite)

        # finally save the cura.cfg file
        Logger.log("i", "Robox Plugin - Writing to " + str(
            Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg")))
        self._application.getPreferences().writeToFile(
            Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))

    ######################################################################
    ## Taking snapshot needs to be called on QT thread
    ## see this function for more info
    ## https://github.com/Ultimaker/Cura/blob/bcf180985d8503245822d420b420f826d0b2de72/plugins/CuraEngineBackend/CuraEngineBackend.py#L250-L261
    ######################################################################
    @call_on_qt_thread
    def _createSnapshot(self, w=80, h=60):
        # must be called from the main thread because of OpenGL
        Logger.log("d", "Creating thumbnail image with size (", w, ",", h, ")")
        self._snapshot = Snapshot.snapshot(width=w, height=h)
        Logger.log("d", "Thumbnail taken")

    def createPreferencesWindow(self):
        path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "RoboxPluginprefs.qml")
        Logger.log("i", "Creating RoboxPrinterPlugin preferences UI " + path)
        self._preferences_window = self._application.createQmlComponent(path, {"manager": self})

    def showPreferences(self):
        if self._preferences_window is None:
            self.createPreferencesWindow()
        self._preferences_window.show()

    def hidePreferences(self):
        if self._preferences_window is not None:
            self._preferences_window.hide()

    ######################################################################
    ##  function so that the preferences menu can open website
    ######################################################################
    @pyqtSlot()
    def openPluginWebsite(self):
        url = QUrl('https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/releases', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status",
                                            "Robox Plugin could not navigate to https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/releases"))
            message.show()
        return

    ######################################################################
    ##  Show the help
    ######################################################################
    @pyqtSlot()
    def showHelp(self):
        url = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "README.pdf")
        Logger.log("i", "Robox Plugin opening help document: " + url)
        try:
            if not QDesktopServices.openUrl(QUrl("file:///" + url, QUrl.TolerantMode)):
                message = Message(catalog.i18nc("@info:status",
                                                "Robox Plugin could not open help document.\n Please download it from here: https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/raw/cura-3.4/README.pdf"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status",
                                            "Robox Plugin could not open help document.\n Please download it from here: https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/raw/cura-3.4/README.pdf"))
            message.show()
        return

    ######################################################################
    ##  Open up the Github Issues Page
    ######################################################################
    @pyqtSlot()
    def reportIssue(self):
        Logger.log("i",
                   "Robox Plugin opening issue page: https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/issues/new")
        try:
            if not QDesktopServices.openUrl(
                    QUrl("https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/issues/new")):
                message = Message(catalog.i18nc("@info:status",
                                                "Robox Plugin could not open https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/issues/new please navigate to the page and report an issue"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status",
                                            "Robox Plugin could not open https://github.com/Automaker-Unofficial/Cura-Robox-Printer-Plugin/issues/new please navigate to the page and report an issue"))
            message.show()
        return

    ######################################################################
    ## returns true if the versions match and false if they don't
    ######################################################################
    def versionsMatch(self):
        # get the currently installed plugin version number
        if self.getPreferenceValue("curr_version") is None:
            self.setPreferenceValue("curr_version", "0.0.0")
            # self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))

        installed_version = self._application.getPreferences().getValue("RoboxPrinterPlugin/curr_version")
        Logger.log("i",
                   "Robox Plugin checking versions: " + installed_version + " == " + RoboxPrinterPlugin.version)

        try:
            if StrictVersion(installed_version) == StrictVersion(RoboxPrinterPlugin.version):
                # if the version numbers match, then return true
                Logger.log("i",
                           "Robox Plugin versions match: " + installed_version + " matches " + RoboxPrinterPlugin.version)
                return True
            else:
                Logger.log("i",
                           "Robox Plugin - The currently installed version: " + installed_version + " doesn't match this version: " + RoboxPrinterPlugin.version)
                return False
        except:  # Installing a new plugin should never crash the application so catch any random errors and show a message.
            Logger.logException("w",
                                f"An exception occurred in Robox Printer Plugin while checking version {installed_version}. It might be a development version")
            message = Message(catalog.i18nc("@warning:status",
                                            f"Robox Printer Plugin experienced an error while checking version {installed_version}. It might be a development version"))
            message.show()
            return True

    ######################################################################
    ## Check to see if the plugin files are all installed
    ## Return True if all files are installed, false if they are not
    ######################################################################
    def isInstalled(self):
        Logger.log("i", "Robox Plugin checking instalation files")
        files_installed = True

        for f in files:
            path = os.path.join(Resources.getStoragePathForType(Resources.Resources), *f)
            if not os.path.isfile(path):
                Logger.log("e", f"Missing {path} instalation file")
                return False

        # if everything is there, return True
        Logger.log("i", "Robox Plugin all files ARE installed")
        return True

    ######################################################################
    ##  Gets a value from Cura's preferences
    ######################################################################
    def getPreferenceValue(self, preferenceName):
        return self._application.getPreferences().getValue("RoboxPrinterPlugin/" + str(preferenceName))

    ######################################################################
    ## Sets a value to be stored in Cura's preferences file
    ######################################################################
    def setPreferenceValue(self, preferenceName, preferenceValue):
        if preferenceValue is None:
            return False
        name = "RoboxPrinterPlugin/" + str(preferenceName)
        Logger.log("i", "Robox Plugin: setting preference " + name + " to " + str(preferenceValue))
        if self.getPreferenceValue(preferenceName) is None:
            Logger.log("i", "Adding preference " + name);
            self._application.getPreferences().addPreference(name, preferenceValue)

        self._application.getPreferences().setValue(name, preferenceValue)
        return self.getPreferenceValue(preferenceName) == preferenceValue

    ######################################################################
    ## Install the plugin files from the included zip file.
    ######################################################################
    def installPluginFiles(self):
        Logger.log("i", "Robox Plugin installing printer files")
        try:
            resources_path = os.path.join(self.this_plugin_path, "../../../")
            zipdata = os.path.join(self.this_plugin_path, "resources.zip")
            Logger.log("i", "Robox Plugin: found zipfile: " + zipdata)
            with zipfile.ZipFile(zipdata, "r") as zip_ref:
                for info in zip_ref.infolist():
                    Logger.log("i", "Robox Plugin: found in zipfile: " + info.filename)
                    extracted_path = zip_ref.extract(info.filename, resources_path)
                    permissions = os.stat(extracted_path).st_mode
                    os.chmod(extracted_path, permissions | stat.S_IEXEC)  # Make these files executable.
                    Logger.log("i", "Robox Plugin installing " + info.filename + " to " + resources_path)

            if self.isInstalled():
                # The files are now installed, so set the curr_version prefrences value
                if not self.setPreferenceValue("curr_version", RoboxPrinterPlugin.version):
                    Logger.log("e", "Robox Plugin could not set curr_version preference ")

        except:  # Installing a new plugin should never crash the application so catch any random errors and show a message.
            Logger.logException("w", "An exception occurred in Robox Printer Plugin while installing the files")
            message = Message(catalog.i18nc("@warning:status",
                                            "Robox Printer Plugin experienced an error installing the necessary files"))
            message.show()

    ######################################################################
    ## Prompt the user that the old  plugin is installed
    ######################################################################
    def PromptToUninstallOldPluginFiles(self):
        Logger.log("i", "PromptToUninstallOldPluginFiles not implemented")
        # currently this will prompt the user to uninstall the old plugin, but not actually uninstall anything
        # if os.path.isdir(robox_plugin_dir):
        #     message = Message(catalog.i18nc("@warning:status",
        #                                     "Please uninstall the Robox old plugin.\n\t• The Robox Printer Plugin replaces the older Robox plugin.\n\t• Currently both are installed. "))
        #     message.show()
        # Uninstall the plugin files.

    def uninstallPluginFiles(self, quiet):
        Logger.log("i", "Robox Plugin uninstalling plugin files")
        # remove the printer definition file
        something_removed = False

        for f in files:
            something_removed = something_removed or remove_file(self.local_printer_def_path, *f)

        for d in dirs:
            something_removed = something_removed or remove_dir(self.local_printer_def_path, *d)

        # prompt the user to restart
        if something_removed and quiet == False:
            self._application.getPreferences().setValue("Robox/install_status", "uninstalled")
            message = Message(catalog.i18nc("@info:status",
                                            "Robox files have been uninstalled, please restart Cura to complete uninstallation."))
            message.show()

    ######################################################################
    ##  Performs the writing of the gcode for robox printers it should check active_printer and convert gcode
    ######################################################################
    def write(self, stream, nodes, mode=MeshWriter.OutputMode.BinaryMode):
        Logger.log("e", "Robox Plugin write called.")
        try:
            if mode != MeshWriter.OutputMode.BinaryMode:
                Logger.log("e", "Robox Plugin does not support non-binary mode.")
                return False
            if stream is None:
                Logger.log("e", "Robox Plugin - Error writing - no output stream.")
                return False

            # after the plugin info - write the gcode from Cura
            active_build_plate = self._application.getMultiBuildPlateModel().activeBuildPlate
            scene = self._application.getController().getScene()
            if not hasattr(scene, "gcode_dict"):
                message = Message(catalog.i18nc("@warning:status", "Please prepare G-code before exporting."))
                message.show()
                return False

            global_container_stack = self._application.getGlobalContainerStack()
            active_machine_stack = self._application.getMachineManager().activeMachine
            print_object("active_machine_stack", active_machine_stack)
            printer_model = active_machine_stack.getDefinition().getId()
            processor = RoboxPostProcessing.RoboxPostProcessing(printer_model, True)

            gcode_dict = getattr(scene, "gcode_dict")
            gcode_list = gcode_dict.get(active_build_plate, None)
            if gcode_list is not None:
                has_settings = False
                stream.write(processor.get_header().encode())
                for gcode in gcode_list:
                    Logger.log("d", "got node" + gcode)
                    try:
                        processed = processor.execute(gcode)
                        # Logger.log("d", "made node " + processed)
                        if gcode[:len(self._setting_keyword)] == self._setting_keyword:
                            has_settings = True
                        stream.write(processed.encode())
                        stream.write(";end gcode item\n".encode())
                    except:
                        Logger.logException("w", "Robox Plugin - Error writing gcode to file.")
                        return False
                try:
                    ## Serialise the current container stack and put it at the end of the file.
                    if not has_settings:
                        settings = self._serialiseSettings(global_container_stack)
                        stream.write(settings.encode())
                    Logger.log("i", "Done writing settings - write complete")
                    return True
                except Exception as e:
                    Logger.logException("w", "Exception caught while serializing settings.")
                    Logger.log("d", sys.exc_info()[:2])
            message = Message(catalog.i18nc("@warning:status", "Please prepare G-code before exporting."))
            message.show()
            return False
        except Exception as e:
            Logger.logException("w", "Exception caught while writing gcode.")
            Logger.log("d", sys.exc_info()[:2])
            return False

    ##  Create a new container with container 2 as base and container 1 written over it.
    def _createFlattenedContainerInstance(self, instance_container1, instance_container2):
        flat_container = InstanceContainer(instance_container2.getName())

        # The metadata includes id, name and definition
        flat_container.setMetaData(copy.deepcopy(instance_container2.getMetaData()))

        if instance_container1.getDefinition():
            flat_container.setDefinition(instance_container1.getDefinition().getId())

        for key in instance_container2.getAllKeys():
            flat_container.setProperty(key, "value", instance_container2.getProperty(key, "value"))

        for key in instance_container1.getAllKeys():
            flat_container.setProperty(key, "value", instance_container1.getProperty(key, "value"))

        return flat_container

    ######################################################################
    ##  Serialises a container stack to prepare it for writing at the end of the
    #   g-code.
    #
    #   The settings are serialised, and special characters (including newline)
    #   are escaped.
    #
    #   \param settings A container stack to serialise.
    #   \return A serialised string of the settings.
    ######################################################################
    def _serialiseSettings(self, stack):
        container_registry = self._application.getContainerRegistry()

        prefix = self._setting_keyword + str(RoboxPrinterPlugin.version) + " "  # The prefix to put before each line.
        prefix_length = len(prefix)

        quality_type = stack.quality.getMetaDataEntry("quality_type")
        container_with_profile = stack.qualityChanges
        machine_definition_id_for_quality = ContainerTree.getInstance().machines[
            stack.definition.getId()].quality_definition
        if container_with_profile.getId() == "empty_quality_changes":
            # If the global quality changes is empty, create a new one
            quality_name = container_registry.uniqueName(stack.quality.getName())
            quality_id = container_registry.uniqueName(
                (stack.definition.getId() + "_" + quality_name).lower().replace(" ", "_"))
            container_with_profile = InstanceContainer(quality_id)
            container_with_profile.setName(quality_name)
            container_with_profile.setMetaDataEntry("type", "quality_changes")
            container_with_profile.setMetaDataEntry("quality_type", quality_type)
            if stack.getMetaDataEntry(
                    "position") is not None:  # For extruder stacks, the quality changes should include an intent category.
                container_with_profile.setMetaDataEntry("intent_category",
                                                        stack.intent.getMetaDataEntry("intent_category", "default"))
            container_with_profile.setDefinition(machine_definition_id_for_quality)
            container_with_profile.setMetaDataEntry("setting_version",
                                                    stack.quality.getMetaDataEntry("setting_version"))

        flat_global_container = self._createFlattenedContainerInstance(stack.userChanges, container_with_profile)
        # If the quality changes is not set, we need to set type manually
        if flat_global_container.getMetaDataEntry("type", None) is None:
            flat_global_container.setMetaDataEntry("type", "quality_changes")

        # Ensure that quality_type is set. (Can happen if we have empty quality changes).
        if flat_global_container.getMetaDataEntry("quality_type", None) is None:
            flat_global_container.setMetaDataEntry("quality_type",
                                                   stack.quality.getMetaDataEntry("quality_type", "normal"))

        # Get the machine definition ID for quality profiles
        flat_global_container.setMetaDataEntry("definition", machine_definition_id_for_quality)

        serialized = flat_global_container.serialize()
        data = {"global_quality": serialized}

        all_setting_keys = flat_global_container.getAllKeys()
        for extruder in stack.extruderList:
            extruder_quality = extruder.qualityChanges
            if extruder_quality.getId() == "empty_quality_changes":
                # Same story, if quality changes is empty, create a new one
                quality_name = container_registry.uniqueName(stack.quality.getName())
                quality_id = container_registry.uniqueName(
                    (stack.definition.getId() + "_" + quality_name).lower().replace(" ", "_"))
                extruder_quality = InstanceContainer(quality_id)
                extruder_quality.setName(quality_name)
                extruder_quality.setMetaDataEntry("type", "quality_changes")
                extruder_quality.setMetaDataEntry("quality_type", quality_type)
                extruder_quality.setDefinition(machine_definition_id_for_quality)
                extruder_quality.setMetaDataEntry("setting_version", stack.quality.getMetaDataEntry("setting_version"))

            flat_extruder_quality = self._createFlattenedContainerInstance(extruder.userChanges, extruder_quality)
            # If the quality changes is not set, we need to set type manually
            if flat_extruder_quality.getMetaDataEntry("type", None) is None:
                flat_extruder_quality.setMetaDataEntry("type", "quality_changes")

            # Ensure that extruder is set. (Can happen if we have empty quality changes).
            if flat_extruder_quality.getMetaDataEntry("position", None) is None:
                flat_extruder_quality.setMetaDataEntry("position", extruder.getMetaDataEntry("position"))

            # Ensure that quality_type is set. (Can happen if we have empty quality changes).
            if flat_extruder_quality.getMetaDataEntry("quality_type", None) is None:
                flat_extruder_quality.setMetaDataEntry("quality_type",
                                                       extruder.quality.getMetaDataEntry("quality_type", "normal"))

            # Change the default definition
            flat_extruder_quality.setMetaDataEntry("definition", machine_definition_id_for_quality)

            extruder_serialized = flat_extruder_quality.serialize()
            data.setdefault("extruder_quality", []).append(extruder_serialized)

            all_setting_keys.update(flat_extruder_quality.getAllKeys())

        # Check if there is any profiles
        if not all_setting_keys:
            Logger.log("i", "No custom settings found, not writing settings to g-code.")
            return ""

        json_string = json.dumps(data)

        # Escape characters that have a special meaning in g-code comments.
        pattern = re.compile("|".join(RoboxPrinterPlugin.escape_characters.keys()))

        # Perform the replacement with a regular expression.
        escaped_string = pattern.sub(lambda m: RoboxPrinterPlugin.escape_characters[re.escape(m.group(0))], json_string)

        # Introduce line breaks so that each comment is no longer than 80 characters. Prepend each line with the prefix.
        result = ""
        # Lines have 80 characters, so the payload of each line is 80 - prefix.
        for pos in range(0, len(escaped_string), 80 - prefix_length):
            result += prefix + escaped_string[pos: pos + 80 - prefix_length] + "\n"
        return result


def print_object(name, obj):
    Logger.log("d", f"object {name}, {type(obj)}: {obj}")


def remove_file(path: str, file_name: str) -> bool:
    try:
        file_path = os.path.join(path, file_name)
        if os.path.isfile(file_path):
            Logger.log("i", "Robox Plugin removing printer definition from " + file_path)
            os.remove(file_path)
            return True
    except:  # Installing a new plugin should never crash the application.
        Logger.logException("d", "An exception occurred in Robox Plugin while removing files")
    return False


def remove_dir(path: str, dir_name: str) -> bool:
    try:
        dir_path = os.path.join(path, dir_name)
        shutil.rmtree(dir_path)
        return True
    except:  # Installing a new plugin should never crash the application.
        Logger.logException("d", "An exception occurred in Robox Plugin while removing dir")
    return False
