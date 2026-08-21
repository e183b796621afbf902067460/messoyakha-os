from typing import Final

from nautilus_trader.model.identifiers import ClientId, Venue


XCEC: Final[str] = "XCEC"

XCEC_VENUE: Final[Venue] = Venue(XCEC)
XCEC_CLIENT_ID: Final[ClientId] = ClientId(XCEC)
