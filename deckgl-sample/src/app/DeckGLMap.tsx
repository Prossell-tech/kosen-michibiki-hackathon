import {useMemo} from "react";
import {Map} from "react-map-gl";
import DeckGL from "@deck.gl/react";
import {ScatterplotLayer} from "@deck.gl/layers";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

type DataPoint = {
  position: [number, number];
  size: number;
};

export default function DeckGLMap() {
  const initialViewState = useMemo(
    () => ({
      longitude: 139.7671,
      latitude: 35.6812,
      zoom: 10,
      pitch: 0,
      bearing: 0,
    }),
    []
  );

  const layers = [
    new ScatterplotLayer<DataPoint>({
      id: "scatterplot-layer",
      data: [{position: [139.7671, 35.6812], size: 100}],
      getPosition: (d: DataPoint) => d.position,
      getRadius: (d: DataPoint) => d.size,
      getFillColor: [255, 0, 0, 200],
    }),
  ];

  return (
    <DeckGL
      initialViewState={initialViewState}
      controller={true}
      layers={layers}
      style={{width: "100vw", height: "60vh"}}
    >
      <Map
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle="mapbox://styles/mapbox/streets-v11"
        style={{width: "100vw", height: "60vh"}}
      />
    </DeckGL>
  );
}
