from datetime import datetime, timedelta

import pytest

from bike_sharing import (
    Bike,
    BikeSharingNetwork,
    BikeStatus,
    Dock,
    DockOccupiedError,
    NoActiveRideError,
    NoBikeError,
    RideActiveError,
    Station,
    StationFullError,
    User,
)


BASE_TIME = datetime(2026, 11, 10, 10, 0)


def make_network() -> tuple[BikeSharingNetwork, Station, Station, Station]:
    chilonzor = Station("Chilonzor", 2)
    yunusobod = Station("Yunusobod", 2)
    full_station = Station("Full", 1)
    chilonzor.docks[0].park(Bike("CH-1"))
    yunusobod.docks[0].park(Bike("YU-1"))
    full_station.docks[0].park(Bike("FULL-1"))
    return BikeSharingNetwork([chilonzor, yunusobod, full_station]), chilonzor, yunusobod, full_station


def test_if_dock_is_free_bike_is_docked_and_available() -> None:
    dock = Dock(1)
    bike = Bike("B-1")

    dock.park(bike)

    assert dock.bike is bike
    assert bike.status is BikeStatus.AVAILABLE


def test_if_dock_is_occupied_second_bike_is_not_parked() -> None:
    dock = Dock(1)
    first = Bike("B-1")
    second = Bike("B-2")
    dock.park(first)

    with pytest.raises(DockOccupiedError):
        dock.park(second)

    assert dock.bike is first
    assert second.status is BikeStatus.AVAILABLE


def test_if_public_properties_are_written_they_are_read_only() -> None:
    station = Station("Chilonzor", 2)
    bike = Bike("B-1")
    dock = station.docks[0]
    dock.park(bike)

    with pytest.raises(AttributeError):
        dock.bike = None  # type: ignore[misc]
    with pytest.raises(AttributeError):
        bike.status = BikeStatus.REPAIR  # type: ignore[misc]
    with pytest.raises(AttributeError):
        station.docks.append(Dock(3))  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        station.docks = ()  # type: ignore[misc]


def test_if_two_stations_are_created_their_docks_are_independent() -> None:
    first = Station("First", 2)
    second = Station("Second", 2)

    first.docks[0].park(Bike("B-1"))

    assert first.docked_bikes == 1
    assert second.docked_bikes == 0
    assert first.docks[0] is not second.docks[0]


def test_if_bike_is_in_repair_it_stays_docked_and_cannot_be_taken() -> None:
    station = Station("Chilonzor", 1)
    dock = station.docks[0]
    bike = Bike("B-1")
    dock.park(bike)

    dock.send_to_repair()

    assert dock.bike is bike
    assert bike.status is BikeStatus.REPAIR
    assert station.take_bike() is None


def test_if_repair_is_completed_docked_bike_becomes_available_again() -> None:
    station = Station("Chilonzor", 1)
    dock = station.docks[0]
    bike = Bike("B-1")
    dock.park(bike)
    dock.send_to_repair()

    dock.return_from_repair()

    assert dock.bike is bike
    assert bike.status is BikeStatus.AVAILABLE
    assert station.take_bike() is bike


def test_if_station_is_printed_it_shows_docked_bikes_and_capacity() -> None:
    station = Station("Chilonzor", 2)
    station.docks[0].park(Bike("B-1"))

    assert str(station) == "Chilonzor: 1/2 bikes"
    assert len(station) == 1
    assert "Station(name='Chilonzor'" in repr(station)


@pytest.mark.parametrize(
    ("minutes", "expected_fee"),
    [(15, 0), (15 + 1 / 60, 500), (20, 500), (20 + 1 / 60, 1_000), (500, 20_000)],
)
def test_if_ride_is_finished_it_charges_the_started_five_minute_blocks(
    minutes: float, expected_fee: int
) -> None:
    network, chilonzor, yunusobod, _ = make_network()
    user = User("Ali")
    ride = network.take_bike(user, chilonzor, BASE_TIME)

    network.return_bike(user, yunusobod, BASE_TIME + timedelta(minutes=minutes))

    assert ride.fee == expected_fee
    assert ride.end_station is yunusobod
    assert ride.is_finished
    assert user.active_ride is None


def test_if_end_time_precedes_start_time_return_is_rejected_without_moving_bike() -> None:
    network, chilonzor, yunusobod, _ = make_network()
    user = User("Ali")
    ride = network.take_bike(user, chilonzor, BASE_TIME)

    with pytest.raises(ValueError, match="before start"):
        network.return_bike(user, yunusobod, BASE_TIME - timedelta(seconds=1))

    assert not ride.is_finished
    assert user.active_ride is ride
    assert yunusobod.free_docks == 1


def test_if_end_time_precedes_start_time_full_station_does_not_count_failure() -> None:
    network, chilonzor, _, full_station = make_network()
    user = User("Ali")
    ride = network.take_bike(user, chilonzor, BASE_TIME)

    with pytest.raises(ValueError, match="before start"):
        network.return_bike(user, full_station, BASE_TIME - timedelta(seconds=1))

    assert ride.return_failures == 0
    assert user.active_ride is ride


def test_if_receipt_is_printed_it_contains_stations_duration_and_fee(capsys: pytest.CaptureFixture[str]) -> None:
    network, chilonzor, yunusobod, _ = make_network()
    user = User("Ali")

    network.take_bike(user, chilonzor, BASE_TIME)
    network.return_bike(user, yunusobod, BASE_TIME + timedelta(minutes=23))

    assert capsys.readouterr().out.strip() == "Chilonzor → Yunusobod, 23 min, 1 000 sum"


def test_if_user_takes_bike_then_the_ride_starts_and_bike_is_in_use() -> None:
    network, chilonzor, _, _ = make_network()
    user = User("Ali")

    ride = network.take_bike(user, chilonzor, BASE_TIME)

    assert ride.start_station is chilonzor
    assert ride.start_time == BASE_TIME
    assert user.active_ride is ride
    assert ride.bike.status is BikeStatus.IN_USE
    assert network.rides == (ride,)


def test_if_user_already_has_ride_a_second_take_is_rejected() -> None:
    network, chilonzor, _, _ = make_network()
    user = User("Ali")
    network.take_bike(user, chilonzor, BASE_TIME)

    with pytest.raises(RideActiveError):
        network.take_bike(user, chilonzor, BASE_TIME)


def test_if_station_has_no_available_bike_take_is_rejected() -> None:
    network, _, _, full_station = make_network()
    full_station.docks[0].send_to_repair()

    with pytest.raises(NoBikeError):
        network.take_bike(User("Ali"), full_station, BASE_TIME)


def test_if_user_has_no_ride_return_is_rejected() -> None:
    network, _, yunusobod, _ = make_network()

    with pytest.raises(NoActiveRideError):
        network.return_bike(User("Ali"), yunusobod, BASE_TIME)


def test_if_station_is_full_first_return_failure_keeps_ride_active() -> None:
    network, chilonzor, _, full_station = make_network()
    user = User("Ali")
    ride = network.take_bike(user, chilonzor, BASE_TIME)

    with pytest.raises(StationFullError) as error:
        network.return_bike(user, full_station, BASE_TIME + timedelta(minutes=1))

    assert error.value.redirect_station is None
    assert ride.return_failures == 1
    assert not ride.is_finished
    assert user.active_ride is ride
    assert ride.bike.status is BikeStatus.IN_USE


def test_if_same_ride_fails_twice_redirect_uses_most_free_docks_then_name() -> None:
    network, chilonzor, yunusobod, full_station = make_network()
    user = User("Ali")
    ride = network.take_bike(user, chilonzor, BASE_TIME)
    yunusobod.docks[1].park(Bike("YU-2"))

    for _ in range(2):
        with pytest.raises(StationFullError) as error:
            network.return_bike(user, full_station, BASE_TIME + timedelta(minutes=1))

    assert error.value.redirect_station == "Chilonzor"
    assert ride.return_failures == 2


def test_if_redirect_candidates_have_equal_free_docks_name_a_to_z_wins() -> None:
    alpha = Station("Alpha", 2)
    beta = Station("Beta", 2)
    origin = Station("Origin", 2)
    full_station = Station("Full", 1)
    origin.docks[0].park(Bike("OR-1"))
    full_station.docks[0].park(Bike("FULL-1"))
    network = BikeSharingNetwork([beta, origin, full_station, alpha])
    user = User("Ali")
    network.take_bike(user, origin, BASE_TIME)

    for _ in range(2):
        with pytest.raises(StationFullError) as error:
            network.return_bike(user, full_station, BASE_TIME + timedelta(minutes=1))

    assert error.value.redirect_station == "Alpha"


def test_if_user_returns_to_redirected_station_ride_closes_and_prints_receipt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    network, chilonzor, _, full_station = make_network()
    user = User("Ali")
    ride = network.take_bike(user, chilonzor, BASE_TIME)
    for _ in range(2):
        with pytest.raises(StationFullError):
            network.return_bike(user, full_station, BASE_TIME + timedelta(minutes=23))

    network.return_bike(user, chilonzor, BASE_TIME + timedelta(minutes=23))

    assert ride.is_finished
    assert ride.end_station is chilonzor
    assert user.active_ride is None
    assert ride.bike.status is BikeStatus.AVAILABLE
    assert "Chilonzor → Chilonzor, 23 min, 1 000 sum" in capsys.readouterr().out


def test_if_ride_is_completed_network_keeps_its_start_end_stations_and_times(
    capsys: pytest.CaptureFixture[str],
) -> None:
    network, chilonzor, yunusobod, _ = make_network()
    user = User("Ali")
    start = BASE_TIME
    end = BASE_TIME + timedelta(minutes=23)
    ride = network.take_bike(user, chilonzor, start)

    network.return_bike(user, yunusobod, end)

    assert network.rides == (ride,)
    assert ride.start_station is chilonzor
    assert ride.end_station is yunusobod
    assert ride.start_time == start
    assert ride.end_time == end
    capsys.readouterr()


def test_if_network_report_is_requested_stations_are_ordered_by_free_docks(
    capsys: pytest.CaptureFixture[str],
) -> None:
    network, _, _, _ = make_network()

    report = network.report()

    assert report.splitlines() == [
        "Chilonzor: 1/2 bikes | 1 free docks",
        "Yunusobod: 1/2 bikes | 1 free docks",
        "Full: 1/1 bikes | 0 free docks",
    ]
    assert capsys.readouterr().out.strip() == report


def test_if_bike_is_parked_it_cannot_be_placed_in_two_docks() -> None:
    first = Dock(1)
    second = Dock(2)
    bike = Bike("B-1")
    first.park(bike)

    with pytest.raises(ValueError, match="already in a dock"):
        second.park(bike)

    assert first.bike is bike
    assert second.is_free


def test_if_two_networks_are_created_station_collections_are_not_shared() -> None:
    first = Station("First", 1)
    second = Station("Second", 1)
    network_one = BikeSharingNetwork([first])
    network_two = BikeSharingNetwork([second])

    assert network_one.stations == (first,)
    assert network_two.stations == (second,)


def test_if_stations_are_sorted_they_are_ordered_by_free_docks() -> None:
    busy = Station("Busy", 2)
    open_station = Station("Open", 2)
    busy.docks[0].park(Bike("B-1"))

    assert sorted([open_station, busy]) == [busy, open_station]
