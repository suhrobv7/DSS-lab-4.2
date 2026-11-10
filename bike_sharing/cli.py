from datetime import datetime

from .errors import BikeSharingError
from .models import Bike, Station, User
from .network import BikeSharingNetwork


def build_demo_network() -> tuple[BikeSharingNetwork, dict[str, User]]:
    chilonzor = Station("Chilonzor", 4)
    yunusobod = Station("Yunusobod", 4)
    chilonzor.docks[0].park(Bike("CH-001"))
    chilonzor.docks[1].park(Bike("CH-002"))
    yunusobod.docks[0].park(Bike("YU-001"))
    return BikeSharingNetwork([chilonzor, yunusobod]), {
        "ali": User("Ali"),
        "malika": User("Malika"),
    }


def run() -> None:
    network, users = build_demo_network()
    print("Bike sharing console")
    print("Commands: take USER STATION | return USER STATION | report | help | quit")
    print("Users: Ali, Malika")
    while True:
        try:
            command = input("> ").strip().split()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not command:
            continue
        action = command[0].lower()
        if action in {"quit", "exit"}:
            return
        if action == "help":
            print("take USER STATION, return USER STATION, report, quit")
            continue
        if action == "report":
            network.report()
            continue
        if action not in {"take", "return"} or len(command) != 3:
            print("Use: take USER STATION or return USER STATION")
            continue
        user = users.get(command[1].lower())
        if user is None:
            print(f"Unknown user: {command[1]}")
            continue
        try:
            if action == "take":
                ride = network.take_bike(user, command[2], datetime.now())
                print(f"{user.name} took {ride.bike.bike_id} from {ride.start_station.name}")
            else:
                network.return_bike(user, command[2], datetime.now())
        except (BikeSharingError, ValueError) as error:
            print(error)


if __name__ == "__main__":
    run()
