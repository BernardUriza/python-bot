# fi-based template backend — Azure Container Apps image.
# conda-native base, non-root user. Build from the api/ dir:
#   docker build -t app api/
# No agent CLI layer: every turn crosses AIRE's door over HTTPS, so nothing
# spawns `claude` or `codex` here anymore.
FROM quay.io/condaforge/miniforge3:latest
SHELL ["/bin/bash", "-l", "-c"]
WORKDIR /app

# Conda env into base (Python + fi-runner + FastAPI — no Node anymore).
COPY environment.yml .
RUN mamba env update -n base -f environment.yml \
 && mamba clean --all --yes \
 && find /opt/conda/ -follow -type f -name '*.pyc' -delete

# NOTE (2026-08-29, the AIREBackend consolidation): this used to install
# `@anthropic-ai/claude-code` and `@openai/codex` because fi_runner shelled out
# to them. It no longer does — AIRE runs the agent server-side. Nothing local
# needs an agent CLI, so the layer is gone and the image is smaller.
#
# A local MCP server would still need its npm package here — but on the AIRE
# route a local MCP server never runs (only its NAME crosses the door). See the
# `_MCP_SERVERS` note in app/runner.py before adding anything back.

# App code (app/ package + entrypoint).
COPY . /app/
RUN chmod +x /app/entrypoint.sh

# Non-root user. It used to be MANDATORY (Claude Code refuses BYPASS as root);
# with the agent running on AIRE that reason is gone, and it stays because
# running a public API as root is a bad idea on its own merits.
RUN useradd --create-home --shell /bin/bash --uid 10001 runner \
 && chown -R runner:runner /app /home/runner
USER runner
ENV HOME=/home/runner

EXPOSE 8080
CMD ["/app/entrypoint.sh"]
