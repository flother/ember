import argparse
import configparser
import pathlib
import sqlite3
import sys

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
import uvicorn


TILE_FORMATS = {
    "pbf": "application/x-protobuf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}


async def tile(request):
    layer = request.path_params["layer"]
    x = request.path_params["x"]
    y = request.path_params["y"]
    z = request.path_params["z"]
    format = request.path_params["format"]

    if layer not in app.state.layers:
        return PlainTextResponse(f"unknown layer '{layer}'", status_code=404)
    if format not in TILE_FORMATS:
        return PlainTextResponse(f"unknown format '{format}'", status_code=404)

    conn = sqlite3.connect(f"file:{app.state.layers[layer]}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tile_data FROM tiles WHERE zoom_level = ? and tile_column = ? and tile_row = ?",
        (z, x, y),
    )
    tile_data = cursor.fetchone()
    if tile_data is None:
        return PlainTextResponse(
            f"/{layer}/{z}/{x}/{y}.{format} not found", status_code=404
        )

    return Response(content=tile_data[0], media_type="image/png")


app = Starlette(
    debug=True,
    routes=[
        Route("/{layer}/{z:int}/{x:int}/{y:int}.{format}", tile, name="tile"),
    ],
)


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
        default=pathlib.Path("layers.ini"),
        help="load layer definitions from configuration file",
        metavar="FILE",
    )
    args = parser.parse_args()

    if not args.config.exists():
        sys.exit(f"{sys.argv[0]}: no file '{args.config}'")
    if args.config.is_dir():
        sys.exit(f"{sys.argv[0]}: '{args.config}' is a directory")

    config = configparser.ConfigParser()
    config.read(args.config)
    app.state.layers = dict(config["layers"])

    uvicorn.run(app, host="0.0.0.0", port=8000)
