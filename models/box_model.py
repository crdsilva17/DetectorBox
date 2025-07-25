
from abc import ABC, abstractmethod


class BoxType(ABC):
    def __init__(self, layout: tuple=(4, 3)):
        self.layout = layout
    
    @abstractmethod
    def set_layout(self, layout: tuple):
        pass

    