---
name: heat-pump-control
description: Use for Persian chat commands controlling the heat pump.
---

# Heat Pump Control (warm pump, Hamburg)

Project dir: `/Users/negin-payam/Desktop/warmpomp`
Modbus TCP simulator on `127.0.0.1:5020` (unit 1). Registers: 0 = current temp ×10, 1 = target water temp (plain °C), 2 = pump 0/1.

## Chat commands
Run from the project dir:

```bash
cd /Users/negin-payam/Desktop/warmpomp && python3 pumpctl.py "<the user's exact message>"
```

Keyword mapping in `pumpctl.py`:
- مهمان / گرم کن / سردم / حمام / دوش → target 55°C, pump ON
- نیستم / سفر / تا فردا / خاموش → target 40°C, pump OFF
- وضعیت / چیه / چطوره → prints current Modbus status
- No match → exit code 2; interpret manually with `warm_pump_tools` (set_target_temp/set_pump) and confirm ambiguous intent.

After the simulator restarts, registers reset to 0 — if status shows target 0, re-apply the user's last intended mode instead of reporting the anomaly as-is.

## Auto-loop cron
Cron job `heat-pump-auto-loop` runs `~/.hermes/scripts/pump_auto_loop.py` every 30m in no_agent mode; writes 55°C when Hamburg temp < 25°C OR current price is in the cheapest 25% of the day, else 40°C. Silent (empty stdout) unless state changed; delivers to Telegram origin. Pause it when the user asks for no automatic messages.

Pitfalls (verified):
- Keep the cron script stdlib-only. The cron runner's python does NOT have project packages like pymodbus — the script talks raw Modbus TCP over sockets (FC 0x06 write single register, MBAP header) and never imports project modules.
- Cron scripts must live under `~/.hermes/scripts/` and use absolute paths (the project dir is hardcoded, not derived from `__file__`).
- Weather: Open-Meteo needs `forecast_days=2` to return a full 6-hour window late in the day.

If port 5020 is dead, restart the simulator from the project dir (background): `python3 heat_pump_sim.py`. Prices come from `prices.json` (24 hourly values) or a live URL via the `PRICE_URL` env var.