import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def truncate_jsonl(file_path: Path, max_lines: int = 5000):
    """Keep only the last max_lines in a jsonl file."""
    if not file_path.exists():
        return

    try:
        # Read all lines
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) <= max_lines:
            return

        # Write back only the last N lines
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines[-max_lines:])
        
        logger.info(f"Truncated {file_path.name} to {max_lines} lines.")
    except Exception as e:
        logger.error(f"Failed to truncate {file_path}: {e}")

def rotate_logs():
    """Main entry point to cleanup all log files."""
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    if not logs_dir.exists():
        return

    # 1. crawl_log.jsonl: Keep last 1000 entries (it grows fast)
    truncate_jsonl(logs_dir / "crawl_log.jsonl", max_lines=1000)

    # 2. review_potential_disasters.jsonl: Keep 5000 entries
    truncate_jsonl(logs_dir / "review_potential_disasters.jsonl", max_lines=15000)

    # 3. sse_buffer.jsonl: Broadcaster already manages it, but let's ensure it's not massive
    truncate_jsonl(logs_dir / "sse_buffer.jsonl", max_lines=500)
