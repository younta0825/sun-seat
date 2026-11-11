# 햇빛 좌석 (sun-seat)

버스 탈 때 어느 자리가 햇빛을 덜 받는지 알려주는 서비스. 지금은 5006번(광교차고지↔강남), 65번(광교차고지↔안양역)을 지원해요.

## 실행
1. `.env`에 `GBIS_KEY=인증키` 넣기
2. `python3 fetch_routes.py` — 경기도 버스 API에서 노선 정류장·경로 좌표 받기 (data/)
3. `python3 build_data.py` — 화면용 web/routes.js 만들기
4. `web/index.html`을 브라우저로 열기 (한 파일 버전: web/sun-seat-standalone.html)

## 구조
- `web/sun.js` — 태양 위치 계산, 진행 방향, 좌석 구역별 햇빛 노출 계산 (핵심 로직)
- `web/index.html` — 화면
- 노선 추가: build_data.py의 TARGETS에 data/ 파일을 추가

## 배포 (GitHub Pages)
`python3 build_data.py`를 돌리면 `docs/index.html`이 갱신돼요. 저장소 Settings → Pages에서 main 브랜치의 `/docs` 폴더를 선택하면 배포돼요.

노선 데이터 출처: 경기도 버스정보(GBIS), 공공데이터포털
