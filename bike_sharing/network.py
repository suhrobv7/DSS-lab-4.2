from datetime import datetime
from typing import Iterable

from .errors import (
    NoActiveRideError,
    NoBikeError,
    RideActiveError,
    StationFullError,
)
from .models import Ride, Station, User
from .receipt import ReceiptPrinter


class BikeSharingNetwork:
    def __init__(
        self,
        stations: Iterable[Station],
    ) -> None:
        self._stations = tuple(stations)
        if not self._stations:
            raise ValueError("A network must have at least one station")
        names = [station.name for station in self._stations]
        if len(names) != len(set(names)):
            raise ValueError("Station names must be unique")
        self._rides: list[Ride] = []

    @property
    def stations(self) -> tuple[Station, ...]:
        return self._stations

    @property
    def rides(self) -> tuple[Ride, ...]:
        return tuple(self._rides)

    def get_station(self, station: str | Station) -> Station:
        if isinstance(station, Station):
            if station not in self._stations:
                raise ValueError(f"{station.name} is not part of this network")
            return station
        for known_station in self._stations:
            if known_station.name == station:
                return known_station
        raise ValueError(f"Unknown station: {station}")

    def take_bike(self, user: User, station: str | Station, at: datetime) -> Ride:
        if user.active_ride is not None:
            raise RideActiveError(f"{user.name} already has an active ride")
        origin = self.get_station(station)
        bike = origin.take_bike()
        if bike is None:
            raise NoBikeError(f"No available bikes at {origin.name}")
        ride = Ride(bike=bike, user=user, start_station=origin, start_time=at)
        user._start_ride(ride)
        self._rides.append(ride)
        return ride

    def return_bike(self, user: User, station: str | Station, at: datetime) -> Ride:
        ride = user.active_ride
        if ride is None:
            raise NoActiveRideError(f"{user.name} has no active ride")
        destination = self.get_station(station)
        if at < ride.start_time:
            raise ValueError("End time cannot be before start time")
        if destination.free_docks == 0:
            ride.record_failed_return()
            redirect = None
            if ride.return_failures >= Ride.REDIRECT_AFTER_FAILED_RETURNS:
                candidates = [item for item in self._stations if item.free_docks > 0]
                if candidates:
                    redirect = min(
                        candidates,
                        key=lambda item: (-item.free_docks, item.name),
                    ).name
            raise StationFullError(destination.name, redirect)
        destination.return_bike(ride.bike)
        ride.finish(destination, at)
        user._finish_ride(ride)
        ReceiptPrinter.print(ride)
        return ride

    def report(self) -> str:
        lines = [
            f"{station} | {station.free_docks} free docks"
            for station in sorted(
                self._stations, key=lambda item: (-item.free_docks, item.name)
            )
        ]
        report = "\n".join(lines)
        print(report)
        return report
