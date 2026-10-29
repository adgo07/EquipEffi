"""Owner额定效率决定：新旧数值口径、单位及历史边界。"""
import unittest
from decimal import Decimal, localcontext
from equipeffi.domain.devices.motor.calculator import Gb18613MotorCalculator
from equipeffi.domain.devices.motor.input_contract import normalize_motor_input, visible_fields, MotorInputError
from equipeffi.infrastructure.standards.motor_repository import load_motor_pack


class MotorRatedInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack, _ = load_motor_pack()
        cls.calc = Gb18613MotorCalculator()

    def values(self, **extra):
        return dict(category_id='three_phase_induction', input_contract_revision='motor-input.v3',
                    rated_output_power_kw='0.14', poles='4', rated_voltage_v='380',
                    rated_frequency_hz='50', rated_efficiency_pct='71.43', **extra)

    def evaluate(self, values):
        return self.calc.evaluate(values, self.pack)

    def test_new_rated_and_legacy_measured_share_exact_limits(self):
        new = self.evaluate(self.values())
        old = self.evaluate(dict(category_id='three_phase_induction', rated_output_power_kw='0.14',
            poles='4', rated_voltage_kv='0.38', rated_frequency_hz='50', measured_efficiency_pct='71.43'))
        self.assertEqual(new.grade, '3')
        self.assertEqual(new.thresholds, old.thresholds)
        self.assertEqual(Decimal(new.trace[0]['normalized_voltage_kv']), Decimal('0.38'))
        self.assertEqual(new.trace[0]['efficiency_basis_status'], 'RATED_NAMEPLATE')
        self.assertIn('额定效率', new.explanation)
        self.assertNotIn('measured_efficiency_pct', new.trace[0]['comparison'])

    def test_voltage_boundaries_and_conversion_ignore_decimal_context(self):
        for category, voltage, expected in (
            ('three_phase_induction', '999.99999999999999999999', 'SUCCESS'),
            ('three_phase_induction', '1000', 'OUT_OF_STANDARD_SCOPE'),
            ('capacitor_run', '690', 'SUCCESS'),
            ('capacitor_run', '690.000000000000000001', 'OUT_OF_STANDARD_SCOPE')):
            values = self.values()
            values.update(category_id=category, rated_voltage_v=voltage, rated_output_power_kw='0.75', rated_efficiency_pct='90')
            with self.subTest(voltage=voltage), localcontext() as context:
                context.prec = 3
                self.assertEqual(self.evaluate(values).evaluation_status, expected)

    def test_rated_percentage_guard_and_missing_fields(self):
        for efficiency in ('0.85', '100.01', 'NaN'):
            values = self.values(); values['rated_efficiency_pct'] = efficiency
            result = self.evaluate(values)
            self.assertEqual(result.evaluation_status, 'INVALID_INPUT')
            self.assertIn('rated_efficiency_pct', result.invalid_fields)
        values = self.values(); del values['rated_voltage_v']
        self.assertIn('rated_voltage_v', self.evaluate(values).missing_fields)
        values = self.values(); del values['rated_efficiency_pct']
        self.assertIn('rated_efficiency_pct', self.evaluate(values).missing_fields)

    def test_legacy_nameplate_gate_is_not_reinterpreted(self):
        old = dict(category_id='three_phase_induction', rated_output_power_kw='0.14', poles='4',
                   rated_voltage_kv='0.38', rated_frequency_hz='50', measured_efficiency_pct='90',
                   efficiency_basis_status='NAMEPLATE_ONLY')
        self.assertEqual(self.evaluate(old).evaluation_status, 'INSUFFICIENT_DATA')
        self.assertEqual(self.evaluate(self.values()).evaluation_status, 'SUCCESS')

    def test_mixed_contracts_rejected_and_new_form_has_no_basis(self):
        for extra in ({'rated_voltage_kv': '0.38'}, {'measured_efficiency_pct': '90'},
                      {'efficiency_basis_status': 'NAMEPLATE_ONLY'}):
            with self.subTest(extra=extra), self.assertRaises(MotorInputError):
                normalize_motor_input(self.values(**extra))
        fields = {field.field_id: field for field in visible_fields('three_phase_induction')}
        self.assertEqual(fields['rated_voltage_v'].unit, 'V')
        self.assertEqual(fields['rated_efficiency_pct'].label, '额定效率')
        self.assertNotIn('efficiency_basis_status', fields)
