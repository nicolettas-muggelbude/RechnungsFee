import json
import unittest

from pruefung import pruefe_kunde


class KundenpruefungTest(unittest.TestCase):
    def test_email_normalisieren_und_andere_felder_erhalten(self):
        original = {'_schema': 'customer@1', 'id': 42, 'firmenname': 'Büro Müller',
                    'email': ' kontakt@example.org ', 'notizen': 'Unverändert'}
        erwartet = {**original, 'email': 'kontakt@example.org'}
        self.assertEqual(json.loads(pruefe_kunde(json.dumps(original))), erwartet)

    def test_privatkunde_ohne_firmenname_ist_erlaubt(self):
        daten = {'_schema': 'customer@1', 'vorname': 'Ada', 'nachname': 'Lovelace', 'email': None}
        self.assertEqual(json.loads(pruefe_kunde(json.dumps(daten))), daten)

    def test_fehlender_name_bricht_ab(self):
        for name in ('', '  ', None):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Firmennamen'):
                pruefe_kunde(json.dumps({'_schema': 'customer@1', 'firmenname': name}))

    def test_anderes_dto_und_ungueltiges_json_abweisen(self):
        for payload in ('[]', '{}', '{"_schema":"invoice@1"}', '{ungueltig'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                pruefe_kunde(payload)


if __name__ == '__main__':
    unittest.main()
