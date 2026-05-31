from abc import ABC

from pydantic import BaseModel, ConfigDict, Field

class BaseAgent(BaseModel, ABC):
     """Base class for all agents in the system.  It defines the common interface and shared functionality that all agents must implement."""

     model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

     agent_name: str = Field(description="The name of the agent")
     description: str = Field(description="A brief description of the agent's purpose and capabilities")
     content_types: list[str] = Field(description="Supported Content Types for the agent responses")