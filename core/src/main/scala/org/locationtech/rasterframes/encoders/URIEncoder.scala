/*
 * This software is licensed under the Apache 2 license, quoted below.
 *
 * Copyright 2018 Astraea, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 *     [http://www.apache.org/licenses/LICENSE-2.0]
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 */

package org.locationtech.rasterframes.encoders

import java.net.URI

import org.apache.spark.sql.catalyst.encoders.ExpressionEncoder

/**
 * Custom Encoder for allowing friction-free use of URIs in DataFrames.
 *
 * @since 1/16/18
 */
object URIEncoder {
  def apply(): ExpressionEncoder[URI] =
    StringBackedEncoder[URI]("uri", "toASCIIString", (URIEncoder.getClass, "fromString"))
  // Not sure why this delegate is necessary, but doGenCode fails without it.
  def fromString(str: String): URI = URI.create(str)
}