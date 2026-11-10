from .models import Ride


class ReceiptPrinter:
    @staticmethod
    def render(ride: Ride) -> str:
        if not ride.is_finished or ride.end_station is None:
            raise ValueError("Cannot print a receipt for an active ride")
        minutes = (ride.duration.seconds + 59) // 60 + ride.duration.days * 24 * 60
        fee = f"{ride.fee:,}".replace(",", " ")
        return (
            f"{ride.start_station.name} → {ride.end_station.name}, "
            f"{minutes} min, {fee} sum"
        )

    @staticmethod
    def print(ride: Ride) -> str:
        receipt = ReceiptPrinter.render(ride)
        print(receipt)
        return receipt
