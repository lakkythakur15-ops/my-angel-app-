import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. सुरक्षा सेटिंग्स (यहाँ अपना पासवर्ड बदलें) ---
USER_ID = "admin" # अपना मनचाहा यूजरनेम रखें
USER_PASS = "12345" # अपना गुप्त पासवर्ड यहाँ रखें

# --- 2. पेज और सेशन स्टेट सेटअप ---
st.set_page_config(page_title="Secure Pro Trader", layout="wide")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.0
if 'positions' not in st.session_state:
    st.session_state.positions = {}
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

# --- 3. लॉगिन फंक्शन ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Trader Login</h1>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            u_id = st.text_input("यूजरनेम")
            u_pass = st.text_input("पासवर्ड", type="password")
            if st.button("लॉगिन करें"):
                if u_id == USER_ID and u_pass == USER_PASS:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("गलत आईडी या पासवर्ड!")

# --- 4. मुख्य ऐप (अगर लॉगिन सफल हो) ---
if not st.session_state.authenticated:
    login_page()
else:
    # लॉगआउट बटन साइडबार में
    if st.sidebar.button("🚪 लॉगआउट"):
        st.session_state.authenticated = False
        st.rerun()

    # --- थीम्स और फंक्शन्स ---
    st.markdown("""<style>.stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #363a45; }</style>""", unsafe_allow_html=True)

    def calc_charges(qty, price, action):
        turnover = qty * price
        brokerage = min(20, turnover * 0.0003)
        stt = 0 if action == 'BUY' else turnover * 0.00025
        exch_txn = turnover * 0.0000345
        gst = (brokerage + exch_txn + (turnover * 0.000001)) * 0.18
        return round(brokerage + stt + exch_txn + gst, 2)

    tab1, tab2 = st.tabs(["📈 ट्रेडिंग टर्मिनल", "💼 पोर्टफोलियो"])

    with tab1:
        # ट्रेडिंग लॉजिक
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1: ticker = st.text_input("स्टॉक खोजें", "^NSEI")
        with col2: tf = st.selectbox("टाइमफ्रेम", ("5m", "15m", "30m", "1h", "1d"), index=1)
        with col3: qty = st.number_input("क्वांटिटी", min_value=1, value=50)

        @st.cache_data(ttl=60)
        def load_data(s, t):
            df = yf.download(s, period="5d", interval=t, progress=False)
            if not df.empty:
                df['Support'] = df['Low'].rolling(20).min().shift(1)
                df['Resist'] = df['High'].rolling(20).max().shift(1)
                df['AvgVol'] = df['Volume'].rolling(20).mean()
                df['Buy_Trap'] = (df['Low'] < df['Support']) & (df['Close'] > df['Support']) & (df['Volume'] > df['AvgVol'] * 1.5)
            return df

        data = load_data(ticker, tf)

        if not data.empty:
            cp = round(data['Close'].iloc[-1], 2)
            fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
            fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("करंट प्राइस", f"₹{cp}")
            m2.metric("वॉलेट", f"₹{round(st.session_state.balance, 2)}")
            
            pos = st.session_state.positions.get(ticker, {'qty': 0, 'avg_price': 0})
            m3.metric(f"पोजीशन ({ticker})", f"{pos['qty']} शेयर")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("🟢 BUY"):
                    charges = calc_charges(qty, cp, 'BUY')
                    st.session_state.balance -= (cp * qty + charges)
                    new_qty = pos['qty'] + qty
                    new_avg = ((pos['qty'] * pos['avg_price']) + (qty * cp)) / new_qty
                    st.session_state.positions[ticker] = {'qty': new_qty, 'avg_price': round(new_avg, 2)}
                    st.session_state.trade_history.append({"Date": datetime.now(), "Symbol": ticker, "Type": "BUY", "Qty": qty, "Price": cp, "Charges": charges, "Net P&L": 0.0})
                    st.rerun()
            with b2:
                if st.button("🔴 SELL"):
                    if pos['qty'] >= qty:
                        charges = calc_charges(qty, cp, 'SELL')
                        net_pnl = ((cp - pos['avg_price']) * qty) - charges - calc_charges(qty, pos['avg_price'], 'BUY')
                        st.session_state.balance += (cp * qty - charges)
                        st.session_state.positions[ticker]['qty'] -= qty
                        st.session_state.trade_history.append({"Date": datetime.now(), "Symbol": ticker, "Type": "SELL", "Qty": qty, "Price": cp, "Charges": charges, "Net P&L": round(net_pnl, 2)})
                        st.rerun()

    with tab2:
        st.subheader("📊 ट्रेड हिस्ट्री और रिपोर्ट")
        if st.session_state.trade_history:
            df = pd.DataFrame(st.session_state.trade_history)
            
            # फिल्टर
            f = st.radio("फिल्टर:", ("All", "Daily", "Weekly", "Monthly"), horizontal=True)
            now = datetime.now()
            if f == "Daily": df = df[df['Date'].dt.date == now.date()]
            elif f == "Weekly": df = df[df['Date'] >= (now - timedelta(days=now.weekday()))]
            elif f == "Monthly": df = df[df['Date'].dt.month == now.month]
            
            st.dataframe(df, use_container_width=True)
            
            c1, c2 = st.columns(2)
            c1.metric("टोटल चार्ज", f"₹{round(df['Charges'].sum(), 2)}")
            c2.metric("नेट P&L", f"₹{round(df['Net P&L'].sum(), 2)}", delta=round(df['Net P&L'].sum(), 2))
            
            # डेटा डाउनलोड करने का बटन
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 रिपोर्ट डाउनलोड करें (Excel/CSV)", data=csv, file_name="trade_report.csv", mime="text/csv")
