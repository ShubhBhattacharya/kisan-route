import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_guardian_json import _read_bundle


class GuardianLegacyImportParsingTests(unittest.TestCase):
    def test_reads_supported_legacy_files_and_hashes_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'guardian_state.json').write_text(json.dumps({'status': 'paused'}), encoding='utf-8')
            (folder / 'guardian_logs.jsonl').write_text(json.dumps({'event_type': 'OLD_EVENT', 'message': 'kept'}) + '\n', encoding='utf-8')
            (folder / 'guardian_issues.json').write_text(json.dumps({'issue-1': {'id': 'issue-1', 'status': 'resolved'}}), encoding='utf-8')
            bundle, digest = _read_bundle(folder)
            self.assertEqual(bundle['guardian_state.json']['status'], 'paused')
            self.assertEqual(bundle['guardian_logs.jsonl'][0]['event_type'], 'OLD_EVENT')
            self.assertEqual(bundle['guardian_issues.json']['issue-1']['status'], 'resolved')
            self.assertEqual(len(digest), 64)

    def test_rejects_malformed_jsonl_with_line_number(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'guardian_logs.jsonl').write_text('{"event_type":"ok"}\n{bad json}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'guardian_logs.jsonl:2'):
                _read_bundle(folder)

    def test_rejects_empty_backup_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'No supported'):
                _read_bundle(Path(temp))


if __name__ == '__main__':
    unittest.main()
