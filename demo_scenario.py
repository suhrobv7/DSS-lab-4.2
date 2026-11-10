from datetime import datetime, timedelta

from bike_sharing import Bike, BikeSharingNetwork, Station, StationFullError, User


def main() -> None:
    chilonzor = Station("Chilonzor", 2)
    yunusobod = Station("Yunusobod", 2)
    chilonzor.docks[0].park(Bike("CH-001"))
    yunusobod.docks[0].park(Bike("YU-001"))
    yunusobod.docks[1].park(Bike("YU-002"))
    network = BikeSharingNetwork([chilonzor, yunusobod])
    user = User("Ali")
    start = datetime(2026, 11, 10, 10, 0)
    finish = start + timedelta(minutes=23)

    ride = network.take_bike(user, chilonzor, start)
    print(f"{user.name} took {ride.bike.bike_id} from {chilonzor.name}")
    for attempt in range(1, 3):
        try:
            network.return_bike(user, yunusobod, finish)
        except StationFullError as error:
            print(f"Return attempt {attempt}: {error}")
    network.return_bike(user, chilonzor, finish)


if __name__ == "__main__":
    main()
