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
    # पेज को पूरा चौड़ा (Wide) कर दिया है ताकि चार्ट बड़ा दिखे
    st.set_page_config(page_title="Secure Pro Trader", layout="wide")
    st.sidebar.success("Welcome, Jagannath!")
    
    # साइडबार इनपुट
    symbol = st.sidebar.text_input("सिंबल (e.g. ^NSEI, SBIN.NS)", "^NSEI")
    tf = st.sidebar.selectbox("टाइमफ्रेम", ["15m", "30m", "1h", "1d"])
    
    # ऐप को फास्ट बनाने के लिए डिफ़ॉल्ट डेटा कम रखा है
    period_dict = {"15m": "5d", "30m": "1mo", "1h": "3mo", "1d": "1y"}
    selected_period = period_dict.get(tf, "1mo")

    @st.cache_data(ttl=300)
    def get_data(ticker, interval, period):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return pd.DataFrame()

    df = get_data(symbol, tf, selected_period)

    if df.empty or len(df) < 21:
        st.error(f"⚠️ {symbol} का डेटा नहीं मिला।")
        st.stop()

    # कैलकुलेशन
    df['Resist'] = df['High'].rolling(20).max().shift(1)
    df['Supp'] = df['Low'].rolling(20).min().shift(1)
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()

    df['Buy_Sig'] = (df['Low'] < df['Supp']) & (df['Close'] > df['Supp']) & (df['Volume'] > df['Vol_Avg'] * 1.5)
    df['Sell_Sig'] = (df['High'] > df['Resist']) & (df['Close'] < df['Resist']) & (df['Volume'] > df['Vol_Avg'] * 1.5)

    # --- एंजल वन जैसा एडवांस चार्ट बनाना ---
    fig = go.Figure()
    
    # कैंडलस्टिक
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
        name='Price', increasing_line_color='#26A69A', decreasing_line_color='#EF5350' # ट्रेडिंगव्यू वाले रंग
    ))
    
    # ट्रैप मार्कर्स
    buys = df[df['Buy_Sig']]
    sells = df[df['Sell_Sig']]
    fig.add_trace(go.Scatter(x=buys.index, y=buys['Low'], mode='markers', marker=dict(symbol='triangle-up', size=14, color='#00E676', line=dict(width=2, color='black')), name='Buy Trap'))
    fig.add_trace(go.Scatter(x=sells.index, y=sells['High'], mode='markers', marker=dict(symbol='triangle-down', size=14, color='#FF1744', line=dict(width=2, color='black')), name='Sell Trap'))

    # लेआउट ऑप्टिमाइज़ेशन (स्मूथ और फास्ट करने के लिए)
    fig.update_layout(
        height=650, 
        template="plotly_dark", 
        xaxis_rangeslider_visible=False,
        dragmode='pan', # डिफ़ॉल्ट रूप से चार्ट खिसकेगा (ज़ूम बॉक्स की जगह)
        margin=dict(l=10, r=50, t=30, b=10), # मोबाइल स्क्रीन का पूरा इस्तेमाल
        hovermode="x unified" # एक बार में पूरी कैंडल की जानकारी दिखाएगा
    )

    # --- मैजिक सेटिंग्स: ड्राइंग टूल्स और ज़ूम ---
    chart_config = {
        'scrollZoom': True,           # मोबाइल पर पिंच-टू-ज़ूम चालू
        'displayModeBar': True,       # ऊपर टूलबार दिखाएगा
        'modeBarButtonsToAdd': [      # एंजल वन जैसे टूल्स: ट्रेंडलाइन, बॉक्स, मिटाना
            'drawline', 'drawopenpath', 'drawrect', 'eraseshape'
        ],
        'displaylogo': False          # Plotly का लोगो हटाना
    }

    # चार्ट को स्क्रीन पर छापना
    st.plotly_chart(fig, use_container_width=True, config=chart_config)
    
    # डैशबोर्ड
    st.markdown(f"**LTP:** `₹{df['Close'].iloc[-1]:.2f}` | **कुल ट्रैप्स:** 🟢 {len(buys)} / 🔴 {len(sells)}")
