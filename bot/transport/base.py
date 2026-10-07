from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


@dataclass
class IncomingMessage:
    user_id: int
    username: Optional[str]
    text: str
    chat_id: int
    message_id: int


@dataclass
class OutgoingMessage:
    chat_id: int
    text: str
    reply_markup: Optional[Any] = None
    parse_mode: str = "HTML"


@dataclass
class OutgoingFile:
    chat_id: int
    file_path: str
    caption: Optional[str] = None


@dataclass
class CallbackQuery:
    user_id: int
    data: str
    message_chat_id: int
    message_id: int


class TransportAdapter(ABC):
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send_message(self, msg: OutgoingMessage) -> None:
        pass

    @abstractmethod
    async def send_file(self, file: OutgoingFile) -> None:
        pass

    @abstractmethod
    async def answer_callback(self, callback_id: str, text: str, show_alert: bool = False) -> None:
        pass

    @abstractmethod
    def register_handlers(self, router) -> None:
        pass


class SkillSchema(BaseModel):
    name: str
    description: str
    allowed_intents: List[str]
    input_schema: Dict[str, Any]
    permission: str
    tools: List[str]
    validation: Dict[str, Any]
    execution: str
    presentation: str