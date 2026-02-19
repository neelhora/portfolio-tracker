# app.py
import pandas as pd
import yfinance as yf
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc

# ---------- Initialize App ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

app.layout = dbc.Container([
    html.H1("Neel's Portfolio Tracker", style={"textAlign": "center", "marginTop": 30, "marginBottom": 20}),
    
    # Input form
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Stock Ticker (e.g., AAPL)"),
                    dbc.Input(id="ticker-input", type="text", placeholder="Enter ticker")
                ], width=3),
                dbc.Col([
                    dbc.Label("Shares Owned"),
                    dbc.Input(id="shares-input", type="number", placeholder="Enter number of shares")
                ], width=3),
                dbc.Col([
                    dbc.Label("Purchase Date"),
                    dbc.Input(id="date-input", type="date")
                ], width=3),
                dbc.Col([
                    dbc.Label(" "),
                    dbc.Button("Add Stock", id="add-button", color="primary", className="w-100")
                ], width=3)
            ])
        ])
    ], className="mb-4"),

    # Hidden storage for portfolio
    dcc.Store(id="portfolio-store", data=[]),

    # Portfolio Graph
    dbc.Card([
        dbc.CardBody([
            dcc.Graph(id="portfolio-graph", style={"height": "400px"})
        ])
    ], className="mb-4"),

    # Portfolio Table
    dbc.Card([
        dbc.CardHeader(html.H4("Portfolio Overview")),
        dbc.CardBody([
            dash_table.DataTable(
                id="portfolio-table",
                columns=[
                    {"name": "Ticker", "id": "Ticker"},
                    {"name": "Shares", "id": "Shares"},
                    {"name": "Purchase Date", "id": "PurchaseDate"},
                    {"name": "Purchase Price ($)", "id": "PurchasePrice"},
                    {"name": "Current Price ($)", "id": "CurrentPrice"},
                    {"name": "Current Value ($)", "id": "CurrentValue"},
                    {"name": "Gain/Loss ($)", "id": "GainLoss"},
                ],
                style_header={
                    'backgroundColor': 'rgb(30, 30, 30)',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_cell={
                    'backgroundColor': 'rgb(50, 50, 50)',
                    'color': 'white',
                    'textAlign': 'center',
                    'padding': '5px'
                },
                style_table={'overflowX': 'auto'},
                page_size=10
            )
        ])
    ], className="mb-4"),

    # Portfolio Stats
    dbc.Card([
        dbc.CardBody([
            html.Div(id="portfolio-stats", style={"fontSize": 18})
        ])
    ], className="mb-4")

], fluid=True)

# ---------- Helper Functions ----------
def portfolio_value_over_time(portfolio_list):
    if not portfolio_list:
        return pd.DataFrame()
    df = pd.DataFrame(portfolio_list)
    combined = None
    for _, row in df.iterrows():
        try:
            prices = yf.Ticker(row['Ticker']).history(start=row['PurchaseDate'])['Close']
            value = prices * float(row['Shares'])
            if combined is None:
                combined = value.to_frame(row['Ticker'])
            else:
                combined = combined.join(value, how='outer')
        except Exception as e:
            print(f"Error fetching {row['Ticker']}: {e}")
    if combined is None:
        return pd.DataFrame()
    combined = combined.ffill().fillna(0)
    combined['Total'] = combined.sum(axis=1)
    return combined


def get_portfolio_table(portfolio_list):
    table_data = []

    for stock in portfolio_list:
        try:
            ticker = stock['Ticker']
            shares = float(stock['Shares'])
            purchase_date = stock['PurchaseDate']

            # Fetch historical prices
            hist = yf.Ticker(ticker).history(start=purchase_date)
            if hist.empty:
                continue  # skip stock if no data

            # Use first available closing price on/after purchase date
            purchase_price = hist['Close'].iloc[0]

            # Current price: most recent close
            current_price = yf.Ticker(ticker).history(period='1d')['Close'].iloc[-1]

            current_value = shares * current_price
            gain_loss = (current_price - purchase_price) * shares

            table_data.append({
                "Ticker": ticker,
                "Shares": shares,
                "PurchaseDate": purchase_date,
                "PurchasePrice": round(purchase_price, 2),
                "CurrentPrice": round(current_price, 2),
                "CurrentValue": round(current_value, 2),
                "GainLoss": round(gain_loss, 2)
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

    return table_data


def get_portfolio_stats(table_data):
    if not table_data:
        return "No portfolio data yet."

    total_value = sum(row.get("CurrentValue", 0) for row in table_data)
    total_invested = sum(row.get("PurchasePrice", 0) * row.get("Shares", 0) for row in table_data)
    total_gain = total_value - total_invested
    gain_percent = (total_gain / total_invested * 100) if total_invested > 0 else 0

    return f"Total Portfolio Value: ${total_value:,.2f} | Total Gain/Loss: ${total_gain:,.2f} ({gain_percent:.2f}%)"

# ---------- Callback ----------
@app.callback(
    Output("portfolio-store", "data"),
    Output("portfolio-graph", "figure"),
    Output("portfolio-table", "data"),
    Output("portfolio-stats", "children"),
    Input("add-button", "n_clicks"),
    State("ticker-input", "value"),
    State("shares-input", "value"),
    State("date-input", "value"),
    State("portfolio-store", "data")
)
def update_portfolio(n_clicks, ticker, shares, date, portfolio_data):
    if portfolio_data is None:
        portfolio_data = []

    # Add stock if inputs are valid
    if n_clicks and ticker and shares and date:
        portfolio_data.append({
            "Ticker": ticker.upper(),
            "Shares": shares,
            "PurchaseDate": date
        })

    # Generate graph
    data = portfolio_value_over_time(portfolio_data)
    if data.empty:
        fig = px.line(title="No stocks in portfolio yet.")
    else:
        fig = px.line(data, y='Total', title="Portfolio Value Over Time")

    # Generate table
    table = get_portfolio_table(portfolio_data)

    # Generate stats
    stats = get_portfolio_stats(table)

    return portfolio_data, fig, table, stats

# ---------- Run App ----------
if __name__ == "__main__":
    app.run(debug=True)
