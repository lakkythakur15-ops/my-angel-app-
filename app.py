import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. सुरक्षा और लॉगिन सेटिंग्स ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Secure Pro Trader - Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u == "Jagannath" and p == "Chakanain@1122":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ गलत विवरण")
        return False
    return True

if check_password():
    st.set_page_config(page_title="Secure Pro Trader", layout="wide")
    st.sidebar.success("Welcome, Jagannath!")
    
    # साइडबार इनपुट
    symbol = st.sidebar.text_input("सिंबल (e.g. ^NSEI, SBIN.NS)", "^NSEI")
    tf = st.sidebar.selectbox("टाइमफ्रेम", ["15m", "30m", "1h", "1d"])

    @st.cache_data(ttl=300)
    def get_data(ticker, interval):
        try:
            # डेटा डाउनलोड
            df = yf.download(ticker, period="1mo", interval=interval, progress=False)
            # मल्टी-इंडेक्स कॉलम को साफ़ करना (Pandas Fix)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return pd.DataFrame()

    df = get_data(symbol, tf)

    # एरर चेक
    if df.empty or len(df) < 21:
        st.error(f"⚠️ {symbol} का डेटा नहीं मिला। कृपया सिंबल चेक करें।")
        st.stop()

    # कैलकुलेशन (S/R और Volume)
    df['Resist'] = df['High'].rolling(20).max().shift(1)
    df['Supp'] = df['Low'].rolling(20).min().shift(1)
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()

    # सिग्नल्स (Ambiguity Error को रोकने के लिए .values का उपयोग)
    df['Buy_Sig'] = (df['Low'] < df['Supp']) & (df['Close'] > df['Supp']) & (df['Volume'] > df['Vol_Avg'] * 1.5)
    df['Sell_Sig'] = (df['High'] > df['Resist']) & (df['Close'] < df['Resist']) & (df['Volume'] > df['Vol_Avg'] * 1.5)

    # चार्ट
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
    
    # ट्रैप मार्कर्स
    buys = df[df['Buy_Sig']]
    sells = df[df['Sell_Sig']]
    
    fig.add_trace(go.Scatter(x=buys.index, y=buys['Low'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='green'), name='Buy Trap'))
    fig.add_trace(go.Scatter(x=sells.index, y=sells['High'], mode='markers', marker=dict(symbol='triangle-down', size=12, color='red'), name='Sell Trap'))

    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    st.write(f"अंतिम क्लोजिंग प्राइस: {df['Close'].iloc[-1]:.2f}")
