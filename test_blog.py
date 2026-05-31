import asyncio
from dotenv import load_dotenv
load_dotenv()
from tools.blog_writer_tools import BlogWriterTools

async def main():
    tools = BlogWriterTools()
    result = await tools.publish_blog_post(
        blog_content="<p>Test content</p>",
        title="Docker Test Blog",
        research_project_id="docker-test",
        port=8098,
        blog_name="docker_test"
    )
    print(result)

asyncio.run(main())
