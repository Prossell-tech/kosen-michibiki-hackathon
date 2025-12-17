"use client";

import {useEffect, useMemo, useRef, useState} from "react";
import DeckGL from "@deck.gl/react";
import {GeoJsonLayer} from "@deck.gl/layers";
import {Map as MapboxMap, Popup} from "react-map-gl";

type PrefFeature = {
  properties?: {
    pref?: number;
    name?: string;
  };
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: any;
  };
};

type HazardEvent = {
  prefCode: number;
  message: string;
  receivedAt: number;
  centroid?: [number, number];
};

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";
const STREAM_ENDPOINT =
  process.env.NEXT_PUBLIC_STREAM_ENDPOINT || "/api/stream";

function computeCentroid(feature: PrefFeature): [number, number] | undefined {
  const coords = feature.geometry.coordinates;
  const pushPoint = (
    pt: number[],
    acc: {lon: number; lat: number; count: number}
  ) => {
    if (!Array.isArray(pt) || pt.length < 2) return;
    const [lon, lat] = pt;
    if (Number.isFinite(lon) && Number.isFinite(lat)) {
      acc.lon += lon;
      acc.lat += lat;
      acc.count += 1;
    }
  };

  const accum = {lon: 0, lat: 0, count: 0};

  if (feature.geometry.type === "Polygon") {
    coords.forEach((ring: number[][]) =>
      ring.forEach((pt) => pushPoint(pt, accum))
    );
  } else if (feature.geometry.type === "MultiPolygon") {
    coords.forEach((poly: number[][][]) =>
      poly.forEach((ring) => ring.forEach((pt) => pushPoint(pt, accum)))
    );
  }

  if (accum.count === 0) return undefined;
  return [accum.lon / accum.count, accum.lat / accum.count];
}

function parseIncomingMessage(
  raw: string,
  prefByName: Map<string, number>,
  centroids: Map<number, [number, number]>
): HazardEvent | null {
  const text = raw.trim();
  if (!text) return null;

  let prefCode: number | null = null;
  let messageText = text;

  const buildReadableMessage = (parsed: any) => {
    const parts: string[] = [];
    const cat =
      parsed?.disaster_category ??
      parsed?.message_type ??
      parsed?.message_header;
    if (cat) parts.push(String(cat));

    if (parsed?.information_type) parts.push(String(parsed.information_type));

    const time = parsed?.report_time ?? parsed?.occurrence_time_of_earthquake;
    if (time) parts.push(String(time));

    const epi = parsed?.seismic_epicenter ?? parsed?.epicenter;
    if (epi) parts.push(`震源:${epi}`);

    const mag = parsed?.magnitude;
    if (mag) parts.push(`M${mag}`);

    const inten =
      parsed?.seismic_intensity_upper_limit ??
      parsed?.seismic_intensity_lower_limit ??
      parsed?.seismic_intensity;
    if (inten) parts.push(`最大:${inten}`);

    const regions = Array.isArray(parsed?.eew_forecast_regions)
      ? parsed.eew_forecast_regions.join("・")
      : undefined;
    if (regions) parts.push(`対象:${regions}`);

    return parts.length ? parts.join(" / ") : text;
  };

  try {
    const parsed = JSON.parse(text);
    const candidate =
      parsed.prefCode ??
      parsed.pref ??
      parsed.prefectureCode ??
      parsed.prefecture ??
      parsed.pref_id ??
      parsed.pref_id2;
    if (typeof candidate === "number") prefCode = candidate;
    if (typeof candidate === "string") {
      const num = Number.parseInt(candidate, 10);
      if (Number.isFinite(num)) prefCode = num;
    }

    if (typeof parsed.message === "string" && parsed.message.trim()) {
      messageText = parsed.message;
      if (/\\x[0-9a-f]{2}/i.test(messageText) || messageText.startsWith("b'")) {
        messageText = buildReadableMessage(parsed);
      }
    } else {
      messageText = buildReadableMessage(parsed);
    }

    if (prefCode === null && Array.isArray(parsed.eew_forecast_regions)) {
      const hit = parsed.eew_forecast_regions.find(
        (r: any) => typeof r === "string" && prefByName.has(r)
      );
      if (hit) prefCode = prefByName.get(hit) ?? null;
    }

    if (prefCode === null && typeof parsed.seismic_epicenter === "string") {
      const hit = Array.from(prefByName.entries()).find(([name]) =>
        parsed.seismic_epicenter.includes(name)
      );
      if (hit) prefCode = hit[1];
    }
  } catch (_) {
    // not JSON
  }

  if (prefCode === null) {
    const nameHit = Array.from(prefByName.entries()).find(([name]) =>
      messageText.includes(name)
    );
    if (nameHit) {
      prefCode = nameHit[1];
    }
  }

  if (prefCode === null) {
    const m = messageText.match(/pref(?:ecture)?\s*[:=]?\s*(\d{1,2})/i);
    if (m) {
      prefCode = Number.parseInt(m[1], 10);
    }
  }

  if (prefCode === null || Number.isNaN(prefCode)) return null;

  return {
    prefCode,
    message: messageText,
    receivedAt: Date.now(),
    centroid: centroids.get(prefCode),
  };
}

export default function Home() {
  const [prefFeatures, setPrefFeatures] = useState<PrefFeature[]>([]);
  const [hazardByPref, setHazardByPref] = useState<Record<number, HazardEvent>>(
    {}
  );
  const [latestEvent, setLatestEvent] = useState<HazardEvent | null>(null);
  const [log, setLog] = useState<HazardEvent[]>([]);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

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

  useEffect(() => {
    const loadGeoJson = async () => {
      try {
        const res = await fetch("/prefectures.geojson");
        const geojson = await res.json();
        setPrefFeatures(geojson.features ?? []);
      } catch (err) {
        console.error("Failed to load prefecture shapes", err);
      }
    };
    loadGeoJson();
  }, []);

  const prefNameMap = useMemo(() => {
    const map = new Map<string, number>();
    prefFeatures.forEach((f) => {
      const name = f.properties?.name;
      const code = f.properties?.pref;
      if (name && typeof code === "number") {
        map.set(name, code);
      }
    });
    return map;
  }, [prefFeatures]);

  const centroids = useMemo(() => {
    const map = new Map<number, [number, number]>();
    prefFeatures.forEach((f) => {
      const code = f.properties?.pref;
      if (typeof code !== "number") return;
      const c = computeCentroid(f);
      if (c) map.set(code, c);
    });
    return map;
  }, [prefFeatures]);

  useEffect(() => {
    if (!prefFeatures.length) return;

    let es: EventSource | null = null;
    let retryMs = 1000;

    const connect = () => {
      es = new EventSource(STREAM_ENDPOINT);

      es.onmessage = (ev) => {
        const data = ev.data;
        const event = parseIncomingMessage(data, prefNameMap, centroids);
        if (!event) return;

        setHazardByPref((prev) => ({...prev, [event.prefCode]: event}));
        setLatestEvent(event);
        setLog((prev) => [event, ...prev].slice(0, 5));
      };

      es.onerror = () => {
        es?.close();
        retryMs = Math.min(retryMs * 2, 15000);
        reconnectTimer.current = setTimeout(connect, retryMs);
      };
    };

    connect();

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      es?.close();
    };
  }, [prefFeatures.length, prefNameMap, centroids]);

  const layers = useMemo(() => {
    if (!prefFeatures.length) return [];
    return [
      new GeoJsonLayer({
        id: "prefectures",
        data: {
          type: "FeatureCollection",
          features: prefFeatures as any,
        },
        pickable: true,
        stroked: true,
        filled: true,
        getFillColor: (f: PrefFeature) => {
          const code = f.properties?.pref;
          if (code && hazardByPref[code]) return [220, 38, 38, 220];
          return [200, 200, 200, 160];
        },
        getLineColor: [110, 110, 110, 200],
        lineWidthMinPixels: 1.2,
        updateTriggers: {
          getFillColor: [hazardByPref],
        },
      }),
    ];
  }, [prefFeatures, hazardByPref]);

  const popup = useMemo(() => {
    if (!latestEvent) return null;
    const pos = latestEvent.centroid ?? centroids.get(latestEvent.prefCode);
    if (!pos) return null;
    return {event: latestEvent, position: pos};
  }, [latestEvent, centroids]);

  return (
    <div style={{width: "100vw", height: "100vh", margin: 0, padding: 0}}>
      <DeckGL
        initialViewState={initialViewState}
        controller
        layers={layers}
        style={{width: "100%", height: "100%"}}
      >
        <MapboxMap
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/light-v11"
          projection={{name: "mercator"}}
          style={{width: "100%", height: "100%"}}
        >
          {popup && (
            <Popup
              longitude={popup.position[0]}
              latitude={popup.position[1]}
              closeButton={false}
              offset={[0, -10]}
              anchor="bottom"
            >
              <div style={{maxWidth: 260}}>
                <div style={{fontWeight: 700, marginBottom: 4}}>災害情報</div>
                <div style={{fontSize: 14, lineHeight: 1.4}}>
                  {popup.event.message}
                </div>
              </div>
            </Popup>
          )}
        </MapboxMap>
      </DeckGL>

      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          padding: "12px 14px",
          background: "rgba(0,0,0,0.55)",
          color: "#fff",
          borderRadius: 8,
          maxWidth: 360,
          backdropFilter: "blur(6px)",
          fontSize: 13,
          lineHeight: 1.5,
        }}
      >
        <div style={{fontWeight: 700, marginBottom: 8}}>受信ログ (最新5件)</div>
        {log.length === 0 && <div>Stream({STREAM_ENDPOINT}) に接続中...</div>}
        {log.slice(0, 5).map((e) => (
          <div key={e.receivedAt} style={{marginBottom: 6}}>
            <span style={{opacity: 0.8, marginRight: 8}}>
              {new Date(e.receivedAt).toLocaleTimeString("ja-JP", {
                hour12: false,
              })}
            </span>
            <span>{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
