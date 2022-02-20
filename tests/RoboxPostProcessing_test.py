import unittest
from files.plugins.RoboxPrinterPlugin.PostProcessing import RoboxPostProcessing


class TestPostProcessing(unittest.TestCase):
    def test_execute_new(self):
        processor = RoboxPostProcessing.RoboxPostProcessing("cel_robox_dual", True, "development")
        in_file = open("dual_material1_in.stl", "r")
        result, tool = processor.execute(in_file.read(), "T1")
        result_file = open("dual_material1_result.stl", "w")
        result_file.write(result)
        result_file.close()
        out_file = open("dual_material1_out.stl", "r")
        self.assertEqual(out_file.read(), result)
        in_file.close()
        out_file.close()

    def test_valve_open_close(self):
        processor = RoboxPostProcessing.RoboxPostProcessing("cel_robox_dual", True, "development")
        in_file = open("dual_material2_in.stl", "r")
        result, tool = processor.execute(in_file.read(), "T1")
        result_file = open("dual_material2_result.stl", "w")
        result_file.write(result)
        result_file.close()
        out_file = open("dual_material2_out.stl", "r")
        self.assertEqual(out_file.read(), result)
        in_file.close()
        out_file.close()
