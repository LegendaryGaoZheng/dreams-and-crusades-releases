"""Temporary fixtures verify managed publication inputs and inventory failures."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from modpack_state import audit, resolve_source, managed_files


class StateTest(unittest.TestCase):
    def test_consistency_and_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / 'mods').mkdir()
            (base / 'mods/automodpack-mc1.21.1-neoforge-4.0.7.jar').write_bytes(b'bootstrap fixture')
            root = base / 'automodpack/modpacks/test'
            (root / 'mods').mkdir(parents=True)
            data = b'fixture mod'
            item = {'file': '/mods/test.jar', 'size': str(len(data)), 'sha1': hashlib.sha1(data).hexdigest()}
            config = base / 'automodpack/automodpack-client.json'
            config.write_text(json.dumps({'selectedModpack': 'test'}))
            (root / 'automodpack-content.json').write_text(json.dumps({'list': [item]}))
            jar = root / 'mods/test.jar'
            jar.write_bytes(data)
            self.assertTrue(audit(base)['consistent'])
            self.assertEqual(resolve_source(base.resolve(), 'mods/test.jar'), jar.resolve())
            # Disabled files never count as enabled copies.
            (base / 'mods/test.jar.disabled').write_bytes(b'old disabled version')
            self.assertTrue(audit(base)['consistent'])
            (base / 'mods/test.jar').write_bytes(b'different enabled version')
            self.assertFalse(audit(base)['consistent'])
            with self.assertRaises(ValueError):
                resolve_source(base.resolve(), 'mods/test.jar')
            (base / 'mods/test.jar').unlink()
            jar.unlink()
            self.assertFalse(audit(base)['consistent'])
            with self.assertRaises(ValueError):
                resolve_source(base.resolve(), 'mods/test.jar')
            jar.write_bytes(data)
            (root / 'mods/extra.jar').write_bytes(b'unlisted')
            self.assertFalse(audit(base)['consistent'])
            config.write_text(json.dumps({'selectedModpack': '../escape'}))
            with self.assertRaises(ValueError):
                managed_files(base)


if __name__ == '__main__':
    unittest.main()
