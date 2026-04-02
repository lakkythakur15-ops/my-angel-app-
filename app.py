import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. सुरक्षा और लॉगिन सेटिंग्स ---
def check_password():
    """रिटर्न True अगर यूजरनेम और पासवर्ड सही हैं"""
    def password_entered():
        """चेक करता है कि क्या क्रेडेंशियल्स मैच हो रहे हैं"""
        if (st.session_state["username"] == "Jagannath" and 
            st.session_state["password"] == "Chakanain@1122"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # सुरक्षा के लिए पासवर्ड हटा दें
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # लॉगिन फॉर्म दिखाना
        st.title("🔐 Secure Pro Trader - Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # गलत पासवर्ड होने पर दोबारा फॉर्म दिखाना
        st.title("🔐 Secure Pro Trader - Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("❌ यूजरनेम या पासवर्ड गलत है।")
        return False
    else:
        return True

# --- लॉगिन चेक करें ---
if check_password():
    # --- 2. मुख्य ऐप का हिस्सा (अगर लॉगिन सफल है) ---
    st.set_page_config(page_title="Secure Pro Trader - Operator Radar", layout="wide")

    st.sidebar.success(f"Welcome, Jagannath!")
    st.title("🏹 Operator Trap Radar - Live")
    st.markdown("---")

    # साइडबार सेटिंग्स
    st.sidebar.header("Trading Settings")
    symbol = st.sidebar.text_input("स्टॉक सिंबल (e.g. ^NSEI, RELIANCE.NS)", "^NSEI")
    timeframe = st.sidebar.selectbox("टाइमफ्रेम चुनें", ["15m", "30m", "1h", "1d"], index=0)
    period = st.sidebar.selectbox("कितने दिन का डेटा?", ["5d", "1mo", "3mo"], index=0)

    # डेटा डाउनलोड फंक्शन (कैशिंग के साथ)
    @st.cache_data(ttl=300)
    def get_live_data(ticker, tf, prd):
        try:
            data = yf.download(ticker, period=prd, interval=tf, progress=False)
            return data
        except Exception as e:
            return pd.DataFrame()

    df = get_live_data(symbol, timeframe, period)

    # सुरक्षा कवच
    if df is None or df.empty:
        st.error(f"⚠️ {symbol} के लिए डेटा नहीं मिल पाया।")
        st.stop()

    # इंडिकेटर्स कैलकुलेशन
    df['Resistance'] = df['High'].rolling(window=20).max().shift(1)
    df['Support'] = df['Low'].rolling(window=20).min().shift(1)
    df['Avg_Volume'] = df['Volume'].rolling(window=20).mean()
    df['Buy_Signal'] = False
    df['Sell_Signal'] = False

    # ट्रैप डिटेक्शन लॉजिक
    for i in range(20, len(df)):
        vol_spike = df['Volume'].iloc[i] > (df['Avg_Volume'].iloc[i] * 1.5)
        buy_hunt = df['Low'].iloc[i] < df['Support'].iloc[i]
        buy_absorb = df['Close'].iloc[i] > df['Support'].iloc[i]
        if buy_hunt and buy_absorb and vol_spike:
            df.iloc[i, df.columns.get_loc('Buy_Signal')] = True

        sell_hunt = df['High'].iloc[i] > df['Resistance'].iloc[i]
        sell_absorb = df['Close'].iloc[i] < df['Resistance'].iloc[i]
        if sell_hunt and sell_absorb and vol_spike:
            df.iloc[i, df.columns.get_loc('Sell_Signal')] = True

    # चार्ट बनाना
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=df.index, y=df['Support'], line=dict(color='green', width=1, dash='dot'), name='Support'))
    fig.add_trace(go.Scatter(x=df.index, y=df['Resistance'], line=dict(color='red', width=1, dash='dot'), name='Resistance'))

    # सिग्नल्स
    buy_indices = df[df['Buy_Signal']].index
    for idx in buy_indices:
        fig.add_annotation(x=idx, y=df.loc[idx, 'Low'], text="⬆️ BUY TRAP", showarrow=True, arrowhead=1, arrowcolor="green")

    sell_indices = df[df['Sell_Signal']].index
    for idx in sell_indices:
        fig.add_annotation(x=idx, y=df.loc[idx, 'High'], text="⬇️ SELL TRAP", showarrow=True, arrowhead=1, arrowcolor="red")

    fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # डैशबोर्ड जानकारी
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"कुल Buy सिग्नल्स: {df['Buy_Signal'].sum()}")
    with col2:
        st.error(f"कुल Sell सिग्नल्स: {df['Sell_Signal'].sum()}")
