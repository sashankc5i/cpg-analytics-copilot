import Plot from "react-plotly.js";

import type { Visualization } from "../types/chat";

interface ChartRendererProps {
  visualization: Visualization;
}

function isRevenueChart(title: string): boolean {
  const normalized = title.toLowerCase();
  return (
    normalized.includes("revenue") ||
    normalized.includes("sales") ||
    normalized.includes("value")
  );
}

function formatCompactValue(value: number, currency: boolean): string {
  const formatter = new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  });
  return `${currency ? "$" : ""}${formatter.format(value)}`;
}

export default function ChartRenderer({
  visualization,
}: ChartRendererProps) {
  const labels = Array.isArray(visualization?.x)
    ? visualization.x
    : [];
  const rawValues = Array.isArray(visualization?.y)
    ? visualization.y
    : [];

  // Ignore malformed rows instead of letting Plotly render misleading bars.
  const points = labels
    .map((label, index) => ({
      label: String(label ?? ""),
      value: Number(rawValues[index]),
    }))
    .filter(
      (point) =>
        point.label.length > 0 && Number.isFinite(point.value),
    );

  if (!points.length) {
    return null;
  }

  const title = visualization.title || "Analytics Results";
  const currency = isRevenueChart(title);
  const isBar = visualization.type === "bar";
  const values = points.map((point) => point.value);
  const categories = points.map((point) => point.label);
  const chartData = isBar
    ? [
        {
          x: categories,
          y: values,
          type: "bar" as const,
          marker: {
            color: "#7654D6",
            line: { color: "#6240C0", width: 1 },
          },
          text: values.map((value) => formatCompactValue(value, currency)),
          textposition: "outside" as const,
          cliponaxis: false,
          hovertemplate: currency
            ? "%{x}<br>Revenue: $%{y:,.2f}<extra></extra>"
            : "%{x}<br>Value: %{y:,.2f}<extra></extra>",
        },
      ]
    : [
        {
          x: categories,
          y: values,
          type: "scatter" as const,
          mode: "lines+markers+text" as const,
          line: { color: "#7654D6", width: 3, shape: "linear" as const },
          marker: {
            color: "#7654D6",
            size: 8,
            line: { color: "#FFFFFF", width: 1.5 },
          },
          text: values.map((value) => formatCompactValue(value, currency)),
          textposition: "top center" as const,
          hovertemplate: currency
            ? "%{x}<br>Revenue: $%{y:,.2f}<extra></extra>"
            : "%{x}<br>Value: %{y:,.2f}<extra></extra>",
        },
      ];

  return (
    <section className="chart-container" aria-label={title}>
      <div className="chart-heading">
        <h3>{title}</h3>
        <span>Interactive chart</span>
      </div>
      <Plot
        data={chartData}
        layout={{
          autosize: true,
          height: 360,
          margin: { l: 78, r: 34, t: 24, b: 78, pad: 4 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: {
            family: "Inter, ui-sans-serif, system-ui, sans-serif",
            size: 12,
            color: "#4B5563",
          },
          showlegend: false,
          hovermode: "closest",
          bargap: 0.34,
          xaxis: {
            title: { text: "Month / Category", standoff: 14 },
            automargin: true,
            tickfont: { size: 11, color: "#4B5563" },
            tickangle: categories.length > 8 ? -35 : 0,
            showgrid: false,
            zeroline: false,
            linecolor: "#D1D5DB",
          },
          yaxis: {
            title: { text: currency ? "Revenue ($)" : "Value", standoff: 12 },
            automargin: true,
            rangemode: "tozero",
            tickformat: currency ? "$,.3s" : ",.3s",
            gridcolor: "#E5E7EB",
            gridwidth: 1,
            zeroline: false,
            tickfont: { size: 11, color: "#6B7280" },
          },
          uniformtext: { minsize: 10, mode: "hide" },
        }}
        useResizeHandler
        style={{ width: "100%", height: "360px" }}
        config={{
          responsive: true,
          displaylogo: false,
          displayModeBar: true,
          modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
          toImageButtonOptions: {
            format: "png",
            filename: "cpg-analytics-chart",
            height: 720,
            width: 1280,
            scale: 2,
          },
        }}
      />
      <p className="chart-footnote">
        Hover over a data point to see the exact value.
      </p>
    </section>
  );
}
