"""
Config immutability hash utility for Sanad v2.
Computes SHA-256 hash of config directory for tamper detection.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

from loguru import logger

# Optional Prometheus metrics (graceful degradation if not available)
try:
    from prometheus_client import Gauge

    CONFIG_HASH_GAUGE = Gauge(
        "sanad_config_hash", "Config directory hash for immutability", ["hash"]
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning(
        "Prometheus metrics not available for config hash - install prometheus_client"
    )


def compute_config_hash(config_dir: str = "config") -> str:
    """
    Compute SHA-256 hash of all files in the config directory.

    Args:
        config_dir: Path to config directory (relative to project root)

    Returns:
        SHA-256 hash string of all config files

    Raises:
        FileNotFoundError: If config directory doesn't exist
        PermissionError: If config files can't be read
    """
    config_path = Path(config_dir)

    if not config_path.exists():
        raise FileNotFoundError(f"Config directory not found: {config_path}")

    if not config_path.is_dir():
        raise ValueError(f"Config path is not a directory: {config_path}")

    # Collect all config files in sorted order for consistent hashing
    config_files = []
    for file_path in sorted(config_path.rglob("*")):
        if file_path.is_file():
            config_files.append(file_path)

    if not config_files:
        logger.warning(f"No config files found in {config_path}")
        return hashlib.sha256(b"").hexdigest()

    # Compute combined hash of all config files
    hasher = hashlib.sha256()

    for file_path in config_files:
        try:
            # Add file path to hash for structure integrity
            hasher.update(str(file_path.relative_to(config_path)).encode("utf-8"))

            # Add file content to hash
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

        except (OSError, PermissionError) as e:
            logger.error(f"Failed to read config file {file_path}: {e}")
            raise

    config_hash = hasher.hexdigest()
    logger.info(f"CONFIG_HASH={config_hash}")

    # Export as Prometheus metric if available
    if METRICS_AVAILABLE:
        try:
            # Clear previous hash metrics
            CONFIG_HASH_GAUGE.clear()
            # Set new hash metric
            CONFIG_HASH_GAUGE.labels(hash=config_hash).set(1)
            logger.debug(f"Config hash exported to Prometheus: {config_hash}")
        except Exception as e:
            logger.warning(f"Failed to export config hash to Prometheus: {e}")

    return config_hash


def verify_config_integrity(expected_hash: Optional[str] = None) -> bool:
    """
    Verify config directory integrity against expected hash.

    Args:
        expected_hash: Expected SHA-256 hash to verify against

    Returns:
        True if hash matches or no expected hash provided, False otherwise
    """
    if not expected_hash:
        logger.info("No expected config hash provided - skipping verification")
        return True

    try:
        current_hash = compute_config_hash()
        if current_hash == expected_hash:
            logger.info("✅ Config integrity verified")
            return True
        else:
            logger.error(f"❌ Config integrity check failed!")
            logger.error(f"Expected: {expected_hash}")
            logger.error(f"Current:  {current_hash}")
            return False

    except Exception as e:
        logger.error(f"Config integrity verification failed: {e}")
        return False


def get_config_files_info(config_dir: str = "config") -> dict:
    """
    Get detailed information about config files for debugging.

    Args:
        config_dir: Path to config directory

    Returns:
        Dictionary with file paths, sizes, and modification times
    """
    config_path = Path(config_dir)
    files_info = {}

    if not config_path.exists():
        return files_info

    for file_path in sorted(config_path.rglob("*")):
        if file_path.is_file():
            try:
                stat = file_path.stat()
                files_info[str(file_path.relative_to(config_path))] = {
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "readable": os.access(file_path, os.R_OK),
                }
            except (OSError, PermissionError) as e:
                files_info[str(file_path.relative_to(config_path))] = {"error": str(e)}

    return files_info


if __name__ == "__main__":
    """
    CLI utility for computing config hash.
    Usage: python -m backend.core.config_hash
    """
    import sys

    try:
        config_dir = sys.argv[1] if len(sys.argv) > 1 else "config"
        hash_value = compute_config_hash(config_dir)
        print(f"CONFIG_HASH={hash_value}")

        # Print file details for debugging
        files_info = get_config_files_info(config_dir)
        print(f"\nConfig files ({len(files_info)}):")
        for file_path, info in files_info.items():
            if "error" in info:
                print(f"  {file_path}: ERROR - {info['error']}")
            else:
                print(
                    f"  {file_path}: {info['size']} bytes, readable={info['readable']}"
                )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
