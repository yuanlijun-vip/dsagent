import unittest
from datetime import datetime

from refund_recovery.dingtalk import enabled_shops
from refund_recovery.models import CustomerProbe, RefundOrder
from refund_recovery.probes import CustomerProbeProvider
from refund_recovery.workflow import _existing_order_keys, previous_day_window


class WorkflowHelpersTests(unittest.TestCase):
    def test_previous_day_window(self):
        start, end = previous_day_window(datetime(2026, 6, 30, 13, 20, 0))
        self.assertEqual(start.isoformat(sep=" "), "2026-06-29 00:00:00")
        self.assertEqual(end.isoformat(sep=" "), "2026-06-30 23:59:59")

    def test_enabled_shops(self):
        rows = [
            ["店铺名", "是否"],
            ["店铺A", "是"],
            ["店铺B", "否"],
            ["店铺C", "是"],
        ]
        shops = enabled_shops(rows, "店铺名", "是否")
        self.assertEqual([shop.name for shop in shops], ["店铺A", "店铺C"])

    def test_existing_order_keys(self):
        rows = [
            ["店铺名", "订单号", "旺旺ID"],
            ["店铺A", "1001", "buyer-a"],
        ]
        self.assertEqual(_existing_order_keys(rows), {("店铺A", "1001", "buyer-a")})


class FakeProbe(CustomerProbeProvider):
    def probe(self, order: RefundOrder) -> CustomerProbe:
        return CustomerProbe(today_chatted=order.buyer_id == "chatted")


if __name__ == "__main__":
    unittest.main()
