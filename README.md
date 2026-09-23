# MT Agent

خانهٔ Hermes برای easyWebBuilder: `SOUL.md`، اسکیل‌های وب‌بیلدر، و اورلی کد روی checkout رسمی `hermes-agent`. کلیدها و سشن‌ها در گیت نیستند.

## نصب روی VPS

نیاز: Python 3.11 یا 3.12، Git، Node.js (برای PM2)، و `uv`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone git@github.com:payam-sharifi/MT_Agent.git ~/.hermes
git clone https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent
git checkout a55c972e09177e4db3934915e329993858b247d6
uv venv ~/.hermes/venvs/hermes --python 3.11
uv pip install --python ~/.hermes/venvs/hermes/bin/python -e ".[all]"
uv pip install --python ~/.hermes/venvs/hermes/bin/python -r ~/.hermes/requirements-local.txt
git apply ~/.hermes/deploy/easywebbuilder.patch
cp ~/.hermes/deploy/tools/*.py tools/
cd ~/.hermes
cp .env.example .env
cp config.example.yaml config.yaml
```

مقادیر `OPENROUTER_API_KEY`، `TELEGRAM_BOT_TOKEN` و `GOOGLE_API_KEY` را در `~/.hermes/.env` بگذارید.

## اجرا با PM2

```bash
npm install -g pm2
pm2 start ~/.hermes/venvs/hermes/bin/python \
  --name hermes-gateway \
  --cwd ~/.hermes/hermes-agent \
  -- hermes_cli/main.py gateway run --external-supervisor
pm2 save
pm2 startup
```

`pm2 logs hermes-gateway` لاگ را نشان می‌دهد. `pm2 restart hermes-gateway` بعد از عوض کردن `.env` یا اورلی کد.
