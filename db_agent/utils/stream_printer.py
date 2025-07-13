from abc import ABC, abstractmethod
from openai.types.chat import ChatCompletionChunk

class StreamPrinter(ABC):
    @abstractmethod
    async def print_chunk(self, chunk: ChatCompletionChunk):
        pass