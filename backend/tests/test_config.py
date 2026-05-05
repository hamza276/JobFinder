import os
import unittest
from unittest.mock import patch

from app.core.config import Settings


class ConfigTests(unittest.TestCase):
    def test_default_cors_supports_localhost_and_loopback_vite_origins(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

        self.assertIn("http://localhost:5173", settings.CORS_ORIGINS)
        self.assertIn("http://127.0.0.1:5173", settings.CORS_ORIGINS)


if __name__ == "__main__":
    unittest.main()
