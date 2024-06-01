# Rosy Assistant App

### 1. Create a virtual environment

```shell
python3 -m venv .venv
source .venvs/bin/activate
```

### 2. Install libraries

```shell
pip install -r src/requirements.txt
```

### 3. create env variables for

```shell
OPENAI_API_KEY=***
OPENAI_MODEL_NAME=***
EXA_API_KEY=***
```

- To use Exa for research, export your EXA_API_KEY (get it from [here](https://dashboard.exa.ai/api-keys))

### 4. Run PgVector

provide long-term memory and knowledge to the LLM.


- run using the docker run command

```shell
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  --name pgvector \
  phidata/pgvector:16
```

### 5. Run the App

```shell
streamlit run src/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your App.
- Add a blog post to knowledge base: https://blog.samaltman.com/gpt-4o
- Ask: What is gpt-4o?
- Web search: Whats happening in france?
- Enable the Research Assistant and ask: write a report on the ibm hashicorp acquisition
- Enable the Investment Assistant and ask: shall i invest in nvda?
