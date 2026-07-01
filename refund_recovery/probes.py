from __future__ import annotations

from .models import CustomerProbe, RefundOrder


class CustomerProbeProvider:
    def probe(self, order: RefundOrder) -> CustomerProbe:
        raise NotImplementedError


class NoopCustomerProbeProvider(CustomerProbeProvider):
    """Safe v1 probe.

    The real QianNiu/window automation is intentionally isolated here. Until
    selectors and window routing are confirmed, this provider never sends
    messages and only reports unknown checks as false.
    """

    def probe(self, order: RefundOrder) -> CustomerProbe:
        return CustomerProbe(
            today_chatted=order.today_chatted,
            has_unfinished_order=order.has_unfinished_order,
        )
