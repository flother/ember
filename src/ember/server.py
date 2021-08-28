import argparse
import configparser
import sqlite3

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
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=argparse.FileType("r"))
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read_file(args.config)
    app.state.layers = dict(config["layers"])

    uvicorn.run(app, host="0.0.0.0", port=8000)
