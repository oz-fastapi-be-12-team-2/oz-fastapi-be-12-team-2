set -eo pipefail  # 실패하면 더 진행하지 않음 -> 왜 실패했는지 조사 가능

COLOR_GREEN=`tput setaf 2;`
COLOR_NC=`tput sgr0;` # No Color

echo "Starting autoflake"
uv run autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
echo "OK"

echo "Starting black"
uv run black .
echo "OK"

echo "Starting isort"
uv run isort --check-only .
echo "OK"

echo "Starting flake8"
uv run flake8 .
echo "OK"

echo "Starting ruff"
uv run ruff check --select I --fix
uv run ruff check --fix
echo "OK"

echo "Starting mypy"
uv run dmypy run -- .
echo "OK"

echo "Starting pytest with coverage"
uv run coverage run -m pytest
uv run coverage report -m
uv run coverage html

echo "${COLOR_GREEN}All tests passed successfully!${COLOR_NC}"