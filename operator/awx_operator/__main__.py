"""Main entry point for AWX operator."""

import logging
import sys

import kopf

from awx_operator.handlers import awx_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the AWX operator."""
    logger.info("Starting AWX Operator")
    logger.info("Watching for AWX custom resources in all namespaces")

    # Run kopf operator
    # This will watch for AWX CRDs and call registered handlers
    kopf.run(
        clusterwide=True,
        liveness_endpoint="http://0.0.0.0:8080/healthz",
    )


if __name__ == "__main__":
    main()
