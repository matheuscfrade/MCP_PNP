from __future__ import annotations

import httpx

from mcp_pnp.errors import PnpError


class ExtratorClient:
    def __init__(self, base: str, transport: httpx.BaseTransport | None = None) -> None:
        self.base = base.rstrip("/")
        self._transport = transport

    def download_csv(self, query_id: int) -> str:
        urls = (
            f"{self.base}/pnpquery/{query_id}/csv",
            f"{self.base}/pnpquery/{query_id}?format=csv",
            f"{self.base}/api/pnpquery/{query_id}/download",
        )
        with httpx.Client(
            transport=self._transport, timeout=60.0, follow_redirects=True
        ) as http:
            last = None
            for url in urls:
                resp = http.get(url)
                last = resp
                if resp.status_code == 200 and _parece_csv(resp.text):
                    return resp.text
        detalhe = f"query {query_id} status={getattr(last, 'status_code', '?')}"
        raise PnpError("sync_falhou", detalhe)


def _parece_csv(text: str) -> bool:
    head = text.splitlines()[0] if text else ""
    return ("Ano" in head) and ("Instituicao" in head or "Instituição" in head)
