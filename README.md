# wpycli

`wpycli`는 Python 3.12+ 환경을 위한 **Cobra 스타일 CLI 툴킷**입니다.

주요 기능:

- 계층형 명령 트리와 alias 지원
- local 플래그와 persistent 플래그 지원
- `--help`, `help`, `--version` 자동 처리
- 훅 기반 실행 흐름
- `wconfig` 기반 계층형 설정 부트스트랩
- `wlogger` 기반 로깅 부트스트랩
- `rich` 없이도 색상, 패널, 구조화된 help를 제공하는 경량 터미널 출력

이 프로젝트는 `https://pypi.wkqcosoft.cloud` 에서 직접 호스팅하는 `wlogger`, `wconfig` 패키지를 사용합니다.

## 설치

```bash
pip install .
```

`pyproject.toml`에 직접 wheel URL을 사용하고 있으므로, 설치 시 `wlogger`와 `wconfig`도 함께 자동으로 내려받습니다.

## 예제

```bash
python main.py --help
python main.py serve --config ./config.yaml
python main.py --log-level DEBUG config
python main.py echo hello world
```

## 프로그래밍 모델

```python
from wpycli import Command, ConfigSettings, LoggingSettings

root = Command(
    use="demo",
    short="Demo CLI",
    version="0.1.0",
)

root.add_persistent_string_flag("config", help="설정 파일 경로")
root.add_persistent_string_flag("log-level", help="로그 레벨 덮어쓰기")

root.configure_runtime(
    config=ConfigSettings(
        defaults={"logging": {"level": "INFO"}},
        env_prefix="DEMO",
        file_flag="config",
    ),
    logging=LoggingSettings(
        logger_name="demo",
        level_flag="log-level",
    ),
)

def run(ctx):
    ctx.logger.info("running %s", ctx.command.full_path)
    print(ctx.config.as_dict())

show = Command(use="show", short="설정 출력", run=run)
root.add_command(show)

raise SystemExit(root.execute())
```

## Cobra 스타일 동작 방식

- 루트 명령이 전체 명령 트리를 소유합니다.
- 하위 명령은 `add_command()`로 명시적으로 등록합니다.
- persistent 플래그는 부모 명령에서 자식 명령으로 전파됩니다.
- 실행 순서는 `persistent_pre_run* -> pre_run -> run -> post_run -> persistent_post_run*` 입니다.
- help 텍스트는 명령 메타데이터와 등록된 플래그를 기준으로 자동 생성됩니다.
- 터미널 출력은 `rich` 대신 내부 경량 렌더러를 사용합니다.

## 개발

```bash
python -m unittest discover -s tests
```
