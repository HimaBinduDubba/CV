from typing import List, Optional, Dict

class QueueManager:
    def __init__(self):
        self.pending: List[str] = []
        self.in_progress: Optional[str] = None
        self.completed: List[str] = []
        self.failed: Dict[str, str] = {} # filepath -> error message
        self.total_files = 0

    def add_file(self, filepath: str) -> None:
        self.pending.append(filepath)
        self.total_files += 1

    def get_next(self) -> Optional[str]:
        if not self.pending:
            return None
        self.in_progress = self.pending.pop(0)
        return self.in_progress

    def mark_completed(self, filepath: str) -> None:
        if self.in_progress == filepath:
            self.in_progress = None
        self.completed.append(filepath)

    def mark_failed(self, filepath: str, error: str) -> None:
        if self.in_progress == filepath:
            self.in_progress = None
        self.failed[filepath] = error

    def get_progress(self) -> float:
        if self.total_files == 0:
            return 100.0
        processed = len(self.completed) + len(self.failed)
        return (processed / self.total_files) * 100.0
