class BikeSharingError(Exception):
    """Base exception for expected bike-sharing domain errors."""


class DockOccupiedError(BikeSharingError):
    pass


class RideActiveError(BikeSharingError):
    pass


class NoBikeError(BikeSharingError):
    pass


class NoActiveRideError(BikeSharingError):
    pass


class StationFullError(BikeSharingError):
    def __init__(self, station_name: str, redirect_station: str | None = None) -> None:
        self.station_name = station_name
        self.redirect_station = redirect_station
        message = f"{station_name} has no free docks"
        if redirect_station is not None:
            message += f"; try {redirect_station}"
        super().__init__(message)
