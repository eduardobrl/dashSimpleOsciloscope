# -*- coding: utf-8 -*-
import numpy as np

import plotly.graph_objs as go
import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import json
import dash_daq as daq
import plotly.graph_objects as go

from dash_daq_drivers import keithley_instruments
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

# Define the app
app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)
server = app.server
app.config.suppress_callback_exceptions = False

# Font and background colors associated with each theme
bkg_color = {'dark': '#23262e', 'light': '#f6f6f7'}
grid_color = {'dark': '#53555B', 'light': '#969696'}
text_color = {'dark': '#95969A', 'light': '#595959'}
card_color = {'dark': '#2D3038', 'light': '#FFFFFF'}
accent_color = {'dark': '#FFD15F', 'light': '#ff9827'}

single_div_toggle_style = {
    'width': '80%',
    'display': 'flex',
    'flexDirection': 'row',
    'margin': 'auto',
    'alignItems': 'center',
    'justifyContent': 'space-between'
}

sweep_div_toggle_style = {
    'display': 'flex',
    'flexDirection': 'column',
    'alignItems': 'center',
    'justifyContent': 'space-around'
}

h_style = {
    'display': 'flex',
    'flex-direction': 'row',
    'alignItems': 'center',
    'justifyContent': 'space-evenly',
    'margin': '5px'
}

v_style = {
    'display': 'flex',
    'flex-direction': 'column',
    'alignItems': 'center',
    'justifyContent': 'space-between',
    'margin': '5px'
}

class Cursor:
    def __init__(self) -> None:
        self.x1 = 0
        self.x2 = 0
        self.points = [
            {
                "curveNumber": 0,
                "pointNumber": 0,
                "pointIndex": 0,
                "x": 0,
                "y": 0
            },
            {
                "curveNumber": 0,
                "pointNumber": 0,
                "pointIndex": 0,
                "x": 0,
                "y": 0
            }
        ]

        self.picking_x1 = False
        self.picking_x2 = False

        self.pick1_clicks = 0
        self.pick2_clicks = 0

class Gate:
    def __init__(self):
        self.x1 = 0
        self.x2 = 0

cursor = Cursor()
gate = Gate()

f = 60
T = 1/f
N = 100*2
t= np.linspace(0, 2*T,N)
y = 115 * np.sin(2*np.pi * t/T) * np.sqrt(2)
step = (T/100)
theme = 'light'

fig = go.Figure()
fig.add_trace(go.Scatter(
        x=t,
        y=y,
        mode='lines+markers',
        name='IV curve',
        line={
            'color': accent_color[theme],
            'width': 2
        }
))
gate.x1 = 0
gate.x2 = 0.01

def rms(y):
    return  np.sqrt(np.mean(np.square(y)))


def main_layout():
    app.layout = html.Div(
    id='main-page',
    className='container',
        children=[
        dcc.Store(id='picking-x1'),
        dcc.Store(id='picking-x2'),

        html.Div([  
            html.P("IV Curve"),
        ], className='appheader'),

        html.Div([  
            dcc.Graph(
                id='IV_graph',
                figure=fig
            ),
        ], className='graph'),
        
        html.Div([
            dcc.Markdown("## Seleção"),
            html.Pre(id='selected-data'),
            html.Pre(id='click-data'),
            daq.LEDDisplay(
                id='rms_display',
                label="Valor RMS",
                value=6
            ),
        ], className='selected'),

        html.Div([
            dcc.Markdown("## Cursores"),
            html.Div([
                html.Div([
                    daq.Knob(
                        id='cursor1_knob',
                        label='Cursor 1',
                        size = 80,
                        min = 0,
                        max = 100
                    ),
                    dcc.Input(
                        id="cursor1_input", type="number", placeholder="Cursor 1",
                        min=0, max=0.5, step=0.01,
                    ),
                    html.Button('Place Cursor 1', id='pick-cursor-1', n_clicks=0, style={"margin" : "10px 0px"}),
                ], style=v_style),

                html.Div([
                    daq.Knob(
                        id='cursor2_knob',
                        label='Cursor 2',
                        size = 80,
                        min = 0,
                        max = 100
                    ),
                    dcc.Input(
                        id="cursor2_input", type="number", placeholder="Cursor 2",
                        min=0, max=0.5, step=0.01,
                    ),
                    html.Button('Place Cursor 2', id='pick-cursor-2', n_clicks=0, style={"margin" : "10px 0px"}),
                ], style=v_style)

            ], style=h_style),

            html.Div([html.Pre(id='cursor-data')])

        ], className='cursors'),

        html.Div([
            dcc.Markdown("## Gatting"),
            daq.Knob(
                id='gate-knob',
                label='knob',
                size = 120,
                min = 0,
                max = 100
            ),
        ], className='gate'),

        ]
    )

@app.callback(
    Output('selected-data', 'children'),
    Output('rms_display', 'value'),
    Input('IV_graph', 'selectedData'))
def display_selected_data(selectedData):
    if selectedData is None:
        return ({}, 0)
    start = selectedData['points'][0]['x']
    end = selectedData['points'][-1]['x']
    y = np.array([point['y'] for point in selectedData['points'] if point['curveNumber'] == 0])
    y_rms = rms(y)
    
    out = {
        "start" : start,
        "end": end,
        "delta" : end - start,
        "rms": y_rms
    }
    
    return (json.dumps(out, indent=2), float(f"{y_rms : .2f}"))

@app.callback(
    Output('IV_graph', 'figure'),
    Output('cursor-data', 'children'),
    Output('cursor1_input', 'value'),
    Output('cursor2_input', 'value'),
    Output('cursor1_knob', 'value'),
    Output('cursor2_knob', 'value'),
    Input('picking-x1', 'data'),
    Input('picking-x2', 'data'),
    Input('IV_graph', 'clickData')
    )
def numeric_input_updated( pickX1, pickX2, clickData):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
            x=t,
            y=y,
            mode='lines+markers',
            name='IV curve',
            line={
                'color': accent_color[theme],
                'width': 2
            }
    ))

    if cursor.picking_x1 < pickX1:
        cursor.x1 = clickData['points'][0]['x']
        cursor.points[0] = clickData['points'][0]
        cursor.picking_x1 = pickX1

    elif cursor.picking_x2 < pickX2:
        cursor.x2 = clickData['points'][0]['x']
        cursor.points[1] = clickData['points'][0]
        cursor.picking_x2 = pickX2

    fig.add_vline(cursor.x1)
    fig.add_vline(cursor.x2)
    fig.add_vrect(
    x0=cursor.x1, x1=cursor.x2,
    fillcolor="LightSalmon", opacity=0.5,
    layer="below", line_width=0,
)


    cursor1_index = cursor.points[0]['pointNumber']
    cursor2_index = cursor.points[1]['pointNumber']

    start = 0
    end = 0

    if cursor1_index > cursor2_index:
        start = cursor2_index
        end = cursor1_index
    else:
        start = cursor1_index
        end = cursor2_index

    max_points = len(y)

    knob1 = float(cursor1_index) / max_points * 100
    knob2 = float(cursor2_index) / max_points * 100
    print(knob1)
    cursorData = {
        "t1" : cursor.x1,
        "t2" : cursor.x2,
        "v1": y[cursor1_index],
        "v2": y[cursor2_index],
        "delta" : cursor.x2 - cursor.x1,
        "rms" : rms(y[start:end+1])
    }

    return (fig, json.dumps(cursorData, indent=2),cursor.x1,cursor.x2, knob1, knob2)

# @app.callback(
#     Output('click-data', 'children'),
#     Input('IV_graph', 'clickData'),
#     Input('picking-x1', 'data'),
#     Input('picking-x2', 'data')
    
#     )
# def display_click_data(clickData, pickX1, pickX2):
#     if cursor.picking_x1 < pickX1:
#         cursor.x1 = clickData['points'][0]['x']
#         cursor.picking_x1 = pickX1
#     elif cursor.picking_x2 < pickX2:
#         cursor.x2 = clickData['points'][0]['x']
#         cursor.picking_x1 = pickX2

#     return json.dumps(clickData, indent=2)

@app.callback(
    Output('picking-x1', 'data'),
    Input('pick-cursor-1', 'n_clicks'))
def update_output(n_clicks):
    return n_clicks
    
@app.callback(
    Output('picking-x2', 'data'),
    Input('pick-cursor-2', 'n_clicks'))
def update_output(n_clicks):
    return n_clicks


if __name__ == "__main__":
    main_layout()
    app.run_server(debug=True)