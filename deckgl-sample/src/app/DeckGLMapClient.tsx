"use client";

import {useMemo} from "react";
import {Map} from "react-map-gl";
import DeckGL from "@deck.gl/react";
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

  const layers: unknown[] = [];

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
        style={{width: "100vw", height: "100vh"}}
      />
    </DeckGL>
  );
}
