"""Stripe adapter — payments, subscriptions, customers."""

import httpx
from typing import Dict, Any, List, Optional
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.stripe")


class StripeAdapter(MCPAdapter):
    name = "stripe"
    description = "Stripe — payments, customers, subscriptions, invoices"

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.stripe.com/v1"
        self.headers = {"Authorization": f"Bearer {settings.stripe_api_key}"}
        self.register_tool("stripe_create_customer", "Create a customer", {"email": {"type": "string"}, "name": {"type": "string"}, "metadata": {"type": "object"}}, ["email"], self._create_customer)
        self.register_tool("stripe_get_customer", "Retrieve a customer", {"customer_id": {"type": "string"}}, ["customer_id"], self._get_customer)
        self.register_tool("stripe_create_charge", "Create a charge", {"amount": {"type": "integer"}, "currency": {"type": "string"}, "customer": {"type": "string"}, "description": {"type": "string"}}, ["amount", "currency"], self._create_charge)
        self.register_tool("stripe_list_invoices", "List invoices for a customer", {"customer_id": {"type": "string"}, "limit": {"type": "integer"}}, ["customer_id"], self._list_invoices)
        self.register_tool("stripe_create_subscription", "Create a subscription", {"customer": {"type": "string"}, "price": {"type": "string"}, "metadata": {"type": "object"}}, ["customer", "price"], self._create_subscription)

    @circuit("stripe", failure_threshold=5, recovery_timeout=60)
    async def _create_customer(self, email: str, name: str = "", metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        data = {"email": email, "name": name}
        if metadata:
            data.update({f"metadata[{k}]": v for k, v in metadata.items()})
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/customers", headers=self.headers, data=data)
            resp.raise_for_status()
            return resp.json()

    @circuit("stripe", failure_threshold=5, recovery_timeout=60)
    async def _get_customer(self, customer_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/customers/{customer_id}", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    @circuit("stripe", failure_threshold=5, recovery_timeout=60)
    async def _create_charge(self, amount: int, currency: str, customer: str = "", description: str = "") -> Dict[str, Any]:
        data = {"amount": amount, "currency": currency, "description": description}
        if customer:
            data["customer"] = customer
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/charges", headers=self.headers, data=data)
            resp.raise_for_status()
            return resp.json()

    @circuit("stripe", failure_threshold=5, recovery_timeout=60)
    async def _list_invoices(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/invoices", headers=self.headers, params={"customer": customer_id, "limit": limit})
            resp.raise_for_status()
            return resp.json().get("data", [])

    @circuit("stripe", failure_threshold=5, recovery_timeout=60)
    async def _create_subscription(self, customer: str, price: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        data = {"customer": customer, "items[0][price]": price}
        if metadata:
            data.update({f"metadata[{k}]": v for k, v in metadata.items()})
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/subscriptions", headers=self.headers, data=data)
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/balance", headers=self.headers)
                resp.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
