import argparse
import logging
import os
import sys
from enum import Enum, auto
from typing import Tuple

from yacl import setup_colored_stderr_logging

try:
    from yacl import setup_colored_exceptions

    has_setup_colored_exceptions = True
except ImportError:
    has_setup_colored_exceptions = False

from . import __version__
from .wrap import setup_signal_handling, wrap_radiotray_ng

logger = logging.getLogger(__name__)


class Verbosity(Enum):
    QUIET = auto()
    ERROR = auto()
    WARN = auto()
    VERBOSE = auto()
    DEBUG = auto()


def get_argumentparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="""
%(prog)s is a wrapper script for radiotray-ng to provide an MPRIS2 interface.
"""
    )
    parser.add_argument("-p", "--play", action="store_true", dest="play", help="start playback immediately")
    parser.add_argument(
        "-V", "--version", action="store_true", dest="print_version", help="print the version number and exit"
    )
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        dest="quiet",
        help='be quiet (default: "%(default)s")',
    )
    verbosity_group.add_argument(
        "--error",
        action="store_true",
        default=False,
        dest="error",
        help='print error messages (default: "%(default)s")',
    )
    verbosity_group.add_argument(
        "--warn",
        action="store_true",
        default=True,
        dest="warn",
        help='print warning and error messages (default: "%(default)s")',
    )
    verbosity_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        dest="verbose",
        help='be verbose (default: "%(default)s")',
    )
    verbosity_group.add_argument(
        "--debug",
        action="store_true",
        default=False,
        dest="debug",
        help='print debug messages (default: "%(default)s")',
    )
    return parser


def parse_arguments() -> argparse.Namespace:
    parser = get_argumentparser()
    args = parser.parse_args()
    if args.print_version:
        return args
    args.verbosity_level = (
        Verbosity.QUIET
        if args.quiet
        else (
            Verbosity.ERROR
            if args.error
            else Verbosity.VERBOSE if args.verbose else Verbosity.DEBUG if args.debug else Verbosity.WARN
        )
    )
    return args


def setup_stderr_logging(verbosity_level: Verbosity) -> None:
    if verbosity_level == Verbosity.QUIET:
        logging.getLogger().handlers = []
    elif verbosity_level == Verbosity.ERROR:
        logging.basicConfig(level=logging.ERROR)
    elif verbosity_level == Verbosity.WARN:
        logging.basicConfig(level=logging.WARNING)
    elif verbosity_level == Verbosity.VERBOSE:
        logging.basicConfig(level=logging.INFO)
    elif verbosity_level == Verbosity.DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        raise NotImplementedError('The verbosity level "{}" is not implemented'.format(verbosity_level))
    if not verbosity_level == Verbosity.QUIET:
        # Only log critical registration errors to not spam the log
        logging.getLogger("pydbus.registration").setLevel(logging.CRITICAL)
        setup_colored_stderr_logging(format_string="[%(levelname)s] %(message)s")


def main() -> None:
    expected_exceptions: Tuple[type, ...] = ()
    try:
        args = parse_arguments()
        if args.print_version:
            print("{}, version {}".format(os.path.basename(sys.argv[0]), __version__))
            sys.exit(0)
        if has_setup_colored_exceptions:
            setup_colored_exceptions(True)
        setup_stderr_logging(args.verbosity_level)
        setup_signal_handling()
        wrap_radiotray_ng(args.play)
    except Exception as e:
        logger.error(str(e))
        for i, exception_class in enumerate(expected_exceptions, start=3):
            if isinstance(e, exception_class):
                sys.exit(i)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    sys.exit(0)
