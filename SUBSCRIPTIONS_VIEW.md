# 구독 뷰(Subscriptions View) 테스트 가이드

이 문서는 구독 관련 화면(구독 채널 리스트, 구독 피드, 구독/구독취소 등)에서 사용하는 API만 모아 정리한 문서입니다.
테스트 기준 URL은 http://localhost:8000 입니다.

요약
- 서버가 로컬에서 실행 중이어야 합니다: `python app.py` (http://localhost:8000)
- 공통 헤더: `Content-Type: application/json`

---

## 1) 상단 사용자 헤더
- 목적: 사용자가 구독한 채널들의 요약 정보(채널 id, 이름, 프로필 이미지, 최신 업로드 썸네일 등)를 가져옵니다.
- Method: GET
- URL: http://localhost:8000/subscriptions/{user_id}/header
- 예: http://localhost:8000/subscriptions/1/header

예시 (curl)
```bash
curl -v "http://localhost:8000/subscriptions/1/header"
```

예시 (Python requests)
```python
import requests
res = requests.get('http://localhost:8000/subscriptions/1/header')
print(res.status_code)
print(res.json())
```

예상 응답(200) 예시
```json
{
  "headers": [
    {
      "channel_id": 3,
      "channel_name": "게임하는토끼",
      "channel_profile": "https://cdn.example.com/u3.png",
      "latest_upload": "2024-03-15 19:00:00",
      "latest_thumbnail": "https://cdn.example.com/v9.jpg"
    }
  ]
}
```

주의
- `{user_id}` 자리에는 실제 숫자 ID를 넣어 호출하세요. 플레이스홀더 `:user_id` 그대로는 404가 납니다.

---

## 2) 필터 리스트
- 목적: 구독 피드에서 사용할 필터 목록을 반환합니다.
- Method: GET
- URL: http://localhost:8000/subscriptions/filters

예시 (curl)
```bash
curl "http://localhost:8000/subscriptions/filters"
```

예상 응답(200) 예시
```json
{
  "filters": ["전체","오늘","동영상","shorts","라이브","이어서시청하기","시청하지않음"]
}
```

---

## 2.5) 구독 채널 목록 (Channels list)
- 목적: 사용자가 구독한 채널들의 목록을 유튜브 앱 기준으로 채널명과 프로필 이미지만 반환합니다.
- Method: GET
- URL: http://localhost:8000/subscriptions/{user_id}/subscriptions
- 예: http://localhost:8000/subscriptions/1/subscriptions
- 쿼리 파라미터:
  - `limit` (선택, 정수, 기본 20, 최대 100)
  - `offset` (선택, 정수, 기본 0)

예시 (curl)
```bash
curl "http://localhost:8000/subscriptions/1/subscriptions?limit=20&offset=0"
```

예시 (Python requests)
```python
import requests
res = requests.get('http://localhost:8000/subscriptions/1/subscriptions', params={'limit':20,'offset':0})
print(res.status_code)
print(res.json())
```

예상 응답(200) 예시
```json
{
  "channels": [
    {
      "channel_id": 123,
      "channel_name": "채널 A",
      "channel_profile": "https://cdn.example.com/u123.jpg"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

노트
- 반환 항목은 채널명과 프로필 이미지 중심입니다(이전의 `subscribed_at` 필드는 포함하지 않음).
- 정렬: 채널명(유저네임) 오름차순으로 정렬됩니다.
- 서버는 내부적으로 중복을 제거하기 위해 DISTINCT를 사용합니다.
- 인증: `user_id` 경로 파라미터는 호출자(identity)와 일치하는지 서버에서 검증해야 합니다(현재 문서화된 예시는 로컬 테스트용).


## 3) 구독 피드 (Subscription Feed)
- 목적: 특정 사용자가 구독한 채널들의 영상 목록을 가져옵니다(타입/기능별 필터 가능).
- Method: GET
- URL: http://localhost:8000/subscriptions/{user_id}/feed
- 예: http://localhost:8000/subscriptions/1/feed
- 쿼리 파라미터 예:
  - `type` = `video` | `shorts` | `live` | `all` (없으면 전체)
  - `filter` = `today` | `unwatched` | `continue` | `all`

예시 (curl)
```bash
curl "http://localhost:8000/subscriptions/1/feed?type=video&filter=all"
```

예시 (Python requests)
```python
import requests
res = requests.get('http://localhost:8000/subscriptions/1/feed', params={'type':'video','filter':'all'})
print(res.status_code)
print(res.json())
```

예상 응답(200) 간단 예시
```json
{
  "feed": [
    {
      "video_id": 3,
      "title": "롤 하이라이트 모음",
      "thumbnail_url": "https://cdn.example.com/v3.jpg",
      "duration": "00:12:05",
      "upload_date": "2024-02-20 21:30:00",
      "time_ago": "며칠 전",
      "channel_id": 3,
      "channel_name": "게임하는토끼",
      "channel_profile": "https://cdn.example.com/u3.png",
      "view_count": 47000
    }
  ]
}
```

---

## 4) 구독하기 (Subscribe)
- 목적: 사용자가 특정 채널을 구독하도록 추가합니다.
- Method: POST
- URL: http://localhost:8000/subscriptions/{user_id}/channel/{channel_id}
- 예: http://localhost:8000/subscriptions/1/channel/2

예시 (curl)
```bash
curl -X POST "http://localhost:8000/subscriptions/1/channel/2" -H "Content-Type: application/json"
```

예시 (Python requests)
```python
import requests
res = requests.post('http://localhost:8000/subscriptions/1/channel/2')
print(res.status_code)
print(res.json())
```

예상 응답(201)
```json
{ "success": true, "action": "subscribed" }
```

에러/중복 처리
- 이미 구독 중일 경우에도 서버는 중복을 방지하거나 subscribed_at을 갱신하도록 동작합니다(현재 구현은 ON DUPLICATE KEY UPDATE 사용).

---

## 5) 구독 취소 (Unsubscribe)
- 목적: 사용자의 구독을 삭제합니다.
- Method: DELETE
- URL: http://localhost:8000/subscriptions/{user_id}/channel/{channel_id}
- 예: http://localhost:8000/subscriptions/1/channel/2

예시 (curl)
```bash
curl -X DELETE "http://localhost:8000/subscriptions/1/channel/2"
```

예시 (Python requests)
```python
import requests
res = requests.delete('http://localhost:8000/subscriptions/1/channel/2')
print(res.status_code)
print(res.json())
```

예상 응답(200)
```json
{ "success": true, "action": "unsubscribed" }
```

---

## 테스트 체크리스트
- 서버가 켜져 있는지 확인: `python app.py` → http://localhost:8000 접속 확인
- URL의 플레이스홀더에 숫자 ID를 넣어 호출
- DB에 더미 데이터가 필요한 경우 `seed.sql`로 삽입 후 테스트
- 인증 플러그인 문제 발생 시: `db.py`에서 PyMySQL 폴백이 동작하도록 이미 구현되어 있습니다.

문의/추가
- 원하는 경우 이 파일로부터 Postman Collection(JSON)을 생성해 드리겠습니다. 또는 예시 응답을 실제 DB 결과로 맞춰 채워 넣을 수도 있습니다.
