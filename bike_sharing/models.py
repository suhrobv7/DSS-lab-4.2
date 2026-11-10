from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .errors import DockOccupiedError, StationFullError


class BikeStatus(Enum):
    AVAILABLE = "available"
    IN_USE = "in use"
    REPAIR = "repair"


class Bike:
    def __init__(self, bike_id: str) -> None:
        if not bike_id.strip():
            raise ValueError("bike_id cannot be empty")
        self._bike_id = bike_id
        self._status = BikeStatus.AVAILABLE
        self._dock: Dock | None = None

    @property
    def bike_id(self) -> str:
        return self._bike_id

    @property
    def status(self) -> BikeStatus:
        return self._status

    def _change_status(self, status: BikeStatus) -> None:
        allowed_transitions = {
            BikeStatus.AVAILABLE: {BikeStatus.IN_USE, BikeStatus.REPAIR},
            BikeStatus.IN_USE: {BikeStatus.AVAILABLE},
            BikeStatus.REPAIR: {BikeStatus.AVAILABLE},
        }
        if status is self._status:
            return
        if status not in allowed_transitions[self._status]:
            raise ValueError(f"Cannot change bike status from {self._status.name} to {status.name}")
        self._status = status

    def __repr__(self) -> str:
        return f"Bike(bike_id={self.bike_id!r}, status={self.status.name})"


class Dock:
    def __init__(self, dock_id: int) -> None:
        self._dock_id = dock_id
        self._bike: Bike | None = None

    @property
    def dock_id(self) -> int:
        return self._dock_id

    @property
    def bike(self) -> Bike | None:
        return self._bike

    @property
    def is_free(self) -> bool:
        return self._bike is None

    def park(self, bike: Bike) -> None:
        if not self.is_free:
            raise DockOccupiedError(f"Dock {self.dock_id} is occupied")
        if bike._dock is not None:
            raise ValueError(f"Bike {bike.bike_id} is already in a dock")
        if bike.status is BikeStatus.REPAIR:
            raise ValueError("A bike in repair cannot be moved to another dock")
        self._bike = bike
        bike._dock = self
        bike._change_status(BikeStatus.AVAILABLE)

    def take_bike(self) -> Bike | None:
        if self._bike is None or self._bike.status is not BikeStatus.AVAILABLE:
            return None
        bike = self._bike
        bike._change_status(BikeStatus.IN_USE)
        self._bike = None
        bike._dock = None
        return bike

    def send_to_repair(self) -> None:
        if self._bike is None or self._bike.status is not BikeStatus.AVAILABLE:
            raise ValueError("Only a docked, available bike can be sent to repair")
        self._bike._change_status(BikeStatus.REPAIR)

    def return_from_repair(self) -> None:
        if self._bike is None or self._bike.status is not BikeStatus.REPAIR:
            raise ValueError("This dock does not contain a bike in repair")
        self._bike._change_status(BikeStatus.AVAILABLE)

    def __repr__(self) -> str:
        return f"Dock(dock_id={self.dock_id}, bike={self.bike!r})"


class Station:
    def __init__(self, name: str, dock_count: int) -> None:
        if not name.strip():
            raise ValueError("Station name cannot be empty")
        if dock_count < 1:
            raise ValueError("A station must have at least one dock")
        self._name = name
        self._docks = tuple(Dock(index + 1) for index in range(dock_count))

    @property
    def name(self) -> str:
        return self._name

    @property
    def docks(self) -> tuple[Dock, ...]:
        return self._docks

    @property
    def free_docks(self) -> int:
        return sum(dock.is_free for dock in self._docks)

    @property
    def docked_bikes(self) -> int:
        return sum(dock.bike is not None for dock in self._docks)

    def take_bike(self) -> Bike | None:
        for dock in self._docks:
            bike = dock.take_bike()
            if bike is not None:
                return bike
        return None

    def return_bike(self, bike: Bike) -> None:
        for dock in self._docks:
            if dock.is_free:
                dock.park(bike)
                return
        raise StationFullError(self.name)

    def __len__(self) -> int:
        return self.docked_bikes

    def __str__(self) -> str:
        return f"{self.name}: {self.docked_bikes}/{len(self._docks)} bikes"

    def __repr__(self) -> str:
        return (
            f"Station(name={self.name!r}, docks={len(self._docks)}, "
            f"free_docks={self.free_docks})"
        )

    def __lt__(self, other: Station) -> bool:
        if not isinstance(other, Station):
            return NotImplemented
        return (self.free_docks, self.name) < (other.free_docks, other.name)


class User:
    def __init__(self, name: str) -> None:
        if not name.strip():
            raise ValueError("User name cannot be empty")
        self._name = name
        self._active_ride: Ride | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def active_ride(self) -> Ride | None:
        return self._active_ride

    def _start_ride(self, ride: Ride) -> None:
        self._active_ride = ride

    def _finish_ride(self, ride: Ride) -> None:
        if self._active_ride is not ride:
            raise ValueError("The ride does not belong to this user's active ride")
        self._active_ride = None

    def __repr__(self) -> str:
        return f"User(name={self.name!r})"


@dataclass
class Ride:
    FREE_MINUTES = 15
    BILLING_INTERVAL_MINUTES = 5
    PRICE_PER_INTERVAL = 500
    MAX_FEE = 20_000
    REDIRECT_AFTER_FAILED_RETURNS = 2

    bike: Bike
    user: User
    start_station: Station
    start_time: datetime
    _end_station: Station | None = field(default=None, init=False, repr=False)
    _end_time: datetime | None = field(default=None, init=False, repr=False)
    _return_failures: int = field(default=0, init=False, repr=False)

    @property
    def end_station(self) -> Station | None:
        return self._end_station

    @property
    def end_time(self) -> datetime | None:
        return self._end_time

    @property
    def return_failures(self) -> int:
        return self._return_failures

    @property
    def is_finished(self) -> bool:
        return self._end_time is not None

    @property
    def duration(self) -> timedelta:
        if self._end_time is None:
            raise ValueError("An active ride has no final duration")
        return self._end_time - self.start_time

    @property
    def fee(self) -> int:
        excess = self.duration - timedelta(minutes=self.FREE_MINUTES)
        if excess <= timedelta(0):
            return 0
        interval = timedelta(minutes=self.BILLING_INTERVAL_MINUTES)
        excess_microseconds = (
            excess.days * 86_400_000_000
            + excess.seconds * 1_000_000
            + excess.microseconds
        )
        interval_microseconds = self.BILLING_INTERVAL_MINUTES * 60 * 1_000_000
        intervals = (
            excess_microseconds + interval_microseconds - 1
        ) // interval_microseconds
        return min(intervals * self.PRICE_PER_INTERVAL, self.MAX_FEE)

    def record_failed_return(self) -> None:
        if self.is_finished:
            raise ValueError("A finished ride cannot be returned again")
        self._return_failures += 1

    def finish(self, station: Station, end_time: datetime) -> None:
        if self.is_finished:
            raise ValueError("Ride is already finished")
        if end_time < self.start_time:
            raise ValueError("End time cannot be before start time")
        self._end_station = station
        self._end_time = end_time
