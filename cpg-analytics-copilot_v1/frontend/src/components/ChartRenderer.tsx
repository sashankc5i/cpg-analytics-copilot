import Plot from "react-plotly.js";

import type {
  Visualization,
} from "../types/chat";


interface ChartRendererProps {
  visualization: Visualization;
}


export default function ChartRenderer({
  visualization,
}: ChartRendererProps) {

  if (
    !visualization ||
    visualization.x.length === 0 ||
    visualization.y.length === 0
  ) {
    return null;
  }


  const chartType =
    visualization.type === "bar"
      ? "bar"
      : "scatter";


  const chartData =
    chartType === "bar"
      ? [
          {
            x: visualization.x,
            y: visualization.y,
            type: "bar" as const,
          },
        ]
      : [
          {
            x: visualization.x,
            y: visualization.y,
            type: "scatter" as const,
            mode: "lines+markers" as const,
          },
        ];


  return (
    <div className="chart-container">

      <Plot
        data={chartData}
        layout={{
          title:
            visualization.title ||
            "Analytics",

          autosize: true,

          margin: {
            l: 70,
            r: 20,
            t: 55,
            b: 70,
          },

          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",

          xaxis: {
            automargin: true,
          },

          yaxis: {
            automargin: true,
          },
        }}

        useResizeHandler

        style={{
          width: "100%",
          height: "400px",
        }}

        config={{
          responsive: true,
          displaylogo: false,
        }}
      />

    </div>
  );
}