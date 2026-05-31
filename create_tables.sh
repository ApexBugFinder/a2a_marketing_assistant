poetry run python -c "
import asyncio
from dotenv import load_dotenv
load_dotenv()
from tools.postgres_tools import PostgresTools

async def main():
    tools = PostgresTools()
    result = await tools.create_tables()
    print(result)

asyncio.run(main())
" 2>&1