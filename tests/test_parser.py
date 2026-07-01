import csv
import tempfile
import unittest
from pathlib import Path

from refund_recovery.parser import parse_export_file


class ParserTests(unittest.TestCase):
    def test_parse_csv_export_with_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "旗舰店A_未发货仅退款.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["主订单编号", "买家旺旺", "申请时间", "交易状态"])
                writer.writerow(["1001", "buyer-a", "2026-06-30 10:00:00", "退款中"])

            orders = parse_export_file(path, "旗舰店A")

        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].order_id, "1001")
        self.assertEqual(orders[0].buyer_id, "buyer-a")
        self.assertEqual(orders[0].refund_time, "2026-06-30 10:00:00")
        self.assertEqual(orders[0].order_status, "退款中")

    def test_parse_optional_probe_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "旗舰店A_未发货仅退款.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["订单号", "旺旺ID", "是否未完结订单", "今日是否已对话"])
                writer.writerow(["1001", "buyer-a", "是", "否"])

            orders = parse_export_file(path, "旗舰店A")

        self.assertTrue(orders[0].has_unfinished_order)
        self.assertFalse(orders[0].today_chatted)


if __name__ == "__main__":
    unittest.main()
