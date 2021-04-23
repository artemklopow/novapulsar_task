import dash
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


from collections import Counter
from wordcloud import WordCloud


def get_top3_specialty(string):
    """
    Принимает строку из слов разделенных пробелом.
    Возвращает 3 наиболее часто встречающихся слова разделенных заяпятой.
    Значаения 'nan' удаляются
    """
    specialties = filter(lambda x: x != 'nan', string.split(' '))
    count_specialties = Counter(specialties)
    return ', '.join([i[0] for i in count_specialties.most_common(3)])

# Основной датасет.
df = pd.read_csv('application/data/df.csv', sep=',')
df['CLAIM_SPECIALTY'] = df['CLAIM_SPECIALTY'].fillna('nan')

# Преобразуем в timestamp.
df['MONTH'] = pd.to_datetime(df['MONTH'])

# Создаём словарь {id_month: {'timestamp': pd.Timestamp, 'string': строковое_представление_месяца}}
months = pd.Series(df['MONTH'].unique())
months = dict((i, {'timestamp': months[i], 'string': months[i].strftime('%b %Y')}) for i in months.index)

payers = list(df['PAYER'].unique())

# Группировки датасета. Чтобы не делать это в callback
df_sum_paid_by_payer = df.groupby(by=['MONTH', 'PAYER'], as_index=False).agg({'PAID_AMOUNT': 'sum', 
                                                                              'CLAIM_SPECIALTY': lambda x: ' '.join(x)})
df_sum_paid_by_payer.rename(columns={'CLAIM_SPECIALTY': 'TOP_SPECIALTIES'}, inplace=True)
df_sum_paid_by_payer['TOP_SPECIALTIES'] = df_sum_paid_by_payer['TOP_SPECIALTIES'].apply(lambda x: get_top3_specialty(x))

app = dash.Dash(__name__)
app.layout = html.Div([
    
    html.Div([
    
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
            value=[min(months.keys()), max(months.keys())],
        ),
        html.Br(),
        
        # PAYER checklist
        dcc.Checklist(
            id='payers_checklist',
            options=[{'label': i, 'value': i} for i in payers],
            value=payers,
            style={'text-align': 'center'}
            )
        ], 
    ),
    dcc.Graph(id='timeseries', style={'border': '3px solid green'}),
    dcc.Graph(id='scatter', style={'border': '3px solid black'}),
    dcc.Graph(id='pie', style={'border': '3px solid red'}),
    dcc.Graph(id='wordcloud', style={'border': '3px solid blue'}),
    html.Br(),
    html.Div(id='out_date_slider'),
    html.Div(id='out_payers_checklist')
])


@app.callback(
    dash.dependencies.Output('out_date_slider', 'children'),
    [dash.dependencies.Input('date_slider', 'value')])
def update_dates(value):
    return '{} - {}'.format(months[value[0]]['string'], months[value[1]]['string'])


@app.callback(
    dash.dependencies.Output('out_payers_checklist', 'children'),
    [dash.dependencies.Input('payers_checklist', 'value')])
def update_payers(value):
    return ', '.join(value)

@app.callback(
    dash.dependencies.Output('timeseries', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_timeseries(dates, payers):
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df_sum_paid_by_payer[(df_sum_paid_by_payer['MONTH'] >= min_date) & (df_sum_paid_by_payer['MONTH'] <= max_date) & (np.isin(df_sum_paid_by_payer['PAYER'], payers))]
    fig = px.line(filtered_df, x="MONTH", y="PAID_AMOUNT", line_group='PAYER', color='PAYER', hover_data=['TOP_SPECIALTIES'])

    fig.update_xaxes(
        tickformat="%b\n%Y"
    )
    fig.update_traces(mode="markers+lines")

    return fig

@app.callback(
    dash.dependencies.Output('scatter', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_scatter(dates, payers):
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df[(df['MONTH'] >= min_date) & (df['MONTH'] <= max_date) & (np.isin(df['PAYER'], payers))]
    
    filtered_df = filtered_df.groupby(by=['SERVICE_CATEGORY', 'PAYER'], as_index=False).agg({'PAID_AMOUNT': 'sum',
                                                                              'MONTH': 'count',
                                                                              'CLAIM_SPECIALTY': lambda x: ' '.join(x)})

    filtered_df['CLAIM_SPECIALTY'] = filtered_df['CLAIM_SPECIALTY'].apply(lambda x: get_top3_specialty(x))
    filtered_df.rename(columns={'MONTH': 'CLAIMS', 'CLAIM_SPECIALTY': 'TOP_SPECIALTIES'}, inplace=True)
    
    fig = px.scatter(filtered_df, x='PAYER', 
                y='SERVICE_CATEGORY', 
                color='CLAIMS', 
                size='PAID_AMOUNT', 
                hover_data=['PAID_AMOUNT', 'CLAIMS', 'TOP_SPECIALTIES'],
                size_max=40)
    return fig

@app.callback(
    dash.dependencies.Output('pie', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_pie(dates, payers):
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df[(df['MONTH'] >= min_date) & (df['MONTH'] <= max_date) & (np.isin(df['PAYER'], payers))]
    filtered_df = filtered_df.groupby(['SERVICE_CATEGORY'], as_index=False).agg({'PAID_AMOUNT': 'sum', 'CLAIM_SPECIALTY':lambda x: ' '.join(x)})
    filtered_df['CLAIM_SPECIALTY'] = filtered_df['CLAIM_SPECIALTY'].apply(lambda x: get_top3_specialty(x))
    labels = filtered_df['SERVICE_CATEGORY']
    values = filtered_df['PAID_AMOUNT']
    customdata = filtered_df['CLAIM_SPECIALTY']
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, customdata = customdata, hole=.6,
                            hovertemplate = "SERVICE_CATEGORY:%{label} <br>PAID_AMOUNT: %{value} </br> TOP SPECIALTIES:%{customdata}")])
    
    return fig

@app.callback(
    dash.dependencies.Output('wordcloud', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_wordcloud(dates, payers):
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df[(df['MONTH'] >= min_date) & (df['MONTH'] <= max_date) & (np.isin(df['PAYER'], payers))]
    words = ' '.join(filter(lambda x: x != 'nan', [i for i in filtered_df['CLAIM_SPECIALTY']]))
    word_dict = dict(Counter(words.split(' ')))
    wc = WordCloud(background_color="white", max_words=1000)
    wc.generate_from_frequencies(word_dict)
    fig = px.imshow(wc)
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)