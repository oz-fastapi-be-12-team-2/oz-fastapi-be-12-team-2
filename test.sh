set -eo pipefail  # 실패하면 더 진행하지 않음 -> 왜 실패했는지 조사 가능

COLOR_GREEN=`tput setaf 2;`  # 초록색 출력
COLOR_NC=`tput sgr0;`        # 색상 초기화

# -----------------------------------------------------------
# 불필요한 import / 사용하지 않는 변수 자동 제거
# -----------------------------------------------------------
echo "Starting autoflake"
uv run autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
echo "OK"

# -----------------------------------------------------------
# isort: import 순서 정렬 (실제로 수정)
# black 프로필과 맞춰서 black과 충돌 방지
# -----------------------------------------------------------
echo "Starting isort (auto-fix imports)"
uv run isort . --profile black
echo "OK"

# -----------------------------------------------------------
# black: 코드 포맷팅 (줄맞춤, 따옴표 스타일 등 자동 수정)
# -----------------------------------------------------------
echo "Starting black"
uv run black .
echo "OK"

# -----------------------------------------------------------
# flake8: 린트 검사 (자동 수정하지 않고 리포트만)
# -----------------------------------------------------------
echo "Starting flake8"
uv run flake8 app --exclude .venv
echo "OK"

# -----------------------------------------------------------
# ruff: import 정렬(I 규칙) 자동 수정
# -----------------------------------------------------------
echo "Starting ruff (auto-fix: imports only)"
uv run ruff check --select I --fix .
echo "OK"

# -----------------------------------------------------------
# ruff: 의미 있는 코드 오류(F/E/W) → 리포트만, 자동 수정 없음
# -----------------------------------------------------------
echo "Starting ruff (report only: other issues)"
uv run ruff check --extend-select F,E,W --no-fix .
echo "OK"

# -----------------------------------------------------------
# mypy: 타입 체크 (코드 오류 잡기)
# -----------------------------------------------------------
echo "Starting mypy"
uv run dmypy run -- .
echo "OK"

# -----------------------------------------------------------
# pytest + coverage: 단위 테스트 실행 및 커버리지 리포트 생성
# -----------------------------------------------------------
echo "Starting pytest with coverage"
uv run coverage run -m pytest
uv run coverage report -m
uv run coverage html

echo "${COLOR_GREEN}All tests passed successfully!${COLOR_NC}"
