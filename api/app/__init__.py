"""fi-based fullstack template — FastAPI face over a fi_runner agent.

This package is the api/ half of the python-bot template: a thin HTTP/SSE
boundary in front of a fi_runner Runner on AIRE's door (longitudinal
ConversationStore memory, optional RAG, anti-drift guards). It carries NO
business logic — fill the persona in ``runner.py`` and the AIRE registry tools
in ``backend.py``, and ship.
"""
