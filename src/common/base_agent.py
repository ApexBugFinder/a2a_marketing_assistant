from abc import ABC

from pydantic import BaseModel, Field

class BaseAgent(BaseModel, ABC):
     """Base class for all agents in the system.  It defines the common interface and shared functionality that all agents must implement."""

     agent_name: str = Field(description="The name of the agent")
     description: str = Field(description="A brief description of the agent's purpose and capabilities")

     content_types: list[str] = Field(description ="Supported Content Types for the agent responses")

     model_config: dict | None = Field(description="""Model configuration parameters for the agent,
                                        such as temperature, max tokens, etc.""",
                                        default = {
                                             "arbitrary_types_allowed": True,
                                             "extra": "allow"
                                             }
                                        )