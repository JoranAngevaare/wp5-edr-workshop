from __future__ import annotations

import logging
from typing import Annotated
import pydantic_core
from covjson_pydantic.coverage import CoverageCollection, Coverage, TiledNdArrayFloat
from covjson_pydantic.ndarray import TileSet, NdArrayFloat
from covjson_pydantic.domain import Domain, Axes, ValuesAxis, DomainType
from covjson_pydantic.parameter import Parameter, ObservedProperty, Unit

from edr_pydantic.parameter import EdrBaseModel
from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from geojson_pydantic import FeatureCollection
from starlette.responses import JSONResponse
import sys
from fastapi import HTTPException
from data import data
from .util import get_reference_system, split_raw_interval_into_start_end_datetime
import numpy as np


router = APIRouter(prefix="/collections/observations")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CoverageJsonResponse(JSONResponse):
    media_type = "application/prs.coverage+json"


class GeoJsonResponse(JSONResponse):
    media_type = "application/geo+json"


class EDRFeatureCollection(EdrBaseModel, FeatureCollection):
    parameters: dict[str, Parameter]


@router.get(
    "/locations",
    tags=["Collection data queries"],
    response_model=EDRFeatureCollection,
    response_model_exclude_none=True,
    response_class=GeoJsonResponse,
)
async def get_locations(
    bbox: Annotated[str | None, Query(example="5.0,52.0,6.0,52.1")] = None,
    # datetime: Annotated[str | None, Query(example="2024-02-22T01:00:00Z/2024-02-22T02:00:00Z")] = None,
    parameter_name: Annotated[
        str | None,
        Query(
            alias="parameter-name",
            description="Comma seperated list of parameter names. "
            "Return only locations that have one of these parameter.",
            example="ff, dd",
        ),
    ] = None,
) -> EDRFeatureCollection:
    pass


@router.get(
    "/locations/{location_id}",
    tags=["Collection data queries"],
    response_model=CoverageCollection,
    response_model_exclude_none=True,
    response_class=CoverageJsonResponse,
)
async def get_data_location_id(
    location_id: Annotated[str, Path(example="0-20000-0-06260")],
    parameter_name: Annotated[
        str | None,
        Query(
            alias="parameter-name",
            description="Comma separated list of parameter names.",
            example="ff, dd",
        ),
    ] = None,
    datetime: Annotated[
        str | None, Query(example="2024-02-22T01:00:00Z/2024-02-22T02:00:00Z")
    ] = None,
) -> CoverageCollection:

    if location_id not in [s.wsi for s in data.get_stations()]:
        raise HTTPException(
            status_code=400, detail=f"{location_id} is not in {data.get_stations()}"
        )
    station = data.get_station(location_id)
    variables = (
        data.get_variables_for_station(location_id)
        if parameter_name is None
        else [data.get_variable(x) for x in parameter_name.replace(" ", "").split(",")]
    )
    variables = [v for v in variables if v is not None]
    if not variables:
        raise HTTPException(
            status_code=400,
            detail=f"Only unknown parameters {parameter_name} for {location_id}",
        )
    variables_str = list(map(lambda x: x.id, variables))
    var_dict = dict(zip(variables_str, variables))
    if datetime is None:
        datetime = "1900-01-01T00:00:00Z/2100-02-22T02:00:00Z"
    try:
        time_start, time_end = split_raw_interval_into_start_end_datetime(datetime)
    except pydantic_core.ValidationError as e:
        raise HTTPException(
            status_code=400, detail=f"One or more invalid date values: {datetime}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"General exception parsing {datetime}"
        ) from e
    data_dict = {
        v: data.get_data_within_time(location_id, v, start=time_start, stop=time_end)
        for v in variables_str
    }
    if all(len(v) == 0 for v in data_dict.values()):
        raise HTTPException(
            status_code=400, detail="No data in range for any variable in time range"
        )

    coverages = []
    for var, data_for_var in data_dict.items():

        dates = [x[0] for x in data_for_var]
        values = [float(x[1]) for x in data_for_var]
        coverages += [
            Coverage(
                domain=Domain(
                    domainType=DomainType.point_series,
                    referencing=get_reference_system(),
                    axes=Axes(
                        x=ValuesAxis(values=[station.longitude]),
                        y=ValuesAxis(values=[station.latitude]),
                        z=ValuesAxis(values=[station.height]),
                        t=ValuesAxis(values=dates),
                    ),
                ),
                ranges={
                    var: NdArrayFloat(
                        values=values,
                        type="NdArray",
                        dataType="float",
                        shape=[len(values), 1, 1],
                        axisNames="t x y".split(),
                    )
                },
                parameters={
                    var: Parameter(
                        id=var,
                        label={"en": var_dict[var].standard_name},
                        description={"en": var_dict[var].long_name},
                        observedProperty=ObservedProperty(
                            id=var,
                            label={"en": var_dict[var].standard_name},
                        ),
                        unit=Unit(id=var, label=dict(en=var_dict[var].units)),
                    )
                },
            )
        ]

    return CoverageCollection(coverages=coverages)


@router.get(
    "/area",
    tags=["Collection data queries"],
    response_model=CoverageCollection,
    response_model_exclude_none=True,
    response_class=CoverageJsonResponse,
)
async def get_data_area(
    coords: Annotated[
        str, Query(example="POLYGON((5.0 52.0, 6.0 52.0,6.0 52.1,5.0 52.1, 5.0 52.0))")
    ],
    parameter_name: Annotated[
        str | None,
        Query(
            alias="parameter-name",
            description="Comma seperated list of parameter names.",
            example="ff, dd",
        ),
    ] = None,
    datetime: Annotated[
        str | None, Query(example="2024-02-22T01:00:00Z/2024-02-22T02:00:00Z")
    ] = None,
) -> CoverageCollection:
    pass
