import os

# Unit tests mock Claude but still run through @traceable functions. A real
# environment variable beats backend/.env in pydantic-settings, so this keeps
# test runs from sending fake traces to the LangSmith project.
os.environ.setdefault("LANGSMITH_TRACING", "false")
