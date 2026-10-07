from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


@dataclass
class SkillResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    files: Optional[List[str]] = None
    requires_approval: bool = False
    approval_data: Optional[Dict[str, Any]] = None


class BaseSkill(ABC):
    name: str = ""
    description: str = ""
    allowed_intents: List[str] = []
    input_schema: Dict[str, Any] = {}
    permission: str = "empleado"
    tools: List[str] = []
    validation: Dict[str, Any] = {}
    execution: str = ""
    presentation: str = ""

    def __init__(self, router):
        self.router = router
        self.db = router.db
        self.engine = router.engine
        self.config = router.config

    @abstractmethod
    async def execute(self, user_id: int, intent: str, args: Dict[str, Any]) -> SkillResult:
        pass

    def validate_input(self, intent: str, args: Dict[str, Any]) -> tuple[bool, str]:
        return True, ""

    def check_permission(self, user_id: int, intent: str) -> tuple[bool, str]:
        role = self.db.get_user_role(user_id)
        if role == "admin":
            return True, ""
        if self.permission == "empleado" and role in ["empleado", "lider", "rrhh"]:
            return True, ""
        if self.permission == "lider" and role in ["lider", "rrhh"]:
            return True, ""
        if self.permission == "rrhh" and role == "rrhh":
            return True, ""
        return False, "No tiene permisos para esta acción"

    async def log_action(self, user_id: int, action: str, entity: str, entity_id: int, payload: Dict):
        self.db.log_audit(user_id, action, entity, entity_id, payload)