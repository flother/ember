import argparse
import configparser
import pathlib
import sys

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
import uvicorn

from .tileset import TileNotFound, Tileset


async def tile(request):
    tileset_name = request.path_params["tileset"]
    z = request.path_params["z"]
    x = request.path_params["x"]
    y = request.path_params["y"]
    format = request.path_params["format"]

    if tileset_name not in app.state.tilesets:
        return PlainTextResponse(f"unknown tileset '{tileset_name}'", status_code=404)
    tileset = app.state.tilesets[tileset_name]
    if format != tileset.metadata.format:
        return PlainTextResponse(
            "Tiles in tileset '{}' are {} not {}".format(
                tileset_name,
                tileset.metadata.format,
                format,
            ),
            status_code=404,
        )

    try:
        tile_data = app.state.tilesets[tileset_name].get_tile(z, x, y)
    except TileNotFound:
        return PlainTextResponse(
            f"/{tileset_name}/{z}/{x}/{y}.{format} not found", status_code=404
        )

    return Response(content=tile_data, media_type=tileset.media_type())


app = Starlette(
    debug=True,
    routes=[
        Route("/{tileset}/{z:int}/{x:int}/{y:int}.{format}", tile, name="tile"),
    ],
)


def parse_config(path: pathlib.Path):
    config = configparser.ConfigParser()
    config.read(path)
    return config


def parse_tilesets(config):
    return {name: Tileset(filename) for name, filename in config.items("tilesets")}


def run():
    parser = argparse.ArgumentParser(
        description="Web server for map tiles stored in MBTiles files",
        epilog="<https://github.com/flother/ember>",
        allow_abbrev=False,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=pathlib.Path,
        default=pathlib.Path("tilesets.ini"),
        help="load tileset definitions from configuration file",
        metavar="FILE",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="bind server to this host",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="bind server to this port",
    )
    args = parser.parse_args()

    if not args.config.exists():
        sys.exit(f"{sys.argv[0]}: no file '{args.config}'")
    if args.config.is_dir():
        sys.exit(f"{sys.argv[0]}: '{args.config}' is a directory")

    config = parse_config(args.config)
    app.state.tilesets = parse_tilesets(config)

    uvicorn.run(app, host=args.host, port=args.port)
