
import json
import logging
import sys


class _OtelDetachFilter(logging.Filter):
    """Suppress the 'Failed to detach context' ValueError spam from google-adk's
    OTel integration. These occur when async-generator cleanup runs in a different
    asyncio context than where the span token was created — a known OTel+asyncio
    limitation (https://github.com/open-telemetry/opentelemetry-python/issues/2606).
    The errors are non-fatal; suppressing them keeps logs actionable."""
    def filter(self, record: logging.LogRecord) -> bool:
        return 'Failed to detach context' not in record.getMessage()


logging.getLogger('opentelemetry').addFilter(_OtelDetachFilter())

from pathlib import Path

import click
import httpx
import uvicorn

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.rest_routes import create_rest_routes
from a2a.server.tasks import (
BasePushNotificationSender,
InMemoryPushNotificationConfigStore,
InMemoryTaskStore,
)
from a2a.types import AgentCard
from a2a.client.card_resolver import parse_agent_card
from common.instructions.aspectuator_agent_cot import ASPECTUATOR_AGENT_COT_INSTRUCTIONS
from common.instructions.deep_research_agent_cot import DEEP_RESEARCH_AGENT_COT_INSTRUCTIONS
from common.instructions.content_strategist_agent_cot import CONTENT_STRATEGIST_AGENT_COT_INSTRUCTIONS
from common.instructions.seo_blog_writer_agent_cot import SEO_BLOG_WRITER_AGENT_COT_INSTRUCTIONS
from common.instructions.linkedin_post_generator_agent_cot import LINKEDIN_POSTER_COT_INSTRUCTION
from common.instructions.marketing_assistant_agent_cot import MARKETING_ASSISTANT_AGENT_COT_INSTRUCTION
from common.instructions.image_generation_agent_cot import IMAGE_GENERATION_COT_INSTRUCTION
from common.instructions.whitepaper_writer_agent import WHITEPAPER_WRITER_AGENT_COT_INSTRUCTIONS
from common.agent_executor import GenericAgentExecutor
from agents.marketing_assistant_agent import MarketingAssistantAgent
from agents.planner_agent import PlannerAgent
from agents.orchestrator_agent import OrchestratorAgent


logger = logging.getLogger(__name__)


def get_agent(agent_card: AgentCard):
     """Get the agent, given an agent card."""
     try:
          match agent_card.name:
               case 'Orchestrator Agent':
                    return OrchestratorAgent()
               case 'Planner Agent':
                    return PlannerAgent()
               case 'Marketing Assistant Agent':
                    return MarketingAssistantAgent(
                         agent_name='MarketingAssistantAgent',
                         description='Provides marketing insights and recommendations based on research findings, and collaborates with the marketing team to ensure that the strategies proposed are actionable and aligned with the overall marketing goals, while also being adaptable and able to evolve based on new research insights and the ongoing market dynamics.',
                         instructions=MARKETING_ASSISTANT_AGENT_COT_INSTRUCTION,
                    )
               case 'Image Generation Agent':
                    return MarketingAssistantAgent(
                         agent_name='ImageGenerationAgent',
                         description='Generates images based on the research findings and content strategy, and collaborates with the marketing team to ensure that the images produced are of high quality, effectively communicate the key messages from the research findings, and are aligned with the overall content strategy, while also being adaptable and able to evolve based on new research insights and the ongoing research process, allowing for continuous improvement and optimization of the images created based on the research findings.',
                         instructions=IMAGE_GENERATION_COT_INSTRUCTION,
                    )
               case 'Deep Research Agent':
                    return MarketingAssistantAgent(
                         agent_name='DeepResearchAgent',
                         description='Conduct deep research on a given topic',
                         instructions=DEEP_RESEARCH_AGENT_COT_INSTRUCTIONS,
                    )
               case 'Aspectuator Agent':
                    return MarketingAssistantAgent(
                         agent_name='AspectuatorAgent',
                         description='Creates new queries based on key words and key aspects of the research topic',
                         instructions=ASPECTUATOR_AGENT_COT_INSTRUCTIONS,
                    )
               case 'Content Strategist Agent':
                    return MarketingAssistantAgent(
                         agent_name='ContentStrategistAgent',
                         description='Develops content strategies for marketing campaigns',
                         instructions=CONTENT_STRATEGIST_AGENT_COT_INSTRUCTIONS,
                    )
               case 'SEO Blog Writer Agent':
                    return MarketingAssistantAgent(
                         agent_name='SEOBlogWriterAgent',
                         description='Writes SEO-optimized blog posts based on the research findings and content strategy',
                         instructions=SEO_BLOG_WRITER_AGENT_COT_INSTRUCTIONS,
                    )
               case 'LinkedIn Post Generator Agent':
                    return MarketingAssistantAgent(
                         agent_name='LinkedInPostGeneratorAgent',
                         description='Generates LinkedIn posts based on the research findings and content strategy',
                         instructions=LINKEDIN_POSTER_COT_INSTRUCTION,
                    )
               case 'Whitepaper Writer Agent':
                    return MarketingAssistantAgent(
                         agent_name='WhitepaperWriterAgent',
                         description='Generates comprehensive, research-backed whitepapers based on research findings and content strategy',
                         instructions=WHITEPAPER_WRITER_AGENT_COT_INSTRUCTIONS,
                    )
               case _:
                    raise ValueError(f"Unknown agent card: '{agent_card.name}'")
     except Exception as e:
          raise e


def _resolve_agent_card_path(agent_card: str) -> Path:
     """Resolve agent card path — try as-is first, then relative to the project root."""
     p = Path(agent_card)
     if p.exists():
          return p
     # Walk up from this file (src/agents/__main__.py) to find the project root.
     project_root = Path(__file__).resolve().parents[2]
     fallback = project_root / agent_card
     if fallback.exists():
          return fallback
     raise FileNotFoundError(
          f"Agent card not found: '{agent_card}'. "
          f"Tried '{p.resolve()}' and '{fallback}'."
     )


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10101)
@click.option('--agent-card', 'agent_card')
def main(host, port, agent_card):
     """Starts an Agent server."""
     try:
          if not agent_card:
               raise ValueError('Agent card is required')
          with _resolve_agent_card_path(agent_card).open() as file:
               data = json.load(file)
          agent_card = parse_agent_card(data)

          client = httpx.AsyncClient()
          push_notification_config_store = InMemoryPushNotificationConfigStore()
          push_notification_sender = BasePushNotificationSender(
               client, config_store=push_notification_config_store
          )

          request_handler = DefaultRequestHandler(
               agent_executor=GenericAgentExecutor(agent=get_agent(agent_card)),
               task_store=InMemoryTaskStore(),
               agent_card=agent_card,
               push_config_store=push_notification_config_store,
               push_sender=push_notification_sender,
          )

          routes = create_agent_card_routes(agent_card=agent_card)
          routes += create_rest_routes(request_handler=request_handler)
          server = Starlette(
               routes=routes,
               middleware=[
                    Middleware(
                         CORSMiddleware,
                         allow_origins=['*'],
                         allow_methods=['*'],
                         allow_headers=['*'],
                    )
               ],
          )

          logger.info(f'Starting server on {host}:{port}')

          uvicorn.run(server, host=host, port=port)
     except FileNotFoundError:
          logger.error(f"Error: File '{agent_card}' not found.")
          sys.exit(1)
     except json.JSONDecodeError:
          logger.error(f"Error: File '{agent_card}' contains invalid JSON.")
          sys.exit(1)
     except Exception as e:
          logger.error(f'An error occurred during server startup: {e}')
          sys.exit(1)


if __name__ == '__main__':
     main()
