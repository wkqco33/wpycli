# wpycli

`wpycli`는 Python 3.12+ 환경을 위한 **Cobra 스타일 CLI 툴킷**입니다. Go의 `cobra`에서 영감을 받아, 명확한 구조와 강력한 설정을 지향하면서도 Python다운 간결함을 유지합니다.

## 주요 기능

- **관리 도구**: `wpycli init`, `add` 명령어를 통한 프로젝트 구조 자동 생성 및 관리
- **명령 트리**: 계층형 명령 트리와 alias 지원
- **플래그 시스템**: local 플래그와 persistent 플래그 지원
- **자동화된 도움말**: `--help`, `help`, `--version` 자동 처리
- **유연한 훅**: 전처리와 후처리를 위한 훅 기반 실행 흐름
- **런타임 부트스트랩**: PyPI 패키지 `wpyconf`와 `wpylog` 기반 계층형 설정 및 로깅 자동 구성
- **경량 터미널**: `rich` 없이도 색상, 패널, 구조화된 help를 제공하는 내장 렌더러

## 설치 및 환경 구성

`uv`를 사용하여 의존성을 설치하고 개발 환경을 구성하는 것을 권장합니다.

```bash
# 프로젝트 다운로드 및 의존성 설치
git clone https://github.com/wkqco33/wpycli.git
cd wpycli
uv sync

# 또는 라이브러리로 설치
uv pip install .
```

## 프로젝트 관리 (CLI 도구)

`wpycli` 관리 도구 또한 `uv run`을 통해 즉시 실행할 수 있습니다.

### 1. 프로젝트 초기화

새로운 CLI 프로젝트를 시작합니다.

```bash
mkdir my-project
cd my-project
uv run --project .. wpycli init my-project
```

`init`은 현재 디렉터리에 프로젝트 파일을 생성하므로 비어 있는 디렉터리에서 실행합니다.

- `main.py`: 엔트리포인트 파일 생성
- `my_project/commands/root.py`: 루트 커맨드 정의 파일 생성

### 2. 커맨드 추가

프로젝트에 새로운 서브 커맨드를 추가합니다.

```bash
cd my-project
uv run wpycli add serve
```

- `my_project/commands/serve.py`: 커맨드 로직 파일 생성
- `root.py`에 해당 커맨드가 자동으로 임포트 및 등록됩니다.

## 예제 실행

`uv run`을 사용하면 별도의 가상환경 활성화 없이도 안전하게 예제를 실행할 수 있습니다.

```bash
uv run python main.py --help
uv run python main.py serve --config ./config.yaml
uv run python main.py --log-level DEBUG config
```

## 프로그래밍 모델

```python
from wpycli import Command, ConfigSettings, LoggingSettings

def build_cli() -> Command:
    root = Command(
        use="demo",
        short="Demo CLI",
        version="0.2.0",
    )

    root.add_persistent_string_flag("config", help="설정 파일 경로")
    
    root.configure_runtime(
        config=ConfigSettings(
            defaults={"server": {"port": 8080}},
            env_prefix="DEMO",
            file_flag="config",
        ),
        logging=LoggingSettings(logger_name="demo"),
    )

    def _run_echo(ctx):
        print(f"Echo: {' '.join(ctx.args)}")

    echo = Command(use="echo", short="출력", run=_run_echo)
    root.add_command(echo)
    return root

if __name__ == "__main__":
    build_cli().execute()
```

## 개발 및 테스트

```bash
# 의존성 동기화
uv sync

# 테스트 실행
uv run python -m unittest discover -s tests
```

## 라이선스

이 프로젝트는 [MIT License](LICENSE)로 배포됩니다.
