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

# Для timeseries можно сгруппировать по датам заранее, чтобы не делать это в callback
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
    # Добавляем фигуры в хтмл.
    html.Div([dcc.Graph(id='timeseries', style={'border-right': '1px gray', 'border-bottom': '1px gray'}), 
        dcc.Graph(id='scatter', style={'border-right': '1px gray', 'border-top': '1px gray'})
    ], style={'height': '20%', 'width': '61%', 'display': 'inline-block'}),
    html.Div([dcc.Graph(id='pie', style={'border-left': '1px gray', 'border-bottom': '1px gray'}),
        dcc.Graph(id='wordcloud', style={'border-left': '1px gray', 'border-top': '1px gray'})],
        style={'height': '20%', 'width': '39%', 'float': 'right', 'display': 'inline-block'})
])



@app.callback(
    dash.dependencies.Output('timeseries', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_timeseries(dates, payers):
    """
    Callback временного ряда. Подаем крайние даты временного интервала и список PAYER из чеклиста.
    Фильтруем датасет, и рисуем.
    """
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df_sum_paid_by_payer[(df_sum_paid_by_payer['MONTH'] >= min_date) & (df_sum_paid_by_payer['MONTH'] <= max_date) & (np.isin(df_sum_paid_by_payer['PAYER'], payers))]
    
    # Заклинание против пустого чеклиста.
    if filtered_df.shape[0] == 0:
        return {}

    if dates[0] == dates[1]:
        fig = px.bar(filtered_df, x='PAYER', y='PAID_AMOUNT', hover_data=['TOP_SPECIALTIES'], color='PAYER')
        return fig
    
    fig = px.line(filtered_df, x='MONTH', y='PAID_AMOUNT', 
        line_group='PAYER', color='PAYER', hover_data=['TOP_SPECIALTIES'])

    fig.update_xaxes(
        tickformat="%b\n%Y"
    )
    fig.update_traces(mode="markers+lines")
    fig.update_layout(
        title={
            'text': 'SUM PAID AMOUNT BY MONTH',
            'y':0.93,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'})

    return fig

@app.callback(
    dash.dependencies.Output('scatter', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_scatter(dates, payers):
    """
    Callback scatter. Подаем крайние даты временного интервала и список PAYER из чеклиста.
    Фильтруем датасет, и рисуем.
    """
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df[(df['MONTH'] >= min_date) & (df['MONTH'] <= max_date) & (np.isin(df['PAYER'], payers))]
    
    # Заклинание против пустого чеклиста.
    if filtered_df.shape[0] == 0:
        return {}

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
    fig.update_layout(
        title={
            'text': 'SUM PAID AMOUNT AND NUMBER OF CLAIMS BY SERVICE CATEGORY AND PAYER',
            'y':0.93,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'})
    return fig

@app.callback(
    dash.dependencies.Output('pie', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_pie(dates, payers):
    """
    Callback пирога. Подаем крайние даты временного интервала и список PAYER из чеклиста.
    Фильтруем датасет, и рисуем.
    """
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df[(df['MONTH'] >= min_date) & (df['MONTH'] <= max_date) & (np.isin(df['PAYER'], payers))]
    
    # Заклинание против пустого чеклиста.
    if filtered_df.shape[0] == 0:
        return {}

    filtered_df = filtered_df.groupby(['SERVICE_CATEGORY'], as_index=False).agg({'PAID_AMOUNT': 'sum', 'CLAIM_SPECIALTY':lambda x: ' '.join(x)})
    filtered_df['CLAIM_SPECIALTY'] = filtered_df['CLAIM_SPECIALTY'].apply(lambda x: get_top3_specialty(x))
    labels = filtered_df['SERVICE_CATEGORY']
    values = filtered_df['PAID_AMOUNT']
    customdata = filtered_df['CLAIM_SPECIALTY']
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, customdata = customdata, hole=.6,
                            hovertemplate = "SERVICE_CATEGORY:%{label} <br>PAID_AMOUNT: %{value} </br> TOP SPECIALTIES:%{customdata}")])
    fig.update_layout(
        title={
            'text': 'SUM PAID AMOUNT BY SERVICE CATEGORY',
            'y':0.93,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'})


    return fig

@app.callback(
    dash.dependencies.Output('wordcloud', 'figure'),
    [dash.dependencies.Input('date_slider', 'value',),
    dash.dependencies.Input('payers_checklist', 'value')])
def update_wordcloud(dates, payers):
    """
    Callback wordcloud. Подаем крайние даты временного интервала и список PAYER из чеклиста.
    Фильтруем датасет, и рисуем.
    """
    min_date = months[dates[0]]['timestamp']
    max_date = months[dates[1]]['timestamp']
    filtered_df = df[(df['MONTH'] >= min_date) & (df['MONTH'] <= max_date) & (np.isin(df['PAYER'], payers))]
    
    # Заклинание против пустого чеклиста.
    if filtered_df.shape[0] == 0:
        return {}

    words = ' '.join(filter(lambda x: x != 'nan', [i for i in filtered_df['CLAIM_SPECIALTY']]))
    word_dict = dict(Counter(words.split(' ')))
    wc = WordCloud(background_color="white", max_words=1000)
    wc.generate_from_frequencies(word_dict)
    fig = px.imshow(wc)
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(
        title={
            'text': 'WORDCLOUD BY NUMBER OF CLAIMS',
            'y':0.93,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'}
    )

    return fig


if __name__ == '__main__':
    app.run_server(debug=False)