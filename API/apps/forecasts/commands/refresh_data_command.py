"""Command: triggers a controlled refresh of cached Elexon data for a date
range. State-changing (invalidates and repopulates the cache), so it is
modelled as a command rather than a query."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.forecasts.services import forecast_service


@dataclass(frozen=True)
class RefreshDataCommand:
    start: date
    end: date

    def execute(self) -> dict:
        return forecast_service.refresh_data(self.start, self.end)
