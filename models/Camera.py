from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')

class Camera(ABC, Generic[T]):

    def __init__(self, name: str, id: int, protocol: T):
        self.name = name
        self.id = id
        self.protocol = protocol
    
    @abstractmethod
    def capture(self):
        pass
