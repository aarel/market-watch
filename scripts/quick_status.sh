#!/bin/bash
# Quick status check for market-watch trading bot
# Usage: ./scripts/quick_status.sh

echo "=== MARKET-WATCH QUICK STATUS ==="
echo ""

curl -s http://localhost:8000/api/status | python3 -c "
import sys, json
try:
    status = json.load(sys.stdin)

    print('🤖 SYSTEM STATUS')
    print(f\"   Running: {status['running']}\")
    print(f\"   Universe: {status.get('universe', 'unknown')}\")
    print()

    print('💰 ACCOUNT')
    acct = status.get('account', {})
    print(f\"   Portfolio Value: \\\${acct.get('portfolio_value', 0):,.2f}\")
    print(f\"   Cash: \\\${acct.get('cash', 0):,.2f}\")
    print(f\"   Equity: \\\${acct.get('equity', 0):,.2f}\")
    print(f\"   Buying Power: \\\${acct.get('buying_power', 0):,.2f}\")
    print()

    print('📊 POSITIONS')
    positions = status.get('positions', [])
    if positions:
        total_pnl = sum(p.get('unrealized_pl', 0) for p in positions)
        for p in positions:
            pnl = p.get('unrealized_pl', 0)
            pnl_pct = p.get('unrealized_plpc', 0)
            color = '📉' if pnl < 0 else '📈'
            print(f\"   {color} {p['symbol']}: {p['qty']} shares @ \\\${p['avg_entry_price']:.2f} | P&L: \\\${pnl:.2f} ({pnl_pct:.1f}%)\")
        print(f\"   Total P&L: \\\${total_pnl:,.2f}\")
    else:
        print('   No open positions')
    print()

    print('🎯 SIGNALS')
    signal_agent = status.get('agents', {}).get('signal', {})
    print(f\"   Total signals: {signal_agent.get('signal_count', 0)}\")
    print(f\"   Actionable: {signal_agent.get('actionable', 0)}\")
    print(f\"   Strategy: {signal_agent.get('strategy', 'unknown')}\")
    print()

    print('⚙️  AGENTS')
    agents = status.get('agents', {})
    for name, agent in agents.items():
        if isinstance(agent, dict) and 'running' in agent:
            emoji = '✅' if agent['running'] else '❌'
            print(f\"   {emoji} {agent.get('name', name)}\")

except json.JSONDecodeError:
    print('❌ Error: Could not connect to server or invalid response')
    print('   Make sure the server is running on http://localhost:8000')
except Exception as e:
    print(f'❌ Error: {e}')
"

echo ""
echo "=== CONFIGURATION ==="
curl -s http://localhost:8000/api/config | python3 -c "
import sys, json
try:
    c = json.load(sys.stdin)
    print(f\"   Auto-trade: {c.get('auto_trade', False)}\")
    print(f\"   Trade interval: {c.get('trade_interval', 0)} min\")
    print(f\"   Max daily trades: {c.get('max_daily_trades', 0)}\")
    print(f\"   Strategy: {c.get('strategy', 'unknown')}\")
    print(f\"   RVOL threshold: {c.get('rvol_threshold', 0)}\")
    print(f\"   Momentum threshold: {c.get('momentum_threshold', 0)}\")
    print(f\"   Stop loss: {c.get('stop_loss_pct', 0)*100:.1f}%\")
except:
    print('   ❌ Could not fetch config')
"
