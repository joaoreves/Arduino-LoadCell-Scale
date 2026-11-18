"""Send simulated Arduino weight readings through a virtual serial port."""

import argparse
import math
import sys
import time

import serial


BAUD_RATE = 115200


def finite_float(value):
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("must be a finite number")
    return number


def positive_float(value):
    number = finite_float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Write simulated Arduino weight readings to one side of a "
            "virtual COM-port pair."
        )
    )
    parser.add_argument(
        "port",
        help="COM port connected to the logger's virtual port (for example COM10)",
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=0.1,
        help="seconds between readings (default: 0.1)",
    )
    parser.add_argument(
        "--center",
        type=finite_float,
        default=10.0,
        help="center of the simulated weight in kg (default: 10.0)",
    )
    parser.add_argument(
        "--amplitude",
        type=finite_float,
        default=0.5,
        help="size of the simulated weight variation in kg (default: 0.5)",
    )
    parser.add_argument(
        "--period",
        type=positive_float,
        default=8.0,
        help="seconds per simulated weight cycle (default: 8.0)",
    )
    args = parser.parse_args(argv)

    started_at = time.monotonic()
    try:
        with serial.Serial(args.port, BAUD_RATE, timeout=1) as port:
            print(
                f"Sending simulated readings to {args.port} at {BAUD_RATE} baud. "
                "Press Ctrl+C to stop."
            )
            while True:
                elapsed = time.monotonic() - started_at
                value = args.center + args.amplitude * math.sin(
                    2 * math.pi * elapsed / args.period
                )
                line = f"{value:.2f}\r\n".encode("ascii")
                port.write(line)
                print(line.decode("ascii").strip())
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except (serial.SerialException, OSError) as exc:
        print(f"Serial error on {args.port}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
