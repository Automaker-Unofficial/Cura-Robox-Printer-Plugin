import re
import enum
from . import GcodeParser as gp
import logging


class ValveState(enum.Enum):
    Opened = "opened"
    Closed = "closed"
    Undefined = "undefined"


class RoboxPostProcessing:
    def __init__(self, model_name: str, close_valve: bool, version: str):
        super().__init__()
        try:
            gp.Model(model_name)
        except ValueError:
            raise "printer is not supported by robox plugin"

        self.roboxCloseValve = close_valve
        self.model = gp.Model(model_name)

        # set executor function
        if self.model == gp.Model.dual:
            self.executor_func = self.dualRobox
        if self.model == gp.Model.quick_fill:
            self.executor_func = self.QuickFillRobox

        self.t0Pattern = re.compile("T0(\s|$)")
        self.t1Pattern = re.compile("T1(\s|$)")
        self.sTemperaturePattern = re.compile("S\d+")
        self.tTemperaturePattern = re.compile("T\d+")
        self.retractPattern = re.compile("E-\d+")
        self.forwardPattern = re.compile("E\d+")
        self.selectedTool = ""
        self.valve_state = ValveState.Undefined
        self.verion = version

    def get_header(self) -> str:
        output = ""
        # if index == 0:
        output += "; Selected robox profile: " + self.model.value + ", close valve \"" + str(
            self.roboxCloseValve) + "\"\n"
        output += "; version " + self.verion + "\n"
        return output

    # retruns not empty string if tool change happened in this line
    def handle_tool_selection(self, line: gp.GcodeLine, tool_pattern: str) -> str:
        selected_tool = ""
        i = line.get_index_of_command_segment(tool_pattern)
        # there is T0
        if i > -1:
            # T command somewhere in the middle
            if i > 0:
                line.remove_command_part(i)
                line.add_comment(f"removed {tool_pattern}")
                line.tool = tool_pattern
            # T command in the start it is a tool set command
            else:
                selected_tool = tool_pattern
                line.tool = selected_tool
        return selected_tool

    def execute_new(self, data: str) -> str:
        lines = data.split("\n")
        parsed_lines = []
        for l in lines:
            parsed_lines.append(gp.GcodeLine(l))

        # handle tool changes: set tool for every line and remove redundant tool patterns
        selected_tool = ""
        for pl in parsed_lines:
            # check if we have tool cahnges and set selected tool
            if self.handle_tool_selection(pl, "T0") != "":
                selected_tool = "T0"
            elif self.handle_tool_selection(pl, "T1") != "":
                selected_tool = "T1"

            # set tool for line if not set
            if pl.tool == "":
                pl.tool = selected_tool

            # rewrite temperature commands for second extruder
            if len(pl.command_parts) > 0 and pl.command_parts[0] in ["M103", "M104", "M109"] and pl.tool == "T1":
                start_index = pl.get_index_prefix("S")
                if start_index > 0:
                    pl.command_parts[start_index] = pl.command_parts[start_index].replace("S",
                                                                                          "T")  # Replace "Sxxx" with "Txxx"

        lines_with_valve = []
        tool = ""
        valve_state = gp.ValveState.Undefined
        # todo use tool parameters instead of hardcoded values
        layer_height = 0.3
        line_width = 0.4
        nozzle_diameter = 0.4
        valve_volume = 0.35
        # add valve closing and opening routines
        for pl in parsed_lines:
            # check if line is working movement
            if pl.get_index_of_command_segment("G1") == 0:
                if pl.tool != tool:
                    # tool changed
                    valve_state = gp.ValveState.Closed
                tool = pl.tool
                # if there is extruder part in command
                if pl.get_index_prefix("E") > 0:
                    # if it is retraction (negative extrusion)
                    extrusion = pl.get_command_part_number("E")
                    if extrusion < 0:
                        # ignore retraction line if comment has _ignore
                        if "_ignore" in pl.comment:
                            continue
                        valve_volume_left = valve_volume
                        start_index = len(lines_with_valve) - 1
                        index_delta = 0
                        # search for last 10 movement commands
                        movement_indexes = []
                        while len(movement_indexes) < 10 and start_index - index_delta > -1:
                            index = start_index - index_delta
                            m_line = lines_with_valve[index]
                            # check if line has movements
                            if m_line.get_index_prefix("X") > -1 and m_line.get_index_prefix("Y") > -1:
                                movement_indexes.append(index)
                            index_delta += 1
                        for i, idx in enumerate(movement_indexes):
                            # prevent stack overflow
                            if i > len(movement_indexes) - 2:
                                break

                            # get line extrusion data to calculate how much valve should move
                            valve_line = lines_with_valve[idx]
                            extrusion_index = valve_line.get_index_prefix("E")
                            # skip line if there is no extrusion
                            if extrusion_index == -1:
                                valve_line.add_comment("no extrusion valve routine")
                                continue
                            extrusion_length = valve_line.get_command_part_number("E")
                            volume = gp.get_volume_form_extrusion_length(extrusion_length)
                            # if last line has too much extruded material,
                            # split it into 2 lines with normal extrusion and valve extrusion
                            if valve_volume_left - volume < 0.0:
                                valve_line.add_comment(
                                    f"line should be split extrusion {extrusion_length} volume {volume} ")
                                try:
                                    # coef - tells how many percents of line should be extruded with valve
                                    coef = valve_volume_left / volume
                                    # get prev movement line to calculate distance between lines
                                    prev_line = lines_with_valve[movement_indexes[i + 1]]
                                    # build a new line with normal extrusion that will be followed with valve
                                    # extrusion line
                                    line = gp.split_line_by_coef(valve_line,
                                                                 prev_line,
                                                                 extrusion_length,
                                                                 coef)
                                    lines_with_valve.insert(idx, line)
                                except Exception as e:
                                    logging.error(f"exception during valve routines {e}")
                                    traceback.print_exc()
                            # remove extrusion part since we add valve command
                            valve_line.remove_command_part(extrusion_index)
                            valve_line.add_comment(f"removed extrusion {extrusion_length}")
                            b_number = gp.get_valve_opening(valve_volume, valve_volume_left)
                            valve_line.command_parts.append(f"B{b_number}")
                            valve_volume_left -= volume
                            valve_line.add_comment("valve routine")
                            if valve_volume_left < 0:
                                break
                        lines_with_valve.append(gp.GcodeLine("; valve routine end, retraction removed"))
                        continue

                        valve_state = gp.ValveState.Closed
                    elif valve_state in [gp.ValveState.Closed, gp.ValveState.Undefined]:
                        # we have extrusion but valve is closed add valve open command
                        valve_state = gp.ValveState.Opened
                        lines_with_valve.append(
                            gp.create_valve_open_fill_command(nozzle_diameter, tool, valve_state))
                        pl.add_comment("added valve opening before")
                    extrusion_position = pl.get_index_prefix("E")
                    # get extrusion command for printer and tool
                    ext = gp.get_extrusion_letter(self.model, pl.tool)
                    pl.command_parts[extrusion_position].replace("E", ext)
            pl.valve_state = valve_state
            lines_with_valve.append(pl)

        # todo make it writing directly to stream
        rendered_lines = []
        for i, pl in enumerate(lines_with_valve):
            if pl is None:
                logging.error(f"{i} is none")
            rendered_lines.append(pl.render())

        return "\n".join(rendered_lines)

    def execute(self, data: str) -> str:
        lines = data.split("\n")
        result = ""
        for line in lines:
            comment_index = line.find(";")
            if comment_index >= 0:
                comment = line[comment_index + 1:]
                line = line[0:comment_index]
            else:
                comment = ""
            result += self.executor_func(line, comment)
        return result

    # valve_close_routine - adds the B0 to B1 command to gcode if valve should be opened or closed
    def valve_close_routine(self, line, tool_for_line) -> str:
        if self.roboxCloseValve:
            if re.search(self.retractPattern, line) and (
                    self.valve_state == ValveState.Undefined or self.valve_state == ValveState.Opened):  # There is 'E-xxx" in the line - add closing valve
                if tool_for_line == "T1":
                    line = line.replace("E", "B0 E")  # Close valve and use second extruder
                elif tool_for_line == "T0":
                    line = line.replace("E", "B0 D")  # Close valve
                self.valve_state = ValveState.Closed
            if re.search(self.forwardPattern, line) and (
                    self.valve_state == ValveState.Undefined or self.valve_state == ValveState.Closed):  # There is 'Exxx' in the line - add opening valve
                if tool_for_line == "T1":
                    line = line.replace("E", "B1 E")  # Open valve and use second extruder
                elif tool_for_line == "T0":
                    line = line.replace("E", "B1 D")  # Open valve
                self.valve_state = ValveState.Opened

        # elif self.valve_state == ValveState.Undefined or self.valve_state == ValveState.Closed:
        else:  # No close valve handling needed
            if tool_for_line == "T0":  # We are using second tool - so we need second extruder as well
                if re.search(self.forwardPattern, line) or re.search(self.retractPattern, line):
                    line = line.replace("E", "B1 D")
            else:
                if re.search(self.forwardPattern, line) or re.search(self.retractPattern, line):
                    line = line.replace("E", "B1 E")
            self.valve_state = ValveState.Opened
        return line

    def dualRobox(self, line, comment):
        result = ""
        toolForLine = self.selectedTool
        if re.search(self.t0Pattern, line):
            if toolForLine != "T0":  # Tool change
                if not line.startswith("T0"):
                    line = line.replace(" T0", "") + " ; removed T0 from the middle"  # Remove tool change
                    toolForLine = "T0"
                else:
                    self.selectedTool = "T0"
                    toolForLine = self.selectedTool
            else:  # No tool changes
                if line.startswith("T0"):  # This is solitary T0 - so remove it
                    comment = comment + " Duplicate T0"
                    self.selectedTool = "T0"
                    toolForLine = self.selectedTool
                else:
                    line = line.replace("T0 ", "")
                    comment = comment + " removed T0 from the middle (no tool change)"  # Remove T0 in the middle of the command as no tool change

        elif re.search(self.t1Pattern, line):
            if toolForLine != "T1":  # Tool change
                if not line.startswith("T1"):
                    # output += "T1 ; forced T1 \n"  # Line is not T1 so we need to add T0 before this line to initiate tool change
                    line = line.replace(" T1", "")
                    comment = comment + " removed T1 from the middle"  # Remove tool change
                    toolForLine = "T1"
                else:
                    self.selectedTool = "T1"
                    toolForLine = self.selectedTool
            else:  # No tool changes
                if line.startswith("T1"):  # This is solitary T1 - so remove it
                    comment = comment + " Duplicate T1"
                    self.selectedTool = "T1"
                    toolForLine = self.selectedTool
                else:
                    line = line.replace("T1 ", "")
                    comment = comment + " removed T1 from the middle (no tool change)"  # Remove T1 in the middle of the command as no tool change

        if toolForLine == "T1" and ("M103" in line or "M104" in line or "M109" in line):
            hasS = re.search(self.sTemperaturePattern, line)
            hasT = re.search(self.tTemperaturePattern, line)

            # There is 'Sxxx' in the line and second tool is selected and line doesn't contain both
            if hasS and not hasT:
                line = line.replace("S", "T")  # Replace "Sxxx" with "Txxx"

        if line.startswith("M109 "):
            line = line + "\n" + "M109 \n"

        line = self.valve_close_routine(line, toolForLine)

        if comment != "":
            result += line + " ;" + comment + "\n"
        else:
            result += line + "\n"
        return result

    def QuickFillRobox(self, line, comment) -> str:
        result = ""
        toolForLine = self.selectedTool
        if re.search(self.t0Pattern, line):
            if toolForLine != "T0":  # Tool change
                if not line.startswith("T0"):
                    line = line.replace(" T0", "") + " ; removed T0 from the middle"  # Remove tool change
                    toolForLine = "T0"
                else:
                    self.selectedTool = "T0"
                    toolForLine = self.selectedTool
            else:  # No tool changes
                if line.startswith("T0"):  # This is solitary T0 - so remove it
                    comment = comment + "T0"
                    self.selectedTool = "T0"
                    toolForLine = self.selectedTool
                else:
                    line = line.replace("T0 ", "")
                    comment = comment + " removed T0 from the middle (no tool change)"  # Remove T0 in the middle of the command as no tool change

        elif re.search(self.t1Pattern, line):
            if toolForLine != "T1":  # Tool change
                if not line.startswith("T1"):
                    # output += "T1 ; forced T1 \n"  # Line is not T1 so we need to add T0 before this line to initiate tool change
                    line = line.replace(" T1", "")
                    comment = comment + " removed T1 from the middle"  # Remove tool change
                    toolForLine = "T1"
                else:
                    self.selectedTool = "T1"
                    toolForLine = self.selectedTool
            else:  # No tool changes
                if line.startswith("T1"):  # This is solitary T1 - so remove it
                    comment = comment + "T1"
                    self.selectedTool = "T1"
                    toolForLine = self.selectedTool
                else:
                    line = line.replace("T1 ", "")
                    comment = comment + " removed T1 from the middle (no tool change)"  # Remove T1 in the middle of the command as no tool change

        if line.startswith("M109 "):
            line = line + "\n" + "M109 \n"

        if self.roboxCloseValve:
            if re.search(self.retractPattern, line):  # There is 'E-xxx" in the line - add closing valve
                if toolForLine == "T1":
                    line = line.replace("E", "B0 E")  # Close valve and use second extruder
                elif toolForLine == "T0":
                    line = line.replace("E", "B0 E")  # Close valve
            if re.search(self.forwardPattern, line):  # There is 'Exxx' in the line - add opening valve
                if toolForLine == "T1":
                    line = line.replace("E", "B1 E")  # Open valve and use second extruder
                elif toolForLine == "T0":
                    line = line.replace("E", "B1 E")  # Open valve

        else:  # No close valve handling needed
            if toolForLine == "T0":  # We are using second tool - so we need second extruder as well
                if re.search(self.forwardPattern, line) or re.search(self.retractPattern, line):
                    line = line.replace("E", "B1 E")
            else:
                if re.search(self.forwardPattern, line) or re.search(self.retractPattern, line):
                    line = line.replace("E", "B1 E")

        if comment != "":
            result += line + " ;" + comment + "\n"
        else:
            result += line + "\n"
        return result
