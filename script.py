import ccxt
import time
import sqlite3

# --- CONFIGURATION DYNAMIQUE ---
SYMBOL = 'BTC/USDT'
GRID_PERCENTAGE = 0.002  # Je remets 0.8% pour la rentabilité, change-le si tu veux
AMOUNT_PER_GRID = 0.0001 
DB_NAME = "grid_bot.db"

exchange = ccxt.binance({
    'apiKey': 'VOTRE_API_KEY',
    'secret': 'VOTRE_SECRET_KEY',
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(True) 

def init_db():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS open_trades 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  buy_price REAL, amount REAL, grid_step REAL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS closed_trades 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  buy_price REAL, sell_price REAL, profit REAL)''')
    # Table pour garder le dernier prix de référence même après un crash du script
    c.execute('''CREATE TABLE IF NOT EXISTS bot_state 
                 (key TEXT PRIMARY KEY, value REAL)''')
    conn.commit()
    return conn

def get_current_price():
    ticker = exchange.fetch_ticker(SYMBOL)
    return ticker['last']

def run_bot():
    conn = init_db()
    cursor = conn.cursor()
    
    print(f"--- Bot Grid Dynamique ({GRID_PERCENTAGE*100}%) sur {SYMBOL} ---")
    
    while True:
        try:
            price = get_current_price()
            
            # 1. RÉCUPÉRATION DU PRIX DE RÉFÉRENCE
            # On cherche soit le dernier achat ouvert, soit la dernière vente effectuée
            cursor.execute("SELECT buy_price FROM open_trades ORDER BY timestamp DESC LIMIT 1")
            last_op = cursor.fetchone()
            
            if not last_op:
                # Si rien d'ouvert, on regarde le prix de la dernière vente dans closed_trades
                cursor.execute("SELECT sell_price FROM closed_trades ORDER BY id DESC LIMIT 1")
                last_op = cursor.fetchone()

            # 2. LOGIQUE D'ACTION
            if last_op:
                reference_price = last_op[0]
                target_buy = reference_price * (1 - GRID_PERCENTAGE)
                
                # ACHAT : Seulement si on est X% sous la dernière opération
                if price <= target_buy:
                    print(f"-> Baisse détectée ({price:.2f} <= {target_buy:.2f}). Achat.")
                    this_step = price * GRID_PERCENTAGE
                    cursor.execute("INSERT INTO open_trades (buy_price, amount, grid_step) VALUES (?, ?, ?)", 
                                (price, AMOUNT_PER_GRID, this_step))
                    conn.commit()
                else:
                    # On ne fait rien, on attend que ça baisse ou que ça monte pour vendre
                    pass
            else:
                # INITIALISATION TOTALE (Uniquement au tout premier lancement du bot)
                print(f"-> Initialisation : Premier achat à {price:.2f}")
                this_step = price * GRID_PERCENTAGE
                cursor.execute("INSERT INTO open_trades (buy_price, amount, grid_step) VALUES (?, ?, ?)", 
                            (price, AMOUNT_PER_GRID, this_step))
                conn.commit()

            # 3. LOGIQUE DE VENTE (Indépendante, on vérifie tous les tickets ouverts)
            cursor.execute("SELECT * FROM open_trades")
            all_open = cursor.fetchall()

            for trade in all_open:
                t_id, b_price, amt, g_step, _ = trade
                target_sell = b_price + g_step
                
                if price >= target_sell:
                    raw_profit = (price - b_price) * amt
                    fees = (price * amt * 0.001) + (b_price * amt * 0.001)
                    net_profit = raw_profit - fees
                    
                    print(f"-> VENTE : {b_price:.2f} -> {price:.2f} | Profit Net: {net_profit:.6f} USDT")
                    cursor.execute("INSERT INTO closed_trades (buy_price, sell_price, profit) VALUES (?, ?, ?)",
                                   (b_price, price, net_profit))
                    cursor.execute("DELETE FROM open_trades WHERE id = ?", (t_id,))
                    conn.commit()

            # 4. STATS
            cursor.execute("SELECT SUM(profit) FROM closed_trades")
            total_p = cursor.fetchone()[0] or 0.0
            cursor.execute("SELECT COUNT(*) FROM open_trades")
            active_g = cursor.fetchone()[0]
            print(f"Prix: {price:.2f} | Profit: {total_p:.4f} | Grilles: {active_g}")
            
            time.sleep(15)

        except Exception as e:
            print(f"ERREUR : {e}")
            time.sleep(20)

if __name__ == "__main__":
    run_bot()