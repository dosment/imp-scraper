"""
Checkpoint manager for crash recovery and resume functionality.
Saves progress after each dealership to enable resuming interrupted runs.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .models import Checkpoint, CheckpointEntry
from .utils import get_logger


class CheckpointManager:
    """
    Manages checkpoints for crash recovery.
    Saves progress to .checkpoints/ directory.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.logger = get_logger()
        self.checkpoint_dir = Path('.checkpoints')
        self.checkpoint_dir.mkdir(exist_ok=True)

        # Generate or use provided session ID
        if session_id:
            self.session_id = session_id
        else:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.checkpoint_file = self.checkpoint_dir / f"session_{self.session_id}.json"

        # Initialize checkpoint
        self.checkpoint = Checkpoint(
            session_id=self.session_id,
            started=datetime.now()
        )

    def save(self):
        """Save current checkpoint to file."""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(
                    self.checkpoint.model_dump(mode='json'),
                    f,
                    indent=2,
                    default=str
                )
            self.logger.debug(f"Checkpoint saved: {self.checkpoint_file}")

        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {e}", exc_info=True)

    def load(self, session_id: str) -> bool:
        """
        Load checkpoint from a previous session.

        Args:
            session_id: Session ID to resume

        Returns:
            True if checkpoint loaded successfully
        """
        checkpoint_file = self.checkpoint_dir / f"session_{session_id}.json"

        if not checkpoint_file.exists():
            self.logger.warning(f"Checkpoint file not found: {checkpoint_file}")
            return False

        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.checkpoint = Checkpoint(**data)
            self.session_id = session_id
            self.checkpoint_file = checkpoint_file

            self.logger.info(f"Loaded checkpoint: {session_id}")
            self.logger.info(
                f"  Completed: {len(self.checkpoint.completed)}, "
                f"Failed: {len(self.checkpoint.failed)}, "
                f"Pending: {len(self.checkpoint.pending)}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error loading checkpoint: {e}", exc_info=True)
            return False

    def find_latest_checkpoint(self) -> Optional[str]:
        """
        Find the most recent checkpoint session ID.

        Returns:
            Session ID of latest checkpoint, or None if none found
        """
        checkpoint_files = list(self.checkpoint_dir.glob("session_*.json"))

        if not checkpoint_files:
            return None

        # Sort by modification time, most recent first
        latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

        # Extract session ID from filename
        session_id = latest_file.stem.replace('session_', '')

        return session_id

    def mark_completed(self, url: str, locations_found: int = 1):
        """Mark a dealership as successfully completed."""
        entry = CheckpointEntry(
            url=url,
            status="success",
            locations_found=locations_found,
            completed_at=datetime.now()
        )

        self.checkpoint.completed.append(entry)

        # Remove from pending if present
        if url in self.checkpoint.pending:
            self.checkpoint.pending.remove(url)

        self.save()

    def mark_failed(self, url: str, error: str):
        """Mark a dealership as failed."""
        entry = CheckpointEntry(
            url=url,
            status="failed",
            error=error,
            attempted_at=datetime.now()
        )

        self.checkpoint.failed.append(entry)

        # Remove from pending if present
        if url in self.checkpoint.pending:
            self.checkpoint.pending.remove(url)

        self.save()

    def add_pending(self, urls: List[str]):
        """Add URLs to pending list."""
        for url in urls:
            if url not in self.checkpoint.pending:
                # Check if already completed or failed
                completed_urls = {e.url for e in self.checkpoint.completed}
                failed_urls = {e.url for e in self.checkpoint.failed}

                if url not in completed_urls and url not in failed_urls:
                    self.checkpoint.pending.append(url)

        self.save()

    def get_pending_urls(self) -> List[str]:
        """Get list of pending URLs to process."""
        return self.checkpoint.pending.copy()

    def get_completed_urls(self) -> List[str]:
        """Get list of completed URLs."""
        return [e.url for e in self.checkpoint.completed]

    def get_failed_urls(self) -> List[str]:
        """Get list of failed URLs."""
        return [e.url for e in self.checkpoint.failed]

    def get_stats(self) -> dict:
        """Get checkpoint statistics."""
        return {
            'session_id': self.session_id,
            'started': self.checkpoint.started.isoformat(),
            'total': len(self.checkpoint.completed) + len(self.checkpoint.failed) + len(self.checkpoint.pending),
            'completed': len(self.checkpoint.completed),
            'failed': len(self.checkpoint.failed),
            'pending': len(self.checkpoint.pending),
            'success_rate': (
                len(self.checkpoint.completed) / max(1, len(self.checkpoint.completed) + len(self.checkpoint.failed))
                * 100
            )
        }

    def print_summary(self):
        """Print checkpoint summary to logger."""
        stats = self.get_stats()

        self.logger.info("Checkpoint Summary:")
        self.logger.info(f"  Session ID: {stats['session_id']}")
        self.logger.info(f"  Started: {stats['started']}")
        self.logger.info(f"  Total URLs: {stats['total']}")
        self.logger.info(f"  Completed: {stats['completed']}")
        self.logger.info(f"  Failed: {stats['failed']}")
        self.logger.info(f"  Pending: {stats['pending']}")
        self.logger.info(f"  Success Rate: {stats['success_rate']:.1f}%")

    def cleanup_old_checkpoints(self, keep_last_n: int = 10):
        """
        Clean up old checkpoint files, keeping only the most recent.

        Args:
            keep_last_n: Number of recent checkpoints to keep
        """
        checkpoint_files = sorted(
            self.checkpoint_dir.glob("session_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Keep only the most recent N checkpoints
        for checkpoint_file in checkpoint_files[keep_last_n:]:
            try:
                checkpoint_file.unlink()
                self.logger.debug(f"Deleted old checkpoint: {checkpoint_file}")
            except Exception as e:
                self.logger.warning(f"Error deleting checkpoint {checkpoint_file}: {e}")
