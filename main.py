from dotenv import load_dotenv
load_dotenv()
import os

import click
import uvicorn

from core.config import config

# 日志已在 core.logger 初始化，无需 basicConfig

@click.command()
@click.option(
    "--env",
    type=click.Choice(["local", "dev", "prod"], case_sensitive=False),
    default="local",
)
@click.option(
    "--debug",
    type=click.BOOL,
    is_flag=True,
    default=False,
)
def main(env: str, debug: bool):

    os.environ["ENV"] = env
    os.environ["DEBUG"] = str(debug)


    uvicorn.run(
        app="app.server:app",
        host=config.app.host,
        port=config.app.port,
        reload=True if config.app.env != "production" else False,
        workers=1,
    )


if __name__ == "__main__":
    main()
