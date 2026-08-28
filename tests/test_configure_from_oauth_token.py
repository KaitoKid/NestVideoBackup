import configparser
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import configure_from_oauth_token as helper


class ConfigureFromOauthTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.config_path = Path(self.temporary_directory.name) / "nest.ini"

    def run_helper(self, exchange_response: dict[str, str]) -> tuple[int, str]:
        output = io.StringIO()
        with (
            mock.patch.object(helper, "CONFIG_PATH", self.config_path),
            mock.patch("builtins.input", return_value="example@gmail.com"),
            mock.patch.object(
                helper.getpass,
                "getpass",
                return_value="oauth2_4/temporary-test-token",
            ),
            mock.patch.object(
                helper, "exchange_token", return_value=exchange_response
            ),
            contextlib.redirect_stdout(output),
        ):
            result = helper.main()
        return result, output.getvalue()

    def test_success_preserves_config_and_never_prints_tokens(self) -> None:
        self.config_path.write_text(
            "[nest]\n"
            "timezone = Europe/London\n"
            "refresh_interval = 15\n",
            encoding="utf-8",
        )

        result, output = self.run_helper({"Token": "aas_et/test-master-token"})

        saved = configparser.ConfigParser()
        saved.read(self.config_path)
        self.assertEqual(result, 0)
        self.assertEqual(saved["nest"]["timezone"], "Europe/London")
        self.assertEqual(saved["nest"]["refresh_interval"], "15")
        self.assertEqual(saved["nest"]["google_username"], "example@gmail.com")
        self.assertEqual(
            saved["nest"]["google_master_token"], "aas_et/test-master-token"
        )
        self.assertNotIn("temporary-test-token", self.config_path.read_text())
        self.assertNotIn("temporary-test-token", output)
        self.assertNotIn("test-master-token", output)
        self.assertEqual(self.config_path.stat().st_mode & 0o777, 0o600)

    def test_failed_exchange_does_not_create_config(self) -> None:
        result, output = self.run_helper({"Error": "BadAuthentication"})

        self.assertEqual(result, 1)
        self.assertFalse(self.config_path.exists())
        self.assertIn("AUTH_FAILED BadAuthentication", output)
        self.assertNotIn("temporary-test-token", output)


if __name__ == "__main__":
    unittest.main()
