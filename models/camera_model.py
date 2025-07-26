from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')
R = TypeVar('R')

class Camera(ABC, Generic[R, T]):

    def __init__(self, name: str, id: int, capture_device: T):
        self.name = name
        self.id = id
        self.capture_device = capture_device
    
    @abstractmethod
    def capture(self) -> R:
        pass
