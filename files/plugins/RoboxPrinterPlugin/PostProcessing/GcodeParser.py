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

    def contains_prefix(self, prefix: str) -> bool:
        return self.get_index_prefix(prefix) > -1

    def get_command_part_number(self, prefix: str) -> float:
        index = self.get_index_prefix(prefix)
        if index > -1:
            rr = re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", self.command_parts[index])
            return float(rr[0])


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


def get_volume_form_extrusion_length(length: float):
    r = 1.75 / 2
    return r ** 2 * math.pi * length
