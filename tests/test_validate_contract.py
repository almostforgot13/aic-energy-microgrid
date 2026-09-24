import tempfile
import unittest
from pathlib import Path

from tools.validate_contract import validate


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_samples(self):
        for kind, file in (
            ("clean", "clean_hourly.csv"),
            ("forecast", "forecast_quantiles.csv"),
            ("dispatch", "dispatch_rule.csv"),
        ):
            with self.subTest(kind=kind):
                self.assertGreater(validate(kind, ROOT / "data" / "sample" / file), 0)

    def test_rejects_quantile_crossing(self):
        source = (ROOT / "data" / "sample" / "forecast_quantiles.csv").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text(source.replace(",65,80,95", ",90,80,95"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "分位数交叉"):
                validate("forecast", path)


if __name__ == "__main__":
    unittest.main()
