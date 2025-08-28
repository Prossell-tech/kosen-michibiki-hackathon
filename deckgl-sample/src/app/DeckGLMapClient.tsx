"use client";

import {useMemo} from "react";
import {Map} from "react-map-gl";
import DeckGL from "@deck.gl/react";
import {GeoJsonLayer} from "@deck.gl/layers";
const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

export default function DeckGLMap() {
  const initialViewState = useMemo(
    () => ({
      longitude: 137.726,
      latitude: 37.5,
      zoom: 4.5,
      pitch: 0,
      bearing: 0,
    }),
    []
  );

  // カラーパレット
  const PREF_COLORS = [
    [255, 99, 132],
    [54, 162, 235],
    [255, 206, 86],
    [75, 192, 192],
    [153, 102, 255],
    [255, 159, 64],
    [199, 199, 199],
    [83, 102, 255],
    [255, 102, 255],
    [102, 255, 102],
    [255, 153, 51],
    [51, 153, 255],
    [255, 51, 153],
    [153, 255, 51],
    [51, 255, 153],
    [153, 51, 255],
    [255, 255, 102],
    [102, 255, 255],
    [255, 102, 102],
    [102, 102, 255],
    [255, 204, 204],
    [204, 255, 204],
    [204, 204, 255],
    [255, 255, 204],
    [204, 255, 255],
    [255, 204, 255],
    [255, 255, 153],
    [153, 255, 255],
    [255, 153, 255],
    [255, 255, 204],
    [204, 255, 153],
    [153, 204, 255],
    [255, 204, 153],
    [153, 255, 204],
    [204, 153, 255],
    [255, 153, 204],
    [204, 204, 153],
    [153, 204, 204],
    [204, 153, 204],
    [204, 204, 204],
    [153, 153, 204],
    [204, 153, 153],
    [153, 204, 153],
    [153, 153, 153],
    [102, 102, 102],
    [51, 51, 51],
    [0, 0, 0],
  ];

  const layers = [
    new GeoJsonLayer({
      id: "prefectures",
      data: "/prefectures.geojson",
      pickable: true,
      stroked: true,
      filled: true,
      getFillColor: (f: any) => {
        const idx = (f.properties?.pref ?? 0) % PREF_COLORS.length;
        return [...PREF_COLORS[idx], 180];
      },
      getLineColor: [80, 80, 80, 200],
      lineWidthMinPixels: 1,
    }),
  ];

  return (
    <DeckGL
      initialViewState={initialViewState}
      controller={true}
      layers={layers}
      style={{width: "100vw", height: "100vh"}}
    >
      <Map
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle="mapbox://styles/mapbox/light-v11"
        projection="mercator"
        style={{width: "100vw", height: "100vh"}}
      />
    </DeckGL>
  );
}
