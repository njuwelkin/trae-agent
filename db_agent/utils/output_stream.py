from abc import ABC, abstractmethod
from fastapi import WebSocket
from enum import Enum
from openai import AsyncOpenAI

class MessageType(str, Enum):
    TEXT = 'text'
    CHUNK = 'chunk'
    START = 'start'
    END = 'end'
    STATUS = 'status'

class OutputMessage(ABC):
    def __init__(self, type: MessageType, content: str):
        self.type = type
        self.content = content

    def to_dict(self):
        return {
            'type': self.type,
            'content': self.content
        }

class OutputStream(ABC):
    @abstractmethod
    async def send_message(self, output_message: OutputMessage) -> None:
        pass

    @abstractmethod
    async def send_text(self, text: str) -> None:
        pass

    @abstractmethod
    async def start_chunk(self) -> None:
        pass

    @abstractmethod
    async def end_chunk(self) -> None:
        pass

    @abstractmethod
    async def send_chunk(self) -> None:
        pass

    @abstractmethod
    async def update_status(self, content: str) -> None:
        pass

class WebSocketOutputStream(OutputStream):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send_message(self, output_message: OutputMessage) -> None:
        await self.websocket.send_json(output_message.to_dict())

    async def send_text(self, text: str) -> None:
        message = OutputMessage(MessageType.CHUNK, text)
        await self.websocket.send_json(message.to_dict())

    async def start_chunk(self) -> None:
        await self.websocket.send_json(OutputMessage(MessageType.START, "").to_dict())

    async def end_chunk(self) -> None:
        await self.websocket.send_json(OutputMessage(MessageType.END, "").to_dict())

    async def send_chunk(self, text: str) -> None:
        await self.websocket.send_json(OutputMessage(MessageType.START, "").to_dict())
        message = OutputMessage(MessageType.CHUNK, text)
        await self.websocket.send_json(message.to_dict())
        await self.websocket.send_json(OutputMessage(MessageType.END, "").to_dict())

    async def update_status(self, content: str) -> None:
        message = OutputMessage(MessageType.STATUS, content)
        await self.websocket.send_json(message.to_dict())