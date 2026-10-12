# Recall Knowledge

[English](README.md) · **한국어**

AI 코딩 에이전트와 배운 내용을 명령 한 번으로 저장하고, 터미널을 떠나지 않고 간격 반복으로 복습합니다.

- `/save-knowledge`는 지금 세션에서 배운 개념을 복습 카드로 만듭니다.
- `/recall-knowledge`는 복습할 때가 된 카드로 객관식 문제를 냅니다.
- 복습 일정은 공식 Python 구현체 [FSRS](https://github.com/open-spaced-repetition/py-fsrs)로 계산합니다.
- **Claude Code**와 **Codex** 모두에서 MCP 서버 하나(`rk-mcp`)로 동작하고, 두 도구가 카드 DB 하나를 함께 씁니다.

## 왜 만들었나

AI의 도움으로 이해한 개념도 시간이 지나면 잊힙니다. 대화하는 동안에는 다 안다고 느끼지만, 며칠 뒤 같은 문제를 만나면 다시 물어보게 됩니다. 배운 것을 오래 남기려면 학습 연구에서 효과가 꾸준히 확인된 두 가지가 필요합니다.

- **간격을 두고 복습하기.** 기억은 시간이 지나면 빠르게 흐려지지만(에빙하우스의 망각 곡선), 잊기 직전에 다시 떠올리면 다음에 잊히기까지 걸리는 시간이 길어집니다. 문제는 그 시점을 사람이 직접 맞추기 어렵다는 것입니다. 그래서 FSRS가 카드마다 지금 기억해 낼 확률을 추정하고, 그 확률이 90%로 떨어질 때 복습하도록 일정을 잡습니다.
- **다시 읽지 말고 떠올리기.** 같은 내용을 다시 읽는 것보다 기억에서 꺼내 보는 쪽이 장기 기억에 훨씬 잘 남습니다(인출 연습, 시험 효과). 그래서 복습할 때 카드를 보여 주지 않고 문제를 냅니다. 객관식이라 정답 여부가 바로 판정되고, 그 결과가 그대로 FSRS의 `Good`과 `Again`이 됩니다. "얼마나 잘 기억했는지"를 스스로 매길 필요가 없습니다.

기존 간격 반복 도구도 이 원리를 쓰지만, 카드를 직접 쓰고, 앱을 옮겨 가고, 내용을 정리해야 해서 대부분 여기서 멈춥니다. Recall Knowledge는 카드 작성을 에이전트에게 맡기고, 저장과 복습을 이미 쓰고 있던 에이전트 세션 안에서 모두 끝냅니다.

## FSRS란

간격 반복은 카드를 잊어버리기 직전에 다시 보여 주는 방식입니다. 복습에 성공할 때마다 다음 복습까지의 간격이 늘어나서, 잘 아는 카드는 매일이 아니라 몇 주나 몇 달 뒤에 다시 나옵니다. 어려운 부분은 그 간격을 정하는 일이고, 이를 스케줄러가 맡습니다.

[FSRS](https://github.com/open-spaced-repetition/fsrs4anki/wiki/ABC-of-FSRS)(Free Spaced Repetition Scheduler)는 카드마다 세 가지 값으로 기억을 모델링하는 오픈소스 스케줄러입니다.

- **난이도(Difficulty)**: 나에게 이 카드가 얼마나 어려운지
- **안정성(Stability)**: 기억할 확률이 90%로 떨어지기까지 걸리는 일수
- **인출 가능성(Retrievability)**: 지금 이 순간 기억해 낼 확률

## 요구 사항

- [uv](https://docs.astral.sh/uv/)
- Claude Code 또는 Codex (둘 다 가능)

## 설치

```bash
git clone https://github.com/aksworns22/recall-knowledge.git ~/recall-knowledge
cd ~/recall-knowledge
./install.sh
```

스크립트가 하는 일:

1. `uv tool install --editable`로 `rk`(CLI)와 `rk-mcp`(MCP 서버)를 설치합니다. repo를 수정하면 바로 반영됩니다.
2. 두 스킬을 `~/.claude/skills/`와 `~/.codex/skills/`에 symlink로 연결합니다.
3. `claude mcp add --scope user`와 `codex mcp add`로 MCP 서버를 `rk`라는 이름으로 등록합니다.
4. `~/.knowledge/knowledge.db`에 DB를 만듭니다.

설치 후 `rk`를 찾을 수 없다고 나오면 `uv tool update-shell`을 실행하고 터미널을 새로 여세요.

### 제거

```bash
./install.sh --uninstall
```

CLI, MCP 등록, 스킬 링크만 지웁니다. 카드는 `~/.knowledge/knowledge.db`에 그대로 남습니다.

## 사용법

1. 평소처럼 Claude Code나 Codex와 작업하거나 공부합니다.
2. 기억하고 싶은 내용이 생기면 `/save-knowledge`를 실행합니다.
   - `/save-knowledge useEffect cleanup은 다음 effect 전에 실행된다`처럼 내용을 함께 쓰면, 그 내용을 바로 카드로 저장합니다.
   - 내용 없이 실행하면, 에이전트가 이번 세션에서 어려워했거나 핵심이었던 개념 1~4개를 고르고, 중복을 확인한 뒤, 한 번만 확인을 받습니다.
3. 원할 때 `/recall-knowledge`를 실행합니다. 복습할 카드마다 한 문제씩, 한 번에 최대 10개를 냅니다(`/recall-knowledge 5`처럼 줄일 수 있음).
4. 맞히면 **Good**, 틀리면 **Again**으로 평가하고 FSRS가 다음 복습일을 정합니다.

새 카드는 저장하자마자 복습 대상이 되므로, 그 세션이 끝날 때 바로 복습할 수 있습니다.

### 카드 예시

```json
{
  "title": "React Server Components 직렬화 경계",
  "summary": "서버 컴포넌트는 서버에서만 실행된다. 클라이언트 컴포넌트로 넘기는 값은 네트워크 경계를 넘으므로 직렬화할 수 있어야 한다.",
  "key_points": [
    "서버 컴포넌트의 코드는 브라우저로 전송되지 않는다",
    "클라이언트 컴포넌트에 넘기는 props는 직렬화 가능해야 한다",
    "서버 컴포넌트에서 클라이언트 컴포넌트로 함수를 props로 넘길 수 없다"
  ],
  "tags": ["react", "nextjs"],
  "source": "my-app"
}
```

문제는 카드의 `key_points`와 `summary` 안에서만 출제되므로, 직접 남기기로 고른 내용만 묻습니다.

## 구조

```
/save-knowledge, /recall-knowledge   SKILL.md: 진행 흐름만
            │ MCP (stdio)
            ▼
rk-mcp                               도구 + 도구 설명에 담긴 카드 작성·출제 규칙
            │
            ▼
~/.knowledge/knowledge.db            SQLite + py-fsrs
```

카드 작성 규칙과 출제 규칙이 MCP 도구 설명에 들어 있어서 스킬은 짧게 유지됩니다. 어떤 MCP 클라이언트에서든 똑같이 동작하고, 에이전트가 셸 명령이나 JSON을 직접 조립할 일이 없습니다.

## MCP 도구

| 도구 | 역할 |
|---|---|
| `search_cards(keywords, limit)` | 키워드 중 하나라도 맞는 카드 검색 (중복 확인용) |
| `save_cards(cards)` | 카드 하나 이상 저장, 저장 즉시 복습 대상 |
| `update_card(card_id, ...)` | 카드 내용 수정, 복습 일정은 유지 |
| `get_due_cards(limit)` | 복습할 카드 목록, 카드마다 정답 위치 `answer_slot`(A~D)을 무작위로 지정 |
| `record_review(card_id, correct)` | `true`면 Good, `false`면 Again으로 기록하고 다음 복습일 반환 |
| `get_stats()` | 전체 카드 수, 지금 복습할 카드 수, 다음 복습일 |

## `rk` CLI

CLI는 같은 DB를 씁니다. 사용자가 직접 확인하거나, 스크립트를 짜거나, 디버깅할 때 씁니다. 모든 명령은 결과를 JSON으로 stdout에 출력합니다. 오류는 `{"error": "..."}` 형태로 stderr에 출력하고 종료 코드 1을 반환합니다.

| 명령 | 역할 |
|---|---|
| `rk init` | DB가 없으면 생성 |
| `rk add` | stdin의 JSON(객체 하나 또는 배열)으로 카드 추가 |
| `rk search <kw>...` | title, summary, key_points, tags 중 하나라도 키워드와 맞는 카드 검색 |
| `rk due [--limit N]` | 복습할 카드를 오래된 순으로 출력 (기본 10개) |
| `rk review <id> good\|again` | 결과를 기록하고 다음 복습일 출력 |
| `rk show <id>` | 카드 하나와 FSRS 상태 출력 |
| `rk update <id>` | stdin의 JSON으로 카드 내용 수정, 복습 일정은 유지 |
| `rk delete <id>` | 카드 삭제 |
| `rk stats` | 전체 카드 수, 지금 복습할 카드 수, 다음 복습일 |
| `rk export` | 전체 카드를 JSON으로 출력 |

`--now <ISO 8601>`로 현재 시각을 바꿀 수 있어 테스트할 때 편합니다. `RK_DB`로 DB 경로를 바꿀 수 있습니다.

## 복습 일정 계산

`rk`는 `fsrs.Scheduler`를 다음 설정으로 사용합니다.

| 설정 | 값 | 이유 |
|---|---|---|
| `desired_retention` | `0.9` | 기억 확률이 90%로 떨어질 때 복습 |
| `learning_steps` | `()` | 터미널에서 하루 한 번 정도 복습하므로 분 단위 단계가 맞지 않음 |
| `relearning_steps` | `()` | 같은 이유. 틀린 카드는 바로 짧은 날짜 단위 간격으로 이동 |
| `enable_fuzzing` | `True` | 함께 저장한 카드가 항상 같은 날 몰려 나오지 않게 분산 |

평가는 두 가지만 씁니다. 맞히면 `good`, 틀리면 `again`입니다. 복습 기록을 따로 남기지 않으므로 FSRS는 기본 파라미터로 동작합니다.

## 저장소

SQLite 파일 하나(`~/.knowledge/knowledge.db`)를 WAL 모드로 씁니다. 그래서 Claude Code와 Codex 세션이 동시에 써도 안전합니다.

```sql
CREATE TABLE cards (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  summary     TEXT NOT NULL,
  key_points  TEXT NOT NULL,         -- JSON 배열
  tags        TEXT NOT NULL DEFAULT '[]',
  source      TEXT,
  created_at  TEXT NOT NULL,
  fsrs_card   TEXT NOT NULL,         -- fsrs.Card를 JSON으로 직렬화
  due         TEXT NOT NULL          -- 인덱스용으로 fsrs_card에서 복사
);
```

FSRS 카드는 py-fsrs가 직렬화한 형태 그대로 저장하므로, py-fsrs를 업그레이드해도 스키마를 바꿀 필요가 없습니다.

## 프로젝트 구조

```
src/rk/server.py      MCP 서버 (rk-mcp)
src/rk/cli.py         CLI (rk)
src/rk/db.py          SQLite 저장소
src/rk/scheduler.py   py-fsrs 래퍼
src/rk/validate.py    CLI와 서버가 함께 쓰는 카드 검증
skills/               Claude Code와 Codex가 함께 쓰는 SKILL.md
tests/                pytest 테스트
install.sh            설치 스크립트
```

## 문제 해결

- **에이전트가 `rk` 도구를 못 찾을 때:** `claude mcp list` 또는 `codex mcp list`로 `rk`가 등록됐는지 확인하세요. 설치 후에는 세션을 새로 시작해야 합니다.

## 개발

```bash
uv run pytest
```
