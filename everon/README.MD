Here is the complete, comprehensive `README.md` file for the **Everon** project. It is structured to act as professional documentation covering the entire architecture, layout configurations, installation procedures, and execution routines we have built.

### `README.md`

```markdown
# ⚡ Everon: Autonomous Multi-Service Intelligence Agent

Everon is an enterprise-grade, autonomous market intelligence agent designed to execute non-blocking sequential portfolio evaluations on a fixed 120-second cadence. The system implements the **Synapse Agent Protocol (SAP v2)** for tool discovery and leverages the **AceDataCloud X402 Payment Protocol** to orchestrate pay-per-request billing for high-fidelity LLM pipelines (Gemini Pro & GPT-4o).

Featuring graceful asset pipeline insulation, specialized trend divergence tie-breaking telemetries, and atomic local state preservation, Everon comes equipped with a real-time Streamlit dashboard to monitor data streams and system health visually.

---

## 🚀 Key Architectural Features

- **Autonomous Background Daemon (`scheduler.py`)**: Runs continuously as a non-blocking background worker that wakes up precisely every 120 seconds to trigger comprehensive asset-index evaluation loops.
- **Sequential Async Limits**: Enforces strict serial processing of target assets. This design eliminates race conditions, mitigates RPC node congestion, and completely evades public API rate limits.
- **Dual-Model Analytical Routing (`decision_engine.py`)**: Offloads narrative-heavy technical trend analysis and macroeconomic signaling to **Gemini Pro**, while routing strict structured telemetry framing to **GPT-4o**.
- **Cryptographic Pay-Per-Request Billing (`x402_client.py`)**: Signs incoming `402 Payment Required` server challenges transparently using Solana keypairs to fulfill metered SPL USDC billing without managing accounts or static api keys.
- **Fail-Safe Fault Isolation (`workflow.py`)**: Intercepts, catches, and isolates runtime connection/provider exceptions to a single token segment. If one tool gateway drops or timeouts, neighboring tracking nodes continue updating seamlessly.
- **Indecision Strategy Engine**: Evaluates conflicting technical indicator metrics against market social sentiment to identify high-ambiguity conditions, updating the local state with automated strategic insulation advice.


## 🛠️ Installation & Setup

### 1. Clone & Initialize Environment

Ensure Python 3.9+ is installed in your target local or containerized environment:

```bash
cd /path/to/your/projects/everon
pip install -r requirements.txt

```

### 2. Configure Environment Variables (`.env`)

Create a `.env` file in the root workspace directory. Everon utilizes strict type casting and automated key masking to secure your keys at runtime:

```env
# Core Identity Telemetry
AGENT_NAME=Everon

# Solana Signer Parameters (Required)
SOLANA_PRIVATE_KEY=your_base58_encoded_private_key_here
SOLANA_WALLET_ADDRESS=your_solana_public_wallet_address_here

# Network Node Gateways
SYNAPSE_RPC_URL=[https://staging.rpc.synapse-sap.net/v1](https://staging.rpc.synapse-sap.net/v1)
ACE_GEMINI_URL=[https://api.acedata.cloud/gemini/chat/completions](https://api.acedata.cloud/gemini/chat/completions)
ACE_GPT_URL=[https://api.acedata.cloud/openai/chat/completions](https://api.acedata.cloud/openai/chat/completions)

# Custom Token Index Tracking Override (Optional - Comma Separated)
TRACKING_INDEX=SOL,BTC,ETH,HYPE,JUP,PYTH,RENDER,BONK,WIF,DRIFT

```

---

## ⚡ Execution Instructions

Everon splits operations into an autonomous analytics collector daemon thread and an independent visualization dashboard interface.

### Running the Intelligence Daemon

Launch the core non-blocking daemon. This boots directory sync checks, verifies your wallet configuration, and triggers continuous sequential asset scans every 120 seconds:

```bash
python main.py

```

### Launching the Streamlit Visual Dashboard

To view live market analysis, tracking metrics, isolated token warning details, and live telemetric agent logs, run the Streamlit application in a separate terminal frame:

```bash
streamlit run app.py

```

---

## 🛡️ Error Recovery & System Policies

1. **`ERROR_ISOLATED` States**: When an underlying tool configuration or network RPC endpoint panics, Everon traps the trace, flags the token as `ERROR_ISOLATED` inside `market_intelligence.json`, logs the stack context, and skips straight to the next asset in sequence.
2. **`INDECISIVE` Trends**: If technical metrics indicate extreme compression or flag sharp decoupling vectors against recent sentiment markers, the decision engine shifts status to `INDECISIVE` and generates structured advice constraints (e.g., halving execution leverage parameters) visible directly on the monitoring interface.
3. **Rotating Log Buffer boundaries**: System logs are managed via thread-safe `RotatingFileHandler` logic limited to 10MB capacities across a 5-file history stack to protect disk storage limits during 24/7 background run-cycles.

```

```