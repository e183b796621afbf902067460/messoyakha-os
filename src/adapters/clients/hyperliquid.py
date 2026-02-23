from typing import Any

from attr import attrs
from hyperliquid.info import Info
from hyperliquid.utils import constants


@attrs(slots=False, auto_attribs=True, kw_only=True)
class HyperliquidAPIClient:
    def __attrs_post_init__(self) -> None:
        self._info: Info = Info(base_url=constants.MAINNET_API_URL, skip_ws=True)

    def meta_and_asset_ctxs(self) -> Any:
        return self._info.meta_and_asset_ctxs()
