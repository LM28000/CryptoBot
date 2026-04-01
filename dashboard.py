import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go # Import manquant pour les graphiques avancés
import time

st.set_page_config(page_title="Crypto Grid Bot Dashboard", layout="wide")

def get_data():
    try:
        conn = sqlite3.connect("grid_bot.db", timeout=10)
        df_open = pd.read_sql_query("SELECT * FROM open_trades", conn)
        df_closed = pd.read_sql_query("SELECT * FROM closed_trades", conn)
        conn.close()
        return df_open, df_closed
    except Exception as e:
        st.error(f"Erreur DB : {e}")
        return pd.DataFrame(), pd.DataFrame()

def get_live_price():
    try:
        import ccxt
        ex = ccxt.binance() 
        return ex.fetch_ticker('BTC/USDT')['last']
    except:
        return None

st.title("🤖 Grid Bot Live Tracker")

refresh_rate = st.sidebar.slider("Rafraîchissement (secondes)", 2, 60, 10)

df_open, df_closed = get_data()

# --- AFFICHAGE ---
k1, k2, k3 = st.columns(3)
total_profit = df_closed['profit'].sum() if not df_closed.empty else 0.0

k1.metric("Profit Total", f"{total_profit:.4f} $")
k2.metric("Grilles Actives", len(df_open))
k3.metric("Trades Clos", len(df_closed))

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Courbe de Profit Cumulé")
    if not df_closed.empty:
        df_closed['cumulative_profit'] = df_closed['profit'].cumsum()
        fig_p = px.line(df_closed, y='cumulative_profit', title="Profit réel (net)")
        st.plotly_chart(fig_p, width='stretch')
    else:
        st.info("En attente de trades clôturés...")

with col2:
    st.subheader("🎯 Suivi des Paliers (Live)")
    live_price = get_live_price()
    
    if not df_open.empty and live_price:
        # Calcul des ventes prévues en utilisant le grid_step de la DB
        df_open['sell_price'] = df_open['buy_price'] + df_open['grid_step']
        
        # Calcul PnL Latent pour l'indicateur
        df_open['pnl_latente'] = (live_price - df_open['buy_price']) * df_open['amount']
        pnl_total = df_open['pnl_latente'].sum()
        st.metric("P&L Latent (Stock)", f"{pnl_total:.4f} $", delta=f"{pnl_total:.4f}")

        fig = go.Figure()
        
        # 1. Ligne du prix actuel
        fig.add_hline(y=live_price, line_dash="dash", line_color="gold", 
                      annotation_text=f"PRIX ACTUEL: {live_price:.2f}")

        # 2. Points d'achats (Triangles rouges vers le bas)
        fig.add_trace(go.Scatter(
            x=df_open['timestamp'], 
            y=df_open['buy_price'],
            mode='markers', 
            name='Achats Faits',
            marker=dict(color='red', size=10, symbol='triangle-down')
        ))

        # 3. Ventes prévues (Triangles verts vers le haut)
        fig.add_trace(go.Scatter(
            x=df_open['timestamp'], 
            y=df_open['sell_price'],
            mode='markers', 
            name='Ventes Prévues',
            marker=dict(color='#00ff00', size=10, symbol='triangle-up')
        ))

        fig.update_layout(
            title="Positionnement : Prix actuel vs Objectifs",
            yaxis_title="Prix USDT",
            template="plotly_dark",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Aucune grille active à afficher.")

# 3. Tableau de log
st.subheader("📋 Historique des 10 derniers trades")
if not df_closed.empty:
    st.dataframe(df_closed.tail(10).sort_index(ascending=False), width='stretch')

time.sleep(refresh_rate)
st.rerun()