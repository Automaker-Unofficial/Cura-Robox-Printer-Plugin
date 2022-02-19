import re
import math
import enum
import typing


class ValveState(enum.Enum):
    Opened = "opened"
    Closed = "closed"
    Undefined = "undefined"


class Model(enum.Enum):
    dual = "cel_robox_dual"
    quick_fill = "cel_robox_quickfill"


class Tool(enum.Enum):
    T0 = "T0"
    T1 = "T1"


class GcodeLine:
    def __init__(self, line: str):
        super().__init__()
        # check if line has comments
        self.command = ""
        if ";" in line:
            parts = line.split(";")
            if parts[0].strip() == "":
                self.comment = line
                self.comment = self.comment.replace(";", "", 1)
            else:
                self.command = parts[0]
                self.comment = parts[1]
        else:
            self.command = line
            self.comment = ""
        # split command to parts to analyze them
        self.command_parts = self.command.split(" ")
        for i, c in enumerate(self.command_parts):
            self.command_parts[i] = c.strip()
        self.tool = ""
        self.valve_state = ValveState.Undefined

    # created a finalized string representation of gocde line
    def render(self) -> str:
        if len(self.command_parts) == 0:
            return f";{self.comment}"
        command = ' '.join(self.command_parts)
        if self.comment != "":
            command = f"{command};{self.comment}"
        return command

    def add_comment(self, comment: str):
        delimiter = ""
        if self.comment != "":
            delimiter = ";"
        self.comment += f"{delimiter} {comment}"

    # returns first item of commands parts
    def get_command_type(self) -> str:
        if len(self.command_parts) == 0:
            return ""
        return self.command_parts[0]

    # tells the position of requested command part
    def get_index_of_command_segment(self, segment: str) -> int:
        for i, s in enumerate(self.command_parts):
            if s == segment:
                return i
        return -1

    # tells the position of requested command part that starts with specific prefix
    def get_index_prefix(self, prefix: str) -> int:
        for i, s in enumerate(self.command_parts):
            if s.startswith(prefix):
                return i
        return -1

    # remove part from command sequence by index
    def remove_command_part(self, index: int):
        self.command_parts.pop(index)

    # returns comment
    def get_comment(self) -> str:
        self.comment

    # remove part from command sequence by name
    def remove_command_part_by_name(self, segment: str):
        index = 0
        for s in self.command_parts:
            if s == segment:
                break
        if index < len(self.command_parts) - 1:
            self.command_parts.pop(index)

    def get_command_part_number(self, prefix: str) -> float:
        index = self.get_index_prefix(prefix)
        if index > -1:
            rr = re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", self.command_parts[index])
            return float(rr[0])


# get distance between lines
def get_distance_between_lines(line1: GcodeLine, line2: GcodeLine) -> float:
    p1 = [line1.get_command_part_number("X"), line1.get_command_part_number("Y")]
    p2 = [line2.get_command_part_number("X"), line2.get_command_part_number("Y")]
    return math.sqrt(((p1[0] - p2[0]) ** 2) + ((p1[1] - p2[1]) ** 2))


def split_line_by_coef(line1: GcodeLine, line2: GcodeLine, extrusion, coef) -> GcodeLine:
    p1 = [line1.get_command_part_number("X"), line1.get_command_part_number("Y")]
    p2 = [line2.get_command_part_number("X"), line2.get_command_part_number("Y")]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    multiplier = 1 - coef
    x = round(p1[0] + dx * multiplier, 3)
    y = round(p1[1] + dy * multiplier, 3)
    ext = round(extrusion * multiplier, 4)
    line = GcodeLine(f"G1 X{x} Y{y} E{ext}")
    line.add_comment("split result before valve closing")
    return line


# simplified model of filament line: half cylinder + box + half cylinder
# it will be used to calculate valve close routines
def calculate_line_volume(height: float, width: float, length: float):
    cylinder_volume = math.pi * width / 2 * width / 2 * height
    box_volume = height * width * length
    return box_volume + cylinder_volume


# calculates line from volume to be extracted
def length_from_volume(height: float, width: float, volume: float):
    return volume / (height * width)


robox_dual_extrusion = {
    "TE": "E",
    "T0": "D",
}

quickfill_extrusion = {
    "T0": "E",
    "TE": "E"
}

extrusion_letter = {
    Model.quick_fill.value: {
        "T0": "E",
        "T1": "E"
    },
    Model.dual.value: {
        "T0": "D",
        "T1": "E"
    },
}


def get_extrusion_letter(model, tool):
    return extrusion_letter[model.value][tool]


def create_valve_open_fill_command(diameter: float, tool: str, valve_state: ValveState) -> GcodeLine:
    line = GcodeLine(f"G1 B1 F150 E{round(diameter * 0.75, 3)}")
    line.tool = tool
    line.valve_state = valve_state
    line.add_comment(f"open valve and fill the nozzle {tool} with filament")
    return line


def get_volume_form_extrusion_length(length: float):
    r = 1.75 / 2
    return r ** 2 * math.pi * length


# converts valve volume into valve opening percents
def get_valve_opening(nozzle_volume, volume_to_extrude):
    value = round(1 - (volume_to_extrude / nozzle_volume), 2)
    if value == 0:
        return 0
    return value
