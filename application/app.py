import dash
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd

# Основной датасет.
df = pd.read_csv('application/data/df.csv', sep=',')

# Преобразуем в timestamp.
df['MONTH'] = pd.to_datetime(df['MONTH'])

# Создаём словарь {id_month: {'timestamp': pd.Timestamp, 'string': строковое_представление_месяца}}
months = pd.Series(df['MONTH'].unique())
months = dict((i, {'timestamp': months[i], 'string': months[i].strftime('%b %Y')}) for i in months.index)

app = dash.Dash(__name__)
app.layout = html.Div([
    
    # Слайдер выбора временного промежутка.
    dcc.RangeSlider(
        id='date_slider',
        min=min(months.keys()),
        max=max(months.keys()),
        step=None,
        marks=dict(
            (i, 
            {
                'label': months[i]['string'], 
                'style': {'width': '1px', 'text-align': 'center'}
             }
             ) for i in months),
        value=[min(months.keys()), max(months.keys())]
    ),
    html.Br(),
    html.Div(id='out_date_slider')
])


@app.callback(
    dash.dependencies.Output('out_date_slider', 'children'),
    [dash.dependencies.Input('date_slider', 'value')])
def update_output(value):
    return '{} - {}'.format(months[value[0]]['string'], months[value[1]]['string'])


if __name__ == '__main__':
    app.run_server(debug=True)
