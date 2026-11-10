# Class discovery and CRC cards

## Nouns from the requirement

| Noun or phrase | Decision | Reason |
|---|---|---|
| Tashkent | Outside context | Describes where the network operates. |
| Network | Class | Coordinates stations, users' rides, returns, and redirects. |
| Station | Class | Has a name and docks, and handles bike take/return operations. |
| Dock | Class | Holds zero or one bike and controls parking and repair state. |
| Bike | Class | Has an identifier and status; its state changes through dock operations. |
| Rider / user | Merge into `User` | Two names for the person who starts and ends rides. |
| Ride | Class and event | Records the bike, rider, stations, times, failures, and calculates its fee. |
| Receipt printer | Supporting class | Formats and prints a completed ride. |
| Manager | Actor | Reads the station report; the manager is not stored by the application. |
| Docks, bike status, active ride, stations, times | Attributes | Values belonging to the classes above. |
| First 15 minutes, 5-minute interval, 500 sum, 20,000 sum | `Ride` constants | Inputs to the fee rule, defined once where the rule lives. |
| "Any station" | Clarification | Interpreted as any station registered with this network. |
| No free docks anywhere | Open question | Should the app keep waiting, notify a manager, or offer another recovery action? The current error has no redirect when every station is full. |

## CRC cards

| Class | Responsibilities | Collaborators |
|---|---|---|
| `Bike` | Keep its identifier and status; accept only valid status transitions. | `Dock` |
| `Dock` | Hold at most one bike; park and release it; keep a repair bike docked and unavailable. | `Bike`, `Station` |
| `Station` | Create its fixed docks; find an available bike or an empty dock; report its counts. | `Dock`, `Bike` |
| `User` | Keep the user's name and at most one active ride. | `Ride`, `BikeSharingNetwork` |
| `Ride` | Record the ride event; own elapsed-time validation, the fee rule, and failed-return count. | `Bike`, `User`, `Station` |
| `BikeSharingNetwork` | Validate take/return operations, keep the in-memory ride history, select a redirect, and provide the manager's report. | `Station`, `User`, `Ride`, `ReceiptPrinter` |

`ReceiptPrinter` is a supporting presentation service rather than a seventh core domain card: it renders one finished `Ride` and does not own ride state.

No card has more than four responsibilities. Fee constants and the failed-return counter stay on `Ride`, which owns the duration and failure data they depend on.

## Return-to-full-station walkthrough

1. `User` asks `BikeSharingNetwork` to return the active `Ride` to a `Station`.
2. `BikeSharingNetwork` checks the destination's free-dock count. If it is zero, it leaves the bike and ride untouched.
3. `Ride` increments its own failed-return counter. On the second failed attempt, `BikeSharingNetwork` finds the non-full station with the most free docks, breaking ties by name.
4. `Station` selects a free `Dock`; that `Dock` parks the `Bike`, which changes to `AVAILABLE`.
5. `Ride` records the end station and time, calculates its fee, `User` clears its active ride, and `ReceiptPrinter` prints the receipt.

The second-round check found no responsibility gap: `Ride` owns the counter because it stores it; `BikeSharingNetwork` owns redirect selection because it holds the set of stations. The app does not invent a redirect if every station is full; this is the open question above.
