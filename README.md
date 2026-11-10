# Tashkent Bike Sharing

A small in-memory console app for taking and returning bikes between stations. It uses Python 3.10+ and has no database, file storage, or background workers.

## Run

```bash
python main.py
```

The sample network contains `Chilonzor` and `Yunusobod`; sample users are `Ali` and `Malika`.

Commands:

```text
take Ali Chilonzor
return Ali Yunusobod
report
help
quit
```

The application clock is supplied by the console boundary. Domain operations accept their time as an argument so tests can cover exact fee boundaries deterministically.

## Tests

Install the test extra, then run the requested command:

```bash
python -m pip install pytest
pytest -v
```

Each test name starts with `test_if_` and describes the requirement it verifies. The suite covers the free period and billing boundaries, occupied and repair docks, read-only properties, active-ride errors, full-station retry and redirect, recovery, receipts, and reporting.

## Demo walkthrough

The repeatable terminal scenario is:

```bash
python demo_scenario.py
```

It takes a bike at Chilonzor, attempts to return it to a full Yunusobod twice, shows the redirect to the station with the most free docks, then returns the bike there and prints the 23-minute receipt. Record this run as a video of no more than 40 seconds and upload it to the private submission repository.

<details>
<summary>Demo video (expand; maximum 40 seconds)</summary>

The recording still needs to be captured and uploaded to the private submission repository. Use `python demo_scenario.py` and show these steps:

1. Ali takes a bike from Chilonzor.
2. Ali attempts to return it to full Yunusobod; show the first failed attempt.
3. Repeat the return; show the redirect to Chilonzor after failure number two.
4. Return the bike to Chilonzor and show the 23-minute, 1 000 sum receipt.

Video link: _Add the uploaded demo video URL here._

</details>

## Relationships

| Pair | Relationship | Multiplicity | Evidence |
|---|---|---|---|
| `Station` – `Dock` | Composition | One station has 1..* docks; each station-owned dock belongs to one station. | [`Station.__init__`](bike_sharing/models.py#L100) |
| `Bike` – `Dock` | Association | A bike has 0..1 dock link; a dock has 0..1 bike link. | [`Bike.__init__`](bike_sharing/models.py#L17) and [`Dock.park`](bike_sharing/models.py#L65) |
| `BikeSharingNetwork` – `Station` | Aggregation | A network has 1..* stations; a station can exist without a network. | [`BikeSharingNetwork.__init__`](bike_sharing/network.py#L15) |
| `BikeSharingNetwork` – `User` | Dependency | A network operation receives one user; the network retains no users. | [`BikeSharingNetwork.take_bike`](bike_sharing/network.py#L45) |
| `User` – `Ride` | Association | A user has 0..1 active ride; each ride has exactly one user. | [`User.active_ride`](bike_sharing/models.py#L168) |
| `Ride` – `Bike` | Association | Each ride records exactly one bike; a bike can be used by many rides over time. | [`Ride.bike`](bike_sharing/models.py#L191) |
| `Ride` – `Station` | Association | Each ride has one start station and zero or one end station while active; stations participate in many rides. | [`Ride.start_station`](bike_sharing/models.py#L193) |
| `BikeSharingNetwork` – `Ride` | Association | A network keeps 0..* ride records; each ride is created and recorded by one network. | [`BikeSharingNetwork.rides`](bike_sharing/network.py#L30) |
| `BikeSharingNetwork` – `ReceiptPrinter` | Dependency | The network invokes the printer only after a successful return. | [`BikeSharingNetwork.return_bike`](bike_sharing/network.py#L78) |
| `ReceiptPrinter` – `Ride` | Dependency | The printer receives a finished ride to render. | [`ReceiptPrinter.render`](bike_sharing/receipt.py#L6) |

### Lifetime checks

- **Station and its docks (composition):** a station creates its own docks. Releasing the station releases its dock tuple if no external references to those docks remain; Python references can keep an individual dock alive.
- **Dock and its bike (aggregation):** deleting a dock does not delete a bike created elsewhere; the bike is still usable and can be parked again.
- **Network and its stations (aggregation):** deleting a network does not delete its stations; callers can retain and reuse those station objects.

The network requires at least one station and unique station names. It keeps ride history in memory for the life of the app; no ride history is written to disk. A station's dock count is fixed and at least one; a dock can contain no more than one bike, and the bike's dock link prevents parking the same bike twice. A station may be used by more than one network; this is intentional because the network does not own its stations.

## Where a bike can be

```text
A bike is either docked at one station or in use on one active ride.
Dock.park rejects a bike that already has a dock link.
Taking a bike clears that link and changes its status to IN_USE.
Returning the bike assigns it to one free dock and changes its status to AVAILABLE.
A bike in REPAIR remains assigned to its dock, which will not release it.
```

The dock and bike properties, and a station's docks tuple, are read-only to callers. Bike movement and state changes go through `Dock`; the network uses those dock operations for rides.

## Design notes

Noun sorting, CRC cards, the full-station walkthrough, and the unresolved all-stations-full question are in [`docs/design.md`](docs/design.md).
