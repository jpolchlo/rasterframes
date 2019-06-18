#
# This software is licensed under the Apache 2 license, quoted below.
#
# Copyright 2019 Astraea, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# [http://www.apache.org/licenses/LICENSE-2.0]
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# SPDX-License-Identifier: Apache-2.0
#

"""
Module initialization for PyRasterFrames. This is where much of the cool stuff is
appended to PySpark classes.
"""

from __future__ import absolute_import
from pyspark import SparkContext
from pyspark.sql import SparkSession, DataFrame, DataFrameReader
from pyspark.sql.column import _to_java_column

# Import RasterFrame types and functions
from .rf_types import *
from . import rasterfunctions
from .context import RFContext
from .version import __version__

__all__ = ['RasterFrame', 'TileExploder']


def _rf_init(spark_session):
    """ Adds RasterFrames functionality to PySpark session."""
    if not hasattr(spark_session, "rasterframes"):
        spark_session.rasterframes = RFContext(spark_session)
        spark_session.sparkContext._rf_context = spark_session.rasterframes

    return spark_session


def _kryo_init(builder):
    """Registers Kryo Serializers for better performance."""
    # NB: These methods need to be kept up-to-date wit those in `org.locationtech.rasterframes.extensions.KryoMethods`
    builder \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.kryo.registrator", "org.locationtech.rasterframes.util.RFKryoRegistrator") \
        .config("spark.kryoserializer.buffer.max", "500m")
    return builder


def get_spark_session():
    from pyspark.sql import SparkSession
    import os
    import sys

    if sys.version < "3":
        import imp
        try:
            module_home = imp.find_module("pyrasterframes")[1]  # path
            jar_path = os.path.join(module_home, 'jars')
        except ImportError:
            print("pyrasterframes was not pip installed. See documentation for initialization instructions.")
            return None
    else:
        from importlib.util import find_spec
        try:
            module_home = find_spec("pyrasterframes").origin
            jar_path = os.path.join(os.path.dirname(module_home), 'jars')
        except ImportError:
            print("pyrasterframes was not pip installed. See documentation for initialization instructions.")
            return None

    jars_cp = ','.join([f.path for f in os.scandir(jar_path) if f.name[-3:] == 'jar'])
    spark = (SparkSession.builder
             .master("local[*]")
             .appName("RasterFrames")
             .config('spark.jars', jars_cp)
             .withKryoSerialization()
             .getOrCreate()
             ).withRasterFrames()
    return spark


def _convert_df(df, sp_key=None, metadata=None):
    ctx = SparkContext._active_spark_context._rf_context

    if sp_key is None:
        return RasterFrame(ctx._jrfctx.asRF(df._jdf), ctx._spark_session)
    else:
        import json
        return RasterFrame(ctx._jrfctx.asRF(
            df._jdf, _to_java_column(sp_key), json.dumps(metadata)), ctx._spark_session)


def _raster_join(df, other, left_extent=None, left_crs=None, right_extent=None, right_crs=None, join_exprs=None):
    ctx = SparkContext._active_spark_context._rf_context
    if join_exprs is not None:
        assert left_extent is not None and left_crs is not None and right_extent is not None and right_crs is not None
        # Note the order of arguments here.
        cols = [join_exprs, left_extent, left_crs, right_extent, right_crs]
        jdf = ctx._jrfctx.rasterJoin(df._jdf, other._jdf, *[_to_java_column(c) for c in cols])

    elif left_extent is not None:
        assert left_crs is not None and right_extent is not None and right_crs is not None
        cols = [left_extent, left_crs, right_extent, right_crs]
        jdf = ctx._jrfctx.rasterJoin(df._jdf, other._jdf, *[_to_java_column(c) for c in cols])

    else:
        jdf = ctx._jrfctx.rasterJoin(df._jdf, other._jdf)

    return RasterFrame(jdf, ctx._spark_session)


def _layer_reader(df_reader, format_key, path, **options):
    """ Loads the file of the given type at the given path."""
    df = df_reader.format(format_key).load(path, **options)
    return _convert_df(df)


def _rastersource_reader(df_reader, path=None, band_indexes=None, tile_dimensions=(256, 256), **options):
    if band_indexes is None:
        band_indexes = [0]

    def to_csv(comp): return ','.join(str(v) for v in comp)
    # If path is list, convert to newline delimited string and pass as "paths" (plural)
    options.update({
        "bandIndexes": to_csv(band_indexes),
        "tileDimensions": to_csv(tile_dimensions)
    })
    return df_reader \
        .format("rastersource") \
        .load(path, **options)


# Patch new method on SparkSession to mirror Scala approach
SparkSession.withRasterFrames = _rf_init
SparkSession.Builder.withKryoSerialization = _kryo_init

# Add the 'asRF' method to pyspark DataFrame
DataFrame.asRF = _convert_df

# Add `raster_join` method to pyspark DataFrame
DataFrame.raster_join = _raster_join

# Add DataSource convenience methods to the DataFrameReader
DataFrameReader.rastersource = _rastersource_reader

# Legacy readers
DataFrameReader.geotiff = lambda df_reader, path: _layer_reader(df_reader, "geotiff", path)
DataFrameReader.geotrellis = lambda df_reader, path: _layer_reader(df_reader, "geotrellis", path)
