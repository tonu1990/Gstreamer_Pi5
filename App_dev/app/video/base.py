from abc import ABC, abstractmethod
from typing import Optional, Tuple

class VideoBackend(ABC):
    """Abstract interface for platform-specific video capture/recording."""

    @abstractmethod
    def start_preview(self, resolution: Tuple[int, int], fps: int) -> None:
        ...

    @abstractmethod
    def start_recording(self, output_path: str) -> None:
        ...

    @abstractmethod
    def stop_recording(self) -> None:
        ...

    @abstractmethod
    def stop_all(self) -> None:
        ...
