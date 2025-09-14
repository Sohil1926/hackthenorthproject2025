# sigma_mulcher

A tiny, dependency-free Python CLI that can call multiple LLM providers from one place.

Providers supported:

- Groq
- Cohere
- Cerebras
- Databricks
- Vapi

The CLI uses only Python's standard library and reads configuration from environment variables.

## Quick start

From the project root, run:

```powershell
# Windows PowerShell examples
$env:SIGMA_MULCHER_TIMEOUT = "60"
$env:SIGMA_MULCHER_TEMPERATURE = "0.2"

# Pick and set the relevant provider credentials before running (examples below)
python -m sigma_mulcher --help
```

Basic invocation:

```powershell
python -m sigma_mulcher -p groq -q "Write a limerick about databases"
```

Add a system prompt, different model, temperature, or print raw JSON response:

```powershell
python -m sigma_mulcher -p groq -q "Summarize this: ..." -s "You are concise." -m llama-3.1-8b-instant -t 0.3 --raw
```

## Environment variables

### Shared options

- `SIGMA_MULCHER_TIMEOUT` (default `60`): HTTP request timeout in seconds
- `SIGMA_MULCHER_TEMPERATURE` (default `0.2`): Sampling temperature used by providers that support it

### Groq

- `GROQ_API_KEY` (required)
- `GROQ_API_BASE` (optional, default `https://api.groq.com/openai/v1`)
- `GROQ_MODEL` (optional, default `llama-3.1-8b-instant`)

Example:

```powershell
$env:GROQ_API_KEY = "sk_..."
python -m sigma_mulcher -p groq -q "Hello!"
```

### Cohere

- `COHERE_API_KEY` (required)
- `COHERE_API_BASE` (optional, default `https://api.cohere.com/v1/chat`)
- `COHERE_MODEL` (optional, default `command-r`)

Example:

```powershell
$env:COHERE_API_KEY = "cohere_..."
python -m sigma_mulcher -p cohere -q "Explain JSON in simple terms"
```

### Cerebras

- `CEREBRAS_API_KEY` (required)
- `CEREBRAS_API_BASE` (optional, default `https://api.cerebras.ai/v1`)
- `CEREBRAS_MODEL` (optional, default `llama3.1-8b`)

Example:

```powershell
$env:CEREBRAS_API_KEY = "cb_..."
python -m sigma_mulcher -p cerebras -q "List 3 use-cases for embeddings"
```

### Databricks

- `DATABRICKS_HOST` (required), e.g. `adb-1234567890123456.17.azuredatabricks.net`
- `DATABRICKS_TOKEN` (required)
- `DATABRICKS_API_BASE` (optional, default `https://<host>/api/2.0/ai`)
- `DATABRICKS_MODEL` (optional, default `meta-llama/Meta-Llama-3.1-8B-Instruct`)

Example:

```powershell
$env:DATABRICKS_HOST = "adb-xxxxxxxxxxxxxxxx.xx.azuredatabricks.net"
$env:DATABRICKS_TOKEN = "dapixx..."
python -m sigma_mulcher -p databricks -q "Generate 5 test ideas for an API"
```

### Vapi

- `VAPI_API_KEY` (required)
- `VAPI_BASE_URL` (optional, default `https://api.vapi.ai/v1`)
- `VAPI_MODEL` (optional, default `default`)

Example:

```powershell
$env:VAPI_API_KEY = "vk_..."
python -m sigma_mulcher -p vapi -q "Translate to French: good morning"
```

## Notes

- The CLI prints the `output_text` by default. Pass `--raw` to print the full JSON response returned by the provider.
- If a required environment variable is missing, the CLI will exit with an error message.
- Network errors and HTTP errors are surfaced with brief messages to stderr.
