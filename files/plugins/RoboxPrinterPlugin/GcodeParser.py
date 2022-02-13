import re
import math


class GcodeLine:
    def __init__(self, line: str):
        super().__init__()
        # check if line has comments
        if ";" in line:
            parts = line.split(";")
            if parts[0].strip() == "":
                self.comment = line
            else:
                self.command = parts[0]
                self.comment = parts[1]
        else:
            self.command = line
        # split command to parts to analyze them
        self.command_parts = self.command.split(" ")
        self.tool = ""

    # created a finalized string representation of gocde line
    def render(self) -> str:
        command = ' '.join(self.command_parts)
        return f"{command} ; {self.comment}"

    # returns first item of commands parts
    def get_command_type(self) -> str:
        if len(self.command_parts) == 0:
            return ""
        return self.command_parts[0]

    # tells the position of requested command part
    def get_index_of_command_segment(self, segment: str) -> int:
        index = -1
        for s in self.command_parts:
            if s == segment:
                return index + 1
            index += 1

    # tells the position of requested command part that starts with specific prefix
    def get_index_of_command_segment_starts_with(self, prefix: str) -> int:
        index = -1
        for s in self.command_parts:
            if s.startswith(prefix):
                return index + 1
            index += 1

    # remove part from command sequence by index
    def remove_command_part(self, index: int):
        self.command_parts.pop(index)

    # remove part from command sequence by name
    def remove_command_part_by_name(self, segment: str):
        index = 0
        for s in self.command_parts:
            if s == segment:
                break
        if index < len(self.command_parts):
            self.command_parts.pop(index)

    def get_command_part_number(self, prefix: str) -> float:
        index = self.get_index_of_command_segment_starts_with(prefix)
        if index > -1:
            rr = re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", self.command_parts[index])
            return float(rr[0])


# get distance between lines
def get_distance_between_lines(line1: GcodeLine, line2: GcodeLine) -> float:
    p1 = [line1.get_command_part_number("X"), line1.get_command_part_number("Y")]
    p2 = [line2.get_command_part_number("X"), line2.get_command_part_number("Y")]
    return math.sqrt(((int(p1[0]) - int(p2[0])) ** 2) + ((int(p1[1]) - int(p2[1])) ** 2))


# simplified model of filament line: half cylinder + box + half cylinder
# it will be used to calculate valve close routines
def calculate_line_volume(height: float, width: float, length: float):
    cylinder_volume = math.PI * width / 2 * width / 2 * height
    box_volume = height * width * length
    return box_volume + cylinder_volume
