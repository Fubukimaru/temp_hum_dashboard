from influxdb import InfluxDBClient

from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

INFLUX_HOST = "afrodita.local"
INFLUX_PORT = 8086
INFLUX_DATABASE = "casa"


# ----------------------------------------------------------------------
# InfluxDB
# ----------------------------------------------------------------------

client = InfluxDBClient(
    host=INFLUX_HOST,
    port=INFLUX_PORT,
    database=INFLUX_DATABASE,
)


def read_measurement(measurement, minutes, interval):
    query = f"""
        SELECT mean("value_mean") AS value
        FROM "{measurement}"
        WHERE time > now() - {minutes}m
        GROUP BY time({interval}), "sensor_id"
        fill(null)
    """

    result = client.query(query)

    series = []

    for (_, tags), points in result.items():
        points = list(points)

        series.append({
            "sensor": tags["sensor_id"],
            "points": points,
        })

    return series


# ----------------------------------------------------------------------
# Plot creation
# ----------------------------------------------------------------------

def make_graph(series, title, unit):
    fig = go.Figure()

    for item in series:
        sensor = item["sensor"]
        points = item["points"]

        times = []
        values = []

        for point in points:
            if point["value"] is not None:
                times.append(point["time"])
                values.append(point["value"])

        fig.add_trace(
            go.Scatter(
                x=times,
                y=values,
                mode="lines",
                name=sensor,
                line=dict(width=2),
                hovertemplate=(
                    f"<b>{sensor}</b><br>"
                    f"%{{y:.1f}} {unit}<br>"
                    "%{x|%H:%M:%S · %d %b}"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=22)),
        template="plotly_dark",
        height=400,
        hovermode="x unified",

        margin=dict(
            l=50,
            r=30,
            t=80,
            b=40,
        ),

        xaxis_title=None,
        yaxis_title=unit,

        paper_bgcolor="#1f2937",
        plot_bgcolor="#1f2937",

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(showgrid=False)

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.08)",
        zeroline=False,
    )

    return fig


# ----------------------------------------------------------------------
# Dash application
# ----------------------------------------------------------------------

app = Dash(__name__)
app.title = "Casa"


app.layout = html.Div(
    [
        # Header
        html.Div(
            [
                html.Div(
                    [
                        html.H1(
                            "Casa",
                            style={
                                "margin": "0",
                                "fontSize": "30px",
                            },
                        ),

                        html.Div(
                            "Temperature & humidity",
                            style={
                                "color": "#9ca3af",
                                "marginTop": "4px",
                            },
                        ),
                    ]
                ),

                html.Div(
                    [
                        html.Span(
                            "Time range",
                            style={"color": "#9ca3af"},
                        ),

                        dcc.Dropdown(
                            id="time-range",

                            options=[
                                {
                                    "label": "5 minutes",
                                    "value": 5,
                                },
                                {
                                    "label": "15 minutes",
                                    "value": 15,
                                },
                                {
                                    "label": "30 minutes",
                                    "value": 30,
                                },
                                {
                                    "label": "1 hour",
                                    "value": 60,
                                },
                                {
                                    "label": "3 hours",
                                    "value": 180,
                                },
                                {
                                    "label": "6 hours",
                                    "value": 360,
                                },
                                {
                                    "label": "12 hours",
                                    "value": 720,
                                },
                                {
                                    "label": "24 hours",
                                    "value": 1440,
                                },
                                {
                                    "label": "3 days",
                                    "value": 4320,
                                },
                                {
                                    "label": "7 days",
                                    "value": 10080,
                                },
                                {
                                    "label": "30 days",
                                    "value": 43200,
                                },
                            ],

                            value=1440,
                            clearable=False,

                            style={
                                "width": "160px",
                                "color": "#111827",
                            },
                        ),

                        html.Button(
                            "↻ Refresh",
                            id="refresh-button",
                            n_clicks=0,

                            style={
                                "height": "38px",
                                "padding": "0 18px",
                                "border": "none",
                                "borderRadius": "7px",
                                "backgroundColor": "#2563eb",
                                "color": "white",
                                "fontWeight": "600",
                                "cursor": "pointer",
                            },
                        ),
                    ],

                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "15px",
                    },
                ),
            ],

            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "25px",
                "flexWrap": "wrap",
                "gap": "20px",
            },
        ),

        # Temperature
        html.Div(
            [
                dcc.Graph(
                    id="temperature",

                    config={
                        "displaylogo": False,
                        "scrollZoom": True,
                    },
                ),
            ],

            style={
                "backgroundColor": "#1f2937",
                "borderRadius": "12px",
                "overflow": "hidden",
                "marginBottom": "20px",
            },
        ),

        # Humidity
        html.Div(
            [
                dcc.Graph(
                    id="humidity",

                    config={
                        "displaylogo": False,
                        "scrollZoom": True,
                    },
                ),
            ],

            style={
                "backgroundColor": "#1f2937",
                "borderRadius": "12px",
                "overflow": "hidden",
            },
        ),

        # Automatic refresh every 60 seconds
        dcc.Interval(
            id="auto-refresh",
            interval=60 * 1000,
            n_intervals=0,
        ),
    ],

    style={
        "backgroundColor": "#111827",
        "color": "#f3f4f6",
        "minHeight": "100vh",
        "padding": "30px",

        "fontFamily": (
            "Inter, system-ui, -apple-system, "
            "BlinkMacSystemFont, sans-serif"
        ),
    },
)


# ----------------------------------------------------------------------
# Dashboard update
# ----------------------------------------------------------------------

@app.callback(
    Output("temperature", "figure"),
    Output("humidity", "figure"),

    Input("time-range", "value"),
    Input("refresh-button", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
)
def update_dashboard(minutes, _, __):

    # Choose aggregation resolution depending on selected range.
    #
    # Your sensors appear to report approximately once per minute,
    # so there's little benefit in going below 1 minute here.

    if minutes <= 60:
        interval = "1m"

    elif minutes <= 360:
        interval = "2m"

    elif minutes <= 1440:
        interval = "5m"

    elif minutes <= 4320:
        interval = "15m"

    elif minutes <= 10080:
        interval = "30m"

    else:
        interval = "2h"

    temperature = read_measurement(
        "temperature",
        minutes=minutes,
        interval=interval,
    )

    humidity = read_measurement(
        "humidity",
        minutes=minutes,
        interval=interval,
    )

    return (
        make_graph(
            temperature,
            "Temperature",
            "°C",
        ),

        make_graph(
            humidity,
            "Humidity",
            "%",
        ),
    )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8050,
        debug=False,
    )
