import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

load_dotenv()
import asyncio
import subprocess
import uuid
import logging

import aiofiles

logger = logging.getLogger(__name__)


class BlogPostArgs(BaseModel):
     blog_content: str = Field(..., description="The content of the blog post.")
     title: str = Field(..., description="The title of the blog post.")
     research_project_id: Optional[str] = Field(default=None, description="The ID of the research project associated with the blog post, if applicable.")

class PublishBlogPostArgs(BlogPostArgs):
     port: int = Field(..., description="The port number to use for the Docker container hosting the blog post.")
     blog_name: str = Field(default="default", description="The name of the blog, used for naming the Docker container and environment file.")

class BlogNameArg(BaseModel):
     blog_name: str = Field(..., description="The name of the blog, used for identifying the Docker container and environment file to manage.")

class ClearBlogPreviewArgs(BaseModel):
     research_project_id: Optional[str] = Field(default=None, description="The ID of the research project for which to clear the blog post preview, if applicable.")

class BlogWriterTools:
     def __init__(self):
          self.blog_post_preview_file_path = os.getenv("BLOG_POST_PREVIEW_FILE_PATH", "blog_preview.html")
          self.blog_preview_tool = StructuredTool.from_function(
               coroutine=self.write_blog_post_preview,
               name="Blog Writer Tool",
               description="Writes blog content to a preview format in html, so it can be viewed before publishing to docker.",
               args_schema=BlogPostArgs,
               response_format="content",
          )
          self.clear_blog_preview_tool = StructuredTool.from_function(
               coroutine=self.clear_blog_post_preview,
               name="Clear Blog Preview Tool",
               description="Clears the blog post preview content.",
               args_schema=ClearBlogPreviewArgs,
               response_format="content",
          )
          self.publish_blog_post_tool = StructuredTool.from_function(
               coroutine=self.publish_blog_post,
               name="Publish Blog Post Tool",
               description="Publishes blog post by docker and return URL.",
               args_schema=PublishBlogPostArgs,
               response_format="content",
          )
          self.start_all_docker_containers_tool = StructuredTool.from_function(
               func=self._start_all_docker_containers,
               name="Start All Docker Containers Tool",
               description="Starts all Docker containers for published blog posts.",
               args_schema=None,
               response_format="content",
          )
          self.start_docker_container_tool = StructuredTool.from_function(
               func=self._start_docker_container_sync,
               name="Start Docker Container Tool",
               description="Starts a Docker container for a published blog post by blog_name.",
               args_schema=BlogNameArg,
               response_format="content",
          )
          self.restart_docker_container_tool = StructuredTool.from_function(
               func=self._restart_docker_container,
               name="Restart Docker Container Tool",
               description="Restarts a Docker container for published blog posts by blog_name.",
               args_schema=BlogNameArg,
               response_format="content",
          )
          self.stop_docker_container_tool = StructuredTool.from_function(
               func=self._stop_docker_container,
               name="Stop Docker Container Tool",
               description="Stops a Docker container for published blog posts by blog_name.",
               args_schema=BlogNameArg,
               response_format="content",
          )


     async def write_blog_post_preview(self, blog_content: str, title: str, research_project_id: Optional[str] = None) -> dict:
          """Writes blog post to html for preview."""
          # Ensure the preview directory exists
          os.makedirs(os.path.dirname(self.blog_post_preview_file_path), exist_ok=True)

          # Build a full HTML page with basic styling so the preview looks like a real blog post
          html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.7; color: #333; }}
  h1 {{ font-size: 2em; margin-bottom: 0.5em; color: #1a1a1a; }}
  .meta {{ color: #888; font-size: 0.9em; margin-bottom: 2em; }}
  p {{ margin-bottom: 1.2em; }}
  img {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">Research Project: {research_project_id or 'N/A'}</div>
{blog_content}
</body>
</html>"""

          async with aiofiles.open(self.blog_post_preview_file_path, 'w') as f:
               await f.write(html)

          return {
               "title": f"Research Project: {research_project_id} - {title}",
               "preview_url": f"/blog_preview/output.html",
               "content": html
          }


     async def clear_blog_post_preview(self, research_project_id: Optional[str] = None) -> dict:
          """Clears the blog post preview content."""
          placeholder = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>No preview</title></head>
<body><p>No blog post preview available. Generate one first.</p></body>
</html>"""
          async with aiofiles.open(self.blog_post_preview_file_path, 'w') as f:
               await f.write(placeholder)

          return {
               "message": f"Blog post preview cleared for research project {research_project_id}."
          }


     def _create_blog_post_output_folder(self, research_project_id: str, blog_name: str) -> str:
          """Creates an output folder for the blog post content based on the research project ID and blog name."""
          fold_seed = uuid.uuid4().hex[:6]
          blog_output_dir = os.getenv("BLOG_POST_OUTPUT_DIR", "blog_output")
          output_folder = os.path.join(
               blog_output_dir,
               f"blog_{blog_name}_{fold_seed}"
          )
          os.makedirs(output_folder, exist_ok=True)
          return output_folder


     def _create_env_file_for_docker(self, output_folder: str, port: int, blog_name: str,
                                      research_project_id: str, title: str) -> str:
          """Creates an .env file in the blog_envs folder so a blog container can be restarted later."""
          blog_envs_dir = os.getenv("BLOG_ENVs_FOLDER", "blog_envs")
          os.makedirs(blog_envs_dir, exist_ok=True)
          env_file_path = os.path.join(blog_envs_dir, f".env.{blog_name}")
          with open(env_file_path, 'w') as f:
               f.write(f"BLOG_PORT={port}\n")
               f.write(f"BLOG_NAME={blog_name}\n")
               f.write(f"BLOG_TITLE={title}\n")
               f.write(f"RESEARCH_PROJECT_ID={research_project_id}\n")
               f.write(f"OUTPUT_FOLDER={output_folder}\n")
          return env_file_path


     # ── Docker container management (synchronous — called via StructuredTool func=) ──

     def _start_docker_container_sync(self, blog_name: str):
          """Start a single blog's nginx container by reading its .env file."""
          blog_envs_dir = os.getenv("BLOG_ENVs_FOLDER", "blog_envs")
          env_file = os.path.join(blog_envs_dir, f".env.{blog_name}")
          if not os.path.exists(env_file):
               return {"error": f"No .env file found for blog '{blog_name}' — publish it first."}

          # Load the saved env vars
          env_vars = {}
          with open(env_file) as f:
               for line in f:
                    if '=' in line:
                         k, v = line.strip().split('=', 1)
                         env_vars[k] = v

          port = env_vars.get("BLOG_PORT", "80")
          output_folder = env_vars.get("OUTPUT_FOLDER", "")
          if not os.path.isdir(output_folder):
               return {"error": f"Blog output folder not found: {output_folder}"}

          # Stop and remove any existing container with this name first
          self._stop_docker_container(blog_name)

          # Run nginx:alpine, mounting only THIS blog's folder, on ITS port
          result = subprocess.run(
               [
                    "docker", "run", "-d",
                    "--name", blog_name,
                    "-p", f"{port}:80",
                    "-v", f"{os.path.abspath(output_folder)}:/usr/share/nginx/html:ro",
                    "--restart", "unless-stopped",
                    "nginx:alpine",
               ],
               capture_output=True, text=True,
          )
          container_id = result.stdout.strip()
          if result.returncode != 0:
               logger.error("docker run failed for blog '%s': %s", blog_name, result.stderr)
               return {"error": f"Docker failed: {result.stderr.strip()}"}

          url = f"http://localhost:{port}"
          logger.info("Blog '%s' started at %s (container %s)", blog_name, url, container_id[:12])
          return {
               "container_id": container_id,
               "blog_name": blog_name,
               "url": url,
               "port": port,
               "status": "running",
          }


     def _restart_docker_container(self, blog_name: str):
          self._stop_docker_container(blog_name=blog_name)
          return self._start_docker_container_sync(blog_name=blog_name)


     def _stop_docker_container(self, blog_name: str):
          """Stop and remove a blog container by name."""
          subprocess.run(["docker", "stop", blog_name], capture_output=True)
          subprocess.run(["docker", "rm", blog_name], capture_output=True)
          return {"status": "stopped", "blog_name": blog_name}


     def _start_all_docker_containers(self):
          """Start containers for every .env.* file in the blog_envs folder."""
          results = []
          blog_envs_dir = os.getenv("BLOG_ENVs_FOLDER", "blog_envs")
          if not os.path.isdir(blog_envs_dir):
               return {"message": "No blog environment files found."}
          for env_file in sorted(os.listdir(blog_envs_dir)):
               if env_file.startswith(".env."):
                    blog_name = env_file.split(".env.", 1)[1]
                    results.append(self._start_docker_container_sync(blog_name))
          return {"started": results}


     # ── Publish ────────────────────────────────────────────────────────────────

     async def publish_blog_post(self, blog_content: str, title: str,
                              research_project_id: Optional[str] = None,
                              port: int = None, blog_name: str = "default") -> dict:
          """Writes the blog to disk and launches a dedicated nginx container.

          This is called from an async context (MCP tool handler).  All real
          work is synchronous (file I/O + subprocess); we offload it to
          ``asyncio.to_thread`` so nothing blocks the event loop.
          """
          # Ensure we have a research_project_id
          if not research_project_id:
               research_project_id = str(uuid.uuid4())

          # Default port: pick one based on hash of the blog name to reduce collisions,
          # but let the caller override explicitly.
          if port is None:
               port = 8080 + (abs(hash(blog_name)) % 500)

          def _do_publish() -> dict:
               output_folder = self._create_blog_post_output_folder(research_project_id, blog_name)
               output_file = os.path.join(output_folder, "index.html")

               # Build a self-contained HTML page
               html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.7; color: #333; }}
  h1 {{ font-size: 2em; margin-bottom: 0.5em; color: #1a1a1a; }}
  .meta {{ color: #888; font-size: 0.9em; margin-bottom: 2em; }}
  p {{ margin-bottom: 1.2em; }}
  img {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">Research Project: {research_project_id}</div>
{blog_content}
</body>
</html>"""

               with open(output_file, 'w') as f:
                    f.write(html)

               # Persist env file so the container can be restarted later
               self._create_env_file_for_docker(
                    output_folder=output_folder,
                    port=port,
                    blog_name=blog_name,
                    research_project_id=research_project_id,
                    title=title,
               )

               # Start the nginx container (blocking subprocess — fine on a thread)
               start_result = self._start_docker_container_sync(blog_name)
               if "error" in start_result:
                    return {
                         "error": start_result["error"],
                         "output_folder": output_folder,
                         "title": title,
                    }

               return {
                    "title": title,
                    "research_project_id": research_project_id,
                    "blog_name": blog_name,
                    "port": port,
                    "url": start_result.get("url", f"http://localhost:{port}"),
                    "output_folder": output_folder,
                    "container_id": start_result.get("container_id", ""),
               }

          return await asyncio.to_thread(_do_publish)
