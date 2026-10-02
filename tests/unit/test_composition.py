from pathlib import Path
import unittest
from unittest.mock import patch

from equipeffi.composition import create_core_api, load_v4_contract
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLReadError


class CompositionTests(unittest.TestCase):
    def test_core_factory_never_loads_template(self):
        with patch("equipeffi.composition.load_v4_contract", side_effect=AssertionError):
            self.assertEqual(len(create_core_api().device_types()), 15)

    def test_expected_template_damage_warns_and_falls_back(self):
        with patch("equipeffi.infrastructure.excel.v4_reader.V4WorkbookReaderImpl.read_contract",
                   side_effect=OOXMLReadError("damaged")):
            with self.assertLogs("equipeffi.composition", level="WARNING") as logs:
                self.assertEqual(load_v4_contract(), (None, None))
            self.assertIn("damaged", logs.output[0])

    def test_unknown_template_error_propagates(self):
        with patch("equipeffi.infrastructure.excel.v4_reader.V4WorkbookReaderImpl.read_contract",
                   side_effect=RuntimeError("unexpected bug")):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                load_v4_contract()
