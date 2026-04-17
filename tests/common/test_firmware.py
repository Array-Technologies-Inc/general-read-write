import unittest
from tests.common import common
from common.firmware import Firmware


class FirmwareTest(unittest.TestCase):

    def setUp(self):
        self.firmware = Firmware(common.FRIMWARE_DIR)

    def test_load_tsc_frm_list(self):
        spec_list = sorted([
            {'path': 'tests/resources/imagen_v06.bin', 'version': '06'},
            {'path': 'tests/resources/imagen_v04.bin', 'version': '04'}],
                key=lambda d: d['version'])
        self.firmware.load_tsc_frm_list()
        result_list = sorted(self.firmware.get_tsc_frm_list(), key=lambda d: d['version'])
        self.assertListEqual(result_list, spec_list)

    def test_load_iwc_frm_list(self):
        spec_list = sorted([
            {'path': 'tests/resources/221017 RSUR14 Release.bin',
             'version': '14'},
            {'path': 'tests/resources/230217 RSUR15 Release.bin',
             'version': '15'}],
                key=lambda d: d['version'])
        self.firmware.load_iwc_frm_list()
        result_list = sorted(self.firmware.get_iwc_frm_list(), key=lambda d: d['version'])
        self.assertListEqual(result_list, spec_list)

    def test_load_frm_list(self):
        spec_tsc_list = sorted([
            {'path': 'tests/resources/imagen_v04.bin', 'version': '04'},
            {'path': 'tests/resources/imagen_v06.bin', 'version': '06'}],
                key=lambda d: d['version'])
        spec_iwc_list = sorted([
            {'path': 'tests/resources/221017 RSUR14 Release.bin',
             'version': '14'},
            {'path': 'tests/resources/230217 RSUR15 Release.bin',
             'version': '15'}],
                key=lambda d: d['version'])

        self.firmware.load_frm_list()
        result_tsc_list = sorted(self.firmware.get_tsc_frm_list(), key=lambda d: d['version'])
        self.assertListEqual(result_tsc_list, spec_tsc_list)
        result_iwc_list = sorted(self.firmware.get_iwc_frm_list(), key=lambda d: d['version'])
        self.assertListEqual(result_iwc_list, spec_iwc_list)

        full_result = self.firmware.get_frm_list()

        self.assertDictEqual(full_result,
                             {"tsc": spec_tsc_list, "iwc": spec_iwc_list})

    def test_get_file_size(self):
        spec_file_size = 161864
        file_size = self.firmware.get_file_size(
            'tests/resources/imagen_v06.bin')
        self.assertEqual(spec_file_size, file_size)

        spec_file_size = 161352
        file_size = self.firmware.get_file_size(
            'tests/resources/imagen_v04.bin')
        self.assertEqual(spec_file_size, file_size)

        spec_file_size = 83652
        file_size = self.firmware.get_file_size(
            'tests/resources/221017 RSUR14 Release.bin')
        self.assertEqual(spec_file_size, file_size)

        spec_file_size = 84342
        file_size = self.firmware.get_file_size(
            'tests/resources/230217 RSUR15 Release.bin')
        self.assertEqual(spec_file_size, file_size)

    def test_get_file_checksum(self):
        spec_file_checksum = 161
        file_checksum = self.firmware.get_file_checksum(
            'tests/resources/imagen_v06.bin')
        self.assertEqual(spec_file_checksum, file_checksum)

        spec_file_checksum = 101
        file_checksum = self.firmware.get_file_checksum(
            'tests/resources/imagen_v04.bin')
        self.assertEqual(spec_file_checksum, file_checksum)

    def test_get_tsc_file_byte_array(self):

        spec_first_tsc_file_byte_array = [
            32768, 8192, 17677, 1, 17653, 1, 17653, 1,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 17653, 1,
            0, 0, 0, 0, 17653, 1, 17773, 1]
        spec_random_tsc_file_byte_array = [
            13110, 30746, 19255, 28698, 35, 13111, 30746, 19254,
            28698, 35, 13112, 30746, 19252, 28698, 35, 13113,
            30746, 19251, 28698, 27618, 19250, 24602, 27682, 19250,
            24602, 7587, 36826, 19249, 32794, 35, 13064, 36826]
        spec_last_tsc_file_byte_array = [
            0, 0, 0, 0, 65535, 65535, 65535, 65535,
            65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535,
            65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535,
            65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535]
        spec_len_byte_array = 2530
        spec_len_frame = 32

        tsc_file_byte_array = self.firmware.get_tsc_file_byte_array(
            'tests/resources/imagen_v06.bin')

        self.assertEqual(spec_len_byte_array, len(tsc_file_byte_array))

        self.assertEqual(spec_len_frame, len(tsc_file_byte_array[0]))
        self.assertEqual(spec_len_frame, len(tsc_file_byte_array[1000]))
        self.assertEqual(spec_len_frame, len(tsc_file_byte_array[-1]))

        self.assertListEqual(
            spec_first_tsc_file_byte_array, tsc_file_byte_array[0])
        self.assertListEqual(
            spec_random_tsc_file_byte_array, tsc_file_byte_array[1000])
        self.assertListEqual(
            spec_last_tsc_file_byte_array, tsc_file_byte_array[-1])

    def test_get_file_crc(self):

        spec_file_crc = 7145
        iwc_file_byte_array = self.firmware.get_iwc_file_byte_array(
            'tests/resources/221017 RSUR14 Release.bin')
        file_crc = self.firmware.get_file_crc(iwc_file_byte_array)
        self.assertEqual(spec_file_crc, file_crc)

    def test_get_iwc_file_byte_array(self):

        spec_first_iwc_file_byte_array = [
            61312, 61442, 0, 0, 28164, 53208, 61445, 53216,
            61446, 256, 53225, 61452, 53226, 61447, 53217, 61448]
        spec_random_iwc_file_byte_array = [
            3584, 258, 10127, 20483, 9104, 268, 11052, 46296,
            11053, 49808, 64562, 49807, 64561, 3585, 9516, 28469]
        spec_last_iwc_file_byte_array = [
            61428, 61467, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        spec_len_byte_array = 2615
        spec_len_frame = 16

        iwc_file_byte_array = self.firmware.get_iwc_file_byte_array(
            'tests/resources/221017 RSUR14 Release.bin')

        self.assertEqual(spec_len_byte_array, len(iwc_file_byte_array))

        self.assertEqual(spec_len_frame, len(iwc_file_byte_array[0]))
        self.assertEqual(spec_len_frame, len(iwc_file_byte_array[1000]))
        self.assertEqual(spec_len_frame, len(iwc_file_byte_array[-1]))

        self.assertListEqual(
            spec_first_iwc_file_byte_array, iwc_file_byte_array[0])
        self.assertListEqual(
            spec_random_iwc_file_byte_array, iwc_file_byte_array[1000])
        self.assertListEqual(
            spec_last_iwc_file_byte_array, iwc_file_byte_array[-1])
