import sys

from .design import banner
from .utils import arg_parser as parser
from .utils import logger


def main() -> None:

    print(banner.BANNER_FULL_SIZE)

    args = parser.parse_args()

    if args.debug:
        logger.header("Parsed Arguments")
        logger.info(f"Input: {args.input}")
        logger.info(f"Verbose: {args.verbose}")


if __name__ == "__main__":
    sys.exit(main())
