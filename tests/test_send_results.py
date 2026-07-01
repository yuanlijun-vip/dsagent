import unittest

from refund_recovery.send_results import load_send_results


class SendResultTests(unittest.TestCase):
    def test_sent_result_maps_to_complete_status(self):
        [result] = load_send_results(
            {
                "created_at": "2026-07-01 10:25:53",
                "message_template": "message_templates/refund_recovery_v1.json",
                "results": [
                    {
                        "shop": "艺颂旗舰店",
                        "buyer_id": "世人皆称我为魔",
                        "order_id": "5122187172583017942",
                        "result": "sent",
                        "sent_parts": ["text", "image"],
                    }
                ],
            }
        )

        self.assertEqual(result.send_status, "已发送")
        self.assertEqual(result.process_status, "已发送")
        self.assertEqual(result.template_version, "refund_recovery_v1")
        self.assertIn("text", result.detail)
        self.assertIn("image", result.detail)

    def test_partial_result_remains_exception(self):
        [result] = load_send_results(
            {
                "created_at": "2026-07-01 10:25:53",
                "message_template": "message_templates/refund_recovery_v1.json",
                "results": [
                    {
                        "shop": "艺颂旗舰店",
                        "buyer_id": "欣轩密封件",
                        "order_id": "5122186272767004814",
                        "result": "partial_sent",
                        "sent_parts": ["image"],
                        "not_sent_parts": ["text"],
                    }
                ],
            }
        )

        self.assertEqual(result.send_status, "部分发送")
        self.assertEqual(result.process_status, "发送异常")
        self.assertIn("未发送: text", result.detail)


if __name__ == "__main__":
    unittest.main()
